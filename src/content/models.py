from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


class Program(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name="Название программы"
    )
    description = models.TextField(
        verbose_name="Описание"
    )
    external_download_link = models.URLField(
        verbose_name="Внешняя ссылка",
        blank=True,
        null=True
    )
    file = models.FileField(
        upload_to="programs/%Y/%m/%d/",
        verbose_name="Файл программы",
        blank=True,
        null=True
    )
    downloads = models.PositiveIntegerField(
        default=0,
        verbose_name="Скачивания"
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.0,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(5.0)
        ],
        verbose_name="Рейтинг"
    )
    verified = models.BooleanField(
        default=False,
        verbose_name="Проверено"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Обновлено"
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
        verbose_name = "Программа"
        verbose_name_plural = "Программы"
        ordering = ["-created_at"]
