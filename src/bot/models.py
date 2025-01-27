from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from markdownx.models import MarkdownxField

from core.constants import MAX_LEN, CompanyCfg, UserActivityCfg


class Company(models.Model):
    name = models.CharField(
        verbose_name=CompanyCfg.VERBOSE_NAME,
        max_length=MAX_LEN)

    class Meta:
        verbose_name = CompanyCfg.META_NAME
        verbose_name_plural = CompanyCfg.META_PL_NAME

    def __str__(self) -> str:
        return self.name


class UserActivity(models.Model):
    user_id = models.IntegerField(
        verbose_name=UserActivityCfg.USER_ID_V
    )
    username = models.CharField(
        max_length=MAX_LEN,
        verbose_name=UserActivityCfg.USERNAME_V,
        blank=True,
        null=True)
    company = models.ForeignKey(
        Company,
        verbose_name=UserActivityCfg.COMPANY_V,
        on_delete=models.CASCADE)
    join_time = models.DateTimeField(
        verbose_name=UserActivityCfg.JOIN_TIME_V,
        default=timezone.now)
    leave_time = models.DateTimeField(
        verbose_name=UserActivityCfg.LEAVE_TIME_V,
        blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.username} в {self.company.name}"

    @property
    def get_spent_time(self):
        if self.leave_time:
            delta = self.leave_time - self.join_time
            total_seconds = delta.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            if hours < 1:
                return f"{minutes} мин."
            return f"{hours} ч. {minutes} мин."
        return "Ещё не покинул"

    class Meta:
        verbose_name = UserActivityCfg.SPENT_TIME_V
        verbose_name_plural = UserActivityCfg.SPENT_TIME_PLURAL_V


class DailytTips(models.Model):
    title = models.CharField(
        max_length=MAX_LEN,
        verbose_name="Название",
    )
    content = MarkdownxField(
        verbose_name="Текст (Markdown)",
    )
    pub_date = models.DateTimeField(
        verbose_name="Дата публикации",
        default=timezone.now
    )
    author = models.ForeignKey(
        User,
        verbose_name="Автор совета",
        on_delete=models.CASCADE
    )
    is_published = models.BooleanField(
        verbose_name="Опубликовано",
        default=False
    )
    external_link = models.URLField(
        verbose_name="Ссылка на внешний ресурс",
        blank=True,
        null=True,
    )
    rating = models.FloatField(
        verbose_name="Рейтинг",
        default=0.0,
        blank=True,
    )
    views_count = models.PositiveIntegerField(
        verbose_name="Количество просмотров",
        default=0,
    )

    class Meta:
        verbose_name = "Совет дня"
        verbose_name_plural = "Советы дня"

    def __str__(self):
        return self.title


class Achievement(models.Model):
    user_id = models.IntegerField(
        verbose_name="Telegram ID")
    username = models.CharField(
        verbose_name="Имя пользователя Telegram",
        max_length=255)
    achievement_name = models.CharField(
        verbose_name="Название достижения",
        max_length=255)
    achieved_at = models.DateTimeField(
        verbose_name="Дата достижения",
        default=timezone.now)

    class Meta:
        verbose_name = "Достижение"
        verbose_name_plural = "Достижения"

    def __str__(self):
        return f"{self.user_id} - {self.achievement_name}"


class DailyStatistics(models.Model):
    user_id = models.IntegerField(
        verbose_name="Telegram ID"
    )
    username = models.CharField(
        verbose_name="Имя пользователя Telegram",
        max_length=255)
    date = models.DateField(
        verbose_name="Дата",
        default=timezone.now)
    total_time = models.DurationField(
        verbose_name="Общее время"
    )
    total_trips = models.IntegerField(
        verbose_name="Общее количество выездов"
    )

    class Meta:
        verbose_name = "Дневная статистика"
        verbose_name_plural = "Дневная статистика"

    def __str__(self):
        return f"{self.username} - {self.date}"
