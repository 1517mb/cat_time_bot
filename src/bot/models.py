import itertools
from datetime import timedelta

from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone
from markdownx.models import MarkdownxField

from core.constants import (
    MAX_LEN,
    AchievementCfg,
    CompanyCfg,
    DailyStatisticsCfg,
    DailytTipsCfg,
    QuoteCfg,
    TagCfg,
    UserActivityCfg,
    UserRankCfg,
)
from core.utils import cyrillic_slugify


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
    edited = models.BooleanField(default=UserActivityCfg.EDITED_DEFAULT,
                                 verbose_name=UserActivityCfg.EDITED_V)
    edit_count = models.PositiveIntegerField(
        default=UserActivityCfg.EDIT_COUNT_DEFAULT,
        verbose_name=UserActivityCfg.EDIT_COUNT_V)

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


class UserRank(models.Model):
    user_id = models.IntegerField(
        unique=UserRankCfg.USER_ID_UNIQUE,
        verbose_name=UserRankCfg.USER_ID_V
    )
    experience = models.PositiveIntegerField(
        verbose_name=UserRankCfg.EXP_V,
        default=UserRankCfg.EXP_DEFAULT)
    level = models.PositiveIntegerField(
        verbose_name=UserRankCfg.LEVEL_V,
        default=UserRankCfg.LEVEL_DEFAULT
    )
    total_time = models.DurationField(
        verbose_name=UserRankCfg.TOTAL_TIME_V,
        default=timedelta()
    )
    visits_count = models.PositiveIntegerField(
        verbose_name=UserRankCfg.VISITS_COUNT_V,
        default=UserRankCfg.VISITS_COUNT_DEFAULT
    )

    class Meta:
        verbose_name = UserRankCfg.META_NAME
        verbose_name_plural = UserRankCfg.META_PL_NAME

    def __str__(self):
        return f"Уровень {self.level} (Опыт: {self.experience})"


class Tag(models.Model):
    name = models.CharField(
        verbose_name=TagCfg.NAME_V,
        max_length=TagCfg.MAX_LEN_NAME,
        unique=True,
        validators=[
            MinLengthValidator(
                limit_value=3,
                message="Название тега должно содержать минимум 3 символа")]
    )
    slug = models.SlugField(
        verbose_name=TagCfg.SLUG_V,
        max_length=TagCfg.MAX_LEN_SLUG,
        unique=TagCfg.UNIQUE_SLUG,
        blank=True
    )

    class Meta:
        verbose_name = TagCfg.META_NAME
        verbose_name_plural = TagCfg.META_PL_NAME

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self._should_regenerate_slug():
            self.slug = self._generate_unique_slug(cyrillic_slugify(self.name))
        super().save(*args, **kwargs)

    def _should_regenerate_slug(self):
        return not self.slug or (
            self.pk and self.name != self.__class__.objects.get(
                pk=self.pk).name)

    def _generate_unique_slug(self, base_slug):
        for i in itertools.count(1):
            slug_candidate = (base_slug if i == 1 else
                              f"{base_slug}-{i - 1}")
            if not (self.__class__.objects
                    .filter(slug=slug_candidate)
                    .exclude(pk=self.pk).exists()):
                return slug_candidate[:TagCfg.MAX_LEN_SLUG]
            if i > 100:
                raise ValueError(
                    "Генерация пули завершилась неудачей после 100 попыток")


class DailytTips(models.Model):
    title = models.CharField(
        max_length=MAX_LEN,
        verbose_name=DailytTipsCfg.VERBOSE_NAME
    )
    content = MarkdownxField(
        verbose_name=DailytTipsCfg.CONTENT_V,
    )
    pub_date = models.DateTimeField(
        verbose_name=DailytTipsCfg.PUB_DATE_V,
        default=timezone.now
    )
    author = models.ForeignKey(
        User,
        verbose_name=DailytTipsCfg.AUTHOR_V,
        on_delete=models.CASCADE
    )
    is_published = models.BooleanField(
        verbose_name=DailytTipsCfg.IS_PUBLISHED_V,
        default=False
    )
    external_link = models.URLField(
        verbose_name=DailytTipsCfg.EXTERNAL_LINK_V,
        blank=True,
        null=True,
    )
    rating = models.FloatField(
        verbose_name=DailytTipsCfg.RATING_V,
        default=DailytTipsCfg.RATING_DEFAULT,
        blank=True,
    )
    views_count = models.PositiveIntegerField(
        verbose_name=DailytTipsCfg.VIEWS_V,
        default=DailytTipsCfg.VIEWS_DEFAULT,
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name=DailytTipsCfg.TAGS_V,
        blank=DailytTipsCfg.TAGS_BLANK,
        related_name=DailytTipsCfg.TAGS_RELATED_NAME
    )

    class Meta:
        verbose_name = DailytTipsCfg.META_NAME
        verbose_name_plural = DailytTipsCfg.META_PL_NAME

    def __str__(self):
        return self.title


class Achievement(models.Model):
    user_id = models.IntegerField(
        verbose_name=AchievementCfg.USER_ID_V)
    username = models.CharField(
        verbose_name=AchievementCfg.USERNAME_V,
        max_length=MAX_LEN)
    achievement_name = models.CharField(
        verbose_name=AchievementCfg.ACHIEVEMENT_NAME_V,
        max_length=MAX_LEN)
    achieved_at = models.DateTimeField(
        verbose_name=AchievementCfg.ACHIEVED_AT_V,
        default=timezone.now)

    class Meta:
        verbose_name = AchievementCfg.META_NAME
        verbose_name_plural = AchievementCfg.META_PL_NAME

    def __str__(self):
        return f"{self.user_id} - {self.achievement_name}"

    @classmethod
    async def create_achievement(cls, user_id: int, username: str, name: str):
        """
        Создает новое достижение для пользователя

        Args:
            user_id (int): Telegram ID пользователя
            username (str): Имя пользователя Telegram
            name (str): Название достижения

        Returns:
            None
        """
        await sync_to_async(cls.objects.create)(
            user_id=user_id,
            username=username,
            achievement_name=name
        )


class DailyStatistics(models.Model):
    user_id = models.IntegerField(
        verbose_name=DailyStatisticsCfg.USER_ID_V
    )
    username = models.CharField(
        verbose_name=DailyStatisticsCfg.USERNAME_V,
        max_length=255)
    date = models.DateField(
        verbose_name=DailyStatisticsCfg.DATE_V,
        default=timezone.now)
    total_time = models.DurationField(
        verbose_name=DailyStatisticsCfg.TOTAL_TIME_V
    )
    total_trips = models.IntegerField(
        verbose_name=DailyStatisticsCfg.TOTAL_TRIPS_V
    )

    class Meta:
        verbose_name = DailyStatisticsCfg.META_NAME
        verbose_name_plural = DailyStatisticsCfg.META_PL_NAME

    def __str__(self):
        return f"{self.username} - {self.date}"


class Quote(models.Model):
    text = models.TextField(
        verbose_name=QuoteCfg.TEXT_V)
    author = models.CharField(
        verbose_name=QuoteCfg.AUTHOR_V,
        max_length=QuoteCfg.MAX_LEN_AUTHOR)
    source = models.CharField(
        verbose_name=QuoteCfg.SOURCE_V,
        max_length=QuoteCfg.MAX_LEN_SOURCE
    )
    tags = models.CharField(
        verbose_name=QuoteCfg.TAGS_V,
        max_length=QuoteCfg.MAX_LEN_TAGS,
        blank=QuoteCfg.BLANK_TAGS)  # ???
    is_active = models.BooleanField(
        verbose_name=QuoteCfg.IS_ACTIVE_V,
        default=QuoteCfg.IS_ACTIVE_DEFAULT
    )

    class Meta:
        verbose_name = QuoteCfg.META_NAME
        verbose_name_plural = QuoteCfg.META_PL_NAME

    def __str__(self):
        return f"{self.author} - {self.source}"
