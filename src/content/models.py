import hashlib
import logging
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field

from core.constants import NewsCfg, ProgramCfg

logger = logging.getLogger(__name__)


class News(models.Model):
    title = models.CharField(
        max_length=NewsCfg.TITLE_MAX_LEN,
        verbose_name=NewsCfg.TITLE_V
    )
    content = CKEditor5Field(
        verbose_name=NewsCfg.CONTENT_V,
        config_name="extends"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name=NewsCfg.AUTHOR_RELATED,
        verbose_name=NewsCfg.AUTHOR_V
    )
    slug = models.SlugField(
        max_length=NewsCfg.SLUG_MAX_LEN,
        unique=True,
        verbose_name=NewsCfg.SLUG_V
    )
    image = models.ImageField(
        upload_to=NewsCfg.IMAGE_UPLOAD_TO,
        blank=NewsCfg.IMAGE_BLANK,
        null=NewsCfg.IMAGE_NULL,
        verbose_name=NewsCfg.IMAGE_V
    )
    is_published = models.BooleanField(
        default=NewsCfg.IS_PUBLISHED_DEFAULT,
        verbose_name=NewsCfg.IS_PUBLISHED_V
    )
    created_at = models.DateTimeField(
        auto_now_add=NewsCfg.CREATED_AUTO_NOW_ADD,
        verbose_name=NewsCfg.CREATED_V
    )
    updated_at = models.DateTimeField(
        auto_now=NewsCfg.UPDATED_AUTO_NOW,
        verbose_name=NewsCfg.UPDATED_V
    )

    def clean(self):
        """Проверка даты публикации"""
        if self.created_at and self.created_at > timezone.now():
            raise ValidationError("Дата публикации не может быть в будущем")

    def save(self, *args, **kwargs):
        """Принудительная валидация при сохранении"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = NewsCfg.META_NAME
        verbose_name_plural = NewsCfg.META_PL_NAME
        ordering = NewsCfg.ORDERING
        indexes = NewsCfg.INDEXES


class Program(models.Model):
    name = models.CharField(
        max_length=ProgramCfg.NAME_MAX_LEN,
        verbose_name=ProgramCfg.NAME_V
    )
    description = CKEditor5Field(
        verbose_name=ProgramCfg.DESCRIPTION_V,
        config_name="default"
    )
    external_download_link = models.URLField(
        verbose_name=ProgramCfg.EXT_DOWNLOAD_V,
        blank=ProgramCfg.EXT_DOWNLOAD_BLANK,
        null=ProgramCfg.EXT_DOWNLOAD_NULL
    )
    file = models.FileField(
        upload_to=ProgramCfg.FILE_UPLOAD_TO,
        verbose_name=ProgramCfg.FILE_V,
        blank=ProgramCfg.FILE_BLANK,
        null=ProgramCfg.FILE_NULL
    )
    downloads = models.PositiveIntegerField(
        default=ProgramCfg.DOWNLOADS_DEFAULT,
        verbose_name=ProgramCfg.DOWNLOADS_V,
        db_index=True
    )

    rating_sum = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Сумма рейтингов"
    )
    ratings_count = models.PositiveIntegerField(
        default=ProgramCfg.RATINGS_COUNT_DEFAULT,
        verbose_name=ProgramCfg.RATINGS_COUNT_V,
        db_index=True
    )
    verified = models.BooleanField(
        default=ProgramCfg.VERIFIED_DEFAULT,
        verbose_name=ProgramCfg.VERIFIED_V,
        db_index=True
    )
    created_at = models.DateTimeField(
        auto_now_add=ProgramCfg.CREATED_AUTO_NOW_ADD,
        verbose_name=ProgramCfg.CREATED_V,
        db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=ProgramCfg.UPDATED_AUTO_NOW,
        verbose_name=ProgramCfg.UPDATED_V
    )

    @property
    def rating(self):
        if self.ratings_count == 0:
            return 0.00
        return round(self.rating_sum / self.ratings_count, 2)

    def add_rating(self, rating_value):
        """Добавляет новую оценку к программе."""
        if not (0 <= rating_value <= 5):
            raise ValidationError("Рейтинг должен быть от 0 до 5.")
        self.rating_sum += rating_value
        self.ratings_count += 1
        self.save(update_fields=["rating_sum", "ratings_count"])

    def clean(self):
        """Проверяет наличие файла или внешней ссылки"""
        super().clean()
        if not self.file and not self.external_download_link:
            raise ValidationError({
                "Необходимо указать файл или внешнюю ссылку для скачивания."
            })

    def save(self, *args, **kwargs):
        """Принудительная валидация при сохранении"""
        self.full_clean()
        super().save(*args, **kwargs)

    def increment_downloads(self):
        """Увеличивает счетчик скачиваний"""
        self.downloads += 1
        self.save(update_fields=["downloads"])

    def get_absolute_url(self):
        """Возвращает абсолютный URL для детальной страницы"""
        return reverse("content:program_detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = ProgramCfg.META_NAME
        verbose_name_plural = ProgramCfg.META_PL_NAME
        ordering = ProgramCfg.ORDERING
        constraints = [
            models.CheckConstraint(
                check=(models.Q(file__isnull=False) | models.Q(
                    external_download_link__isnull=False)),
                name="file_or_link_required"
            ),
            models.CheckConstraint(
                check=models.Q(rating_sum__gte=0),
                name="rating_sum_non_negative"
            ),
            models.CheckConstraint(
                check=models.Q(ratings_count__gte=0),
                name="ratings_count_non_negative"
            )
        ]


class ProgramVote(models.Model):
    program = models.ForeignKey(
        "Program",
        on_delete=models.CASCADE,
        verbose_name="Программа",
        related_name="votes"
    )
    ip_hash = models.CharField(
        max_length=64,
        verbose_name="Хэш IP адреса",
        db_index=True
    )
    voted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата голосования")

    class Meta:
        unique_together = ("program", "ip_hash")
        verbose_name = "Голос"
        verbose_name_plural = "Голоса"
        ordering = ("-voted_at",)
        indexes = [
            models.Index(fields=["-voted_at"])
        ]

    def __str__(self):
        return f"Голос за {self.program.name} от {self.ip_hash[:8]}..."

    @classmethod
    def create_vote(cls, program, ip_address):
        """Безопасное создание записи о голосовании"""
        salt = getattr(settings, "VOTE_SALT", "default_salt")
        ip_hash = hashlib.sha256(f"{salt}{ip_address}".encode()).hexdigest()

        try:
            existing_vote = cls.objects.get(program=program, ip_hash=ip_hash)
            logger.info(f"Vote already exists for program {program.id}"
                        f" from IP hash {ip_hash[:8]}...")
            return existing_vote, False

        except ObjectDoesNotExist:
            try:
                vote = cls(program=program, ip_hash=ip_hash)
                vote.save()
                logger.info(
                    f"New vote created for program {program.id}"
                    f" from IP hash {ip_hash[:8]}...")
                return vote, True

            except Exception as e:
                logger.error(
                    f"Vote creation error for program {program.id}: {str(e)}")
                return None, False

        except MultipleObjectsReturned:
            vote = cls.objects.filter(program=program, ip_hash=ip_hash).first()
            logger.warning(
                f"Multiple votes found for program {program.id},"
                "  returning first")
            return vote, False

    @classmethod
    def has_voted(cls, program, ip_address):
        """Проверяет, голосовал ли пользователь"""
        salt = getattr(settings, "VOTE_SALT", "default_salt")
        ip_hash = hashlib.sha256(f"{salt}{ip_address}".encode()).hexdigest()
        try:
            return cls.objects.filter(
                program=program,
                ip_hash=ip_hash
            ).exists()
        except Exception as e:
            logger.error(f"Error checking vote status: {str(e)}")
            return False
