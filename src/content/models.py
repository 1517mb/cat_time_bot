from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

from core.constants import ProgramCfg


class Program(models.Model):
    name = models.CharField(
        max_length=ProgramCfg.NAME_MAX_LEN,
        verbose_name=ProgramCfg.NAME_V
    )
    description = models.TextField(
        verbose_name=ProgramCfg.DESCRIPTION_V
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
        verbose_name=ProgramCfg.DOWNLOADS_V
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=ProgramCfg.RATING_DEFAULT,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(5.0)
        ],
        verbose_name=ProgramCfg.RATING_V
    )
    verified = models.BooleanField(
        default=ProgramCfg.VERIFIED_DEFAULT,
        verbose_name=ProgramCfg.VERIFIED_V
    )
    created_at = models.DateTimeField(
        auto_now_add=ProgramCfg.CREATTED_AUTO_NOW_ADD,
        verbose_name=ProgramCfg.CREATED_V
    )
    updated_at = models.DateTimeField(
        auto_now=ProgramCfg.UPDATED_AUTO_NOW,
        verbose_name=ProgramCfg.UPDATED_V
    )

    def clean(self):
        """Проверяет наличие файла или внешней ссылки"""
        if not self.file and not self.external_download_link:
            raise ValidationError(
                "Необходимо указать файл или внешнюю ссылку для скачивания."
            )

    def save(self, *args, **kwargs):
        """Принудительная валидация при сохранении"""
        self.full_clean()
        super().save(*args, **kwargs)

    def increment_downloads(self):
        """Увеличивает счетчик скачиваний"""
        self.downloads += 1
        self.save(update_fields=["downloads"])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = ProgramCfg.META_NAME
        verbose_name_plural = ProgramCfg.META_PL_NAME
        ordering = ProgramCfg.ORDERING
