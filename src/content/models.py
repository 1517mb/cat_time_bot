from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field

from core.constants import NewsCfg, ProgramCfg


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
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=ProgramCfg.RATING_DEFAULT,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(5.0)
        ],
        verbose_name=ProgramCfg.RATING_V,
        db_index=True
    )
    verified = models.BooleanField(
        default=ProgramCfg.VERIFIED_DEFAULT,
        verbose_name=ProgramCfg.VERIFIED_V,
        db_index=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=ProgramCfg.CREATED_V,
        db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=ProgramCfg.UPDATED_V
    )

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
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=(models.Q(file__isnull=False) | models.Q(
                    external_download_link__isnull=False)),
                name="file_or_link_required"
            )
        ]
