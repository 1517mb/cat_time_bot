from django.db import models
from django.utils import timezone
from core.constants import MAX_LEN, CompanyCfg


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
    user_id = models.IntegerField()
    username = models.CharField(max_length=MAX_LEN,
                                blank=True,
                                null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    join_time = models.DateTimeField(default=timezone.now)
    leave_time = models.DateTimeField(blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.username} в {self.company.name}"

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
