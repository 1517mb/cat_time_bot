from import_export import fields, resources

from .models import UserActivity


class UserActivityResource(resources.ModelResource):
    id = fields.Field(
        attribute="id", column_name="№")
    user_id = fields.Field(
        attribute="user_id", column_name="ID пользователя")
    username = fields.Field(
        attribute="username", column_name="Имя пользователя")
    company = fields.Field(
        attribute="company__name", column_name="Компания")
    join_time = fields.Field(
        attribute="join_time", column_name="Время прибытия")
    leave_time = fields.Field(
        attribute="leave_time", column_name="Время ухода")
    time_difference = fields.Field(
        attribute="time_difference", column_name="Общее время")

    class Meta:
        model = UserActivity
        fields = ("id",
                  "user_id",
                  "username",
                  "company",
                  "join_time",
                  "leave_time",
                  "time_difference")
        export_order = fields

    def dehydrate_company(self, obj):
        """Возвращаем название компании"""
        return obj.company.name

    def dehydrate_join_time(self, obj):
        """Возвращает человекочитаемый формат для join_time"""
        return obj.join_time.strftime('%d.%m.%Y %H:%M')

    def dehydrate_leave_time(self, obj):
        """Возвращает человекочитаемый формат для leave_time"""
        if obj.leave_time:
            return obj.leave_time.strftime('%d.%m.%Y %H:%M')
        return "Ещё не покинул"

    def dehydrate_time_difference(self, obj):
        """Возвращает дельту потраченного времени"""
        if obj.join_time and obj.leave_time:
            delta = obj.leave_time - obj.join_time
            total_seconds = delta.total_seconds()

            days = int(total_seconds // (3600 * 24))
            hours = int((total_seconds % (3600 * 24)) // 3600)
            minutes = int((total_seconds % 3600) // 60)

            if days > 0:
                return f"{days} д. {hours} ч. {minutes} мин."
            if hours > 0:
                return f"{hours} ч. {minutes} мин."
            return f"{minutes} мин."

        return "Ещё не покинул"
