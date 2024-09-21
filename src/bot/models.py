from django.db import models
from django.utils import timezone

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
