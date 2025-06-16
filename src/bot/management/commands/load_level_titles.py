from django.core.management.base import BaseCommand

from bot.models import LevelTitle

LEVEL_TITLES = [
    (1, "Пользователь, который 'просто посмотреть'", "beginner"),
    (2, "Мастер перезагрузки роутера", "beginner"),
    (3, "Специалист по нажатию Ctrl+Alt+Del", "beginner"),
    (4, "Админ кофейной машины", "beginner"),
    (5, "Младший повелитель мышек", "beginner"),
    (6, "Сисадмин-стажёр (знает, где кнопка Power)", "beginner"),
    (7, "Эксперт по 'а оно само сломалось'", "intermediate"),
    (8, "Магистр парольной политики 'qwerty123'", "intermediate"),
    (9, "Гуру создания ярлыков на рабочем столе", "intermediate"),
    (10, "Сеньор по установке Windows", "intermediate"),
    (11, "Хранитель резервных копий (которые никогда не восстанавливаются)",
     "intermediate"),
    (12, "Повелитель патч-кордов", "intermediate"),
    (13, "Мастер перепрошивки BIOS (со спичками)", "advanced"),
    (14, "Специалист по бесконечным обновлениям", "advanced"),
    (15, "Легенда серверной комнаты (и холодильника в ней)", "advanced"),
    (16, "Джедай кабельных трасс", "advanced"),
    (17, "Волшебник регистрации доменов", "advanced"),
    (18, "Маг диагностики методом 'выключить-включить'", "expert"),
    (19, "Архитектор виртуальных машин (которые всегда падают)", "expert"),
    (20, "Главный по облакам (и тучам проблем)", "expert"),
    (21, "Император бэкапов", "expert"),
    (22, "Верховный жрец Active Directory", "expert"),
    (23, "Ниндзя сетевой безопасности", "legend"),
    (24, "Создатель бесконечных скриптов", "legend"),
    (25, "Оракул багов и глюков", "legend"),
    (30, "Идеолог цифровой трансформации", "legend"),
    (50, "Бог серверной комнаты", "legend"),
    (100, "Бессмертный Архитектор Систем", "legend"),
]


class Command(BaseCommand):
    help = "Загрузка начальных названий уровней"

    def handle(self, *args, **kwargs):
        for level, title, category in LEVEL_TITLES:
            LevelTitle.objects.update_or_create(
                level=level,
                defaults={
                    "title": title,
                    "category": category,
                    "min_experience": (level - 1) * 1000
                }
            )
        self.stdout.write(self.style.SUCCESS(
            f"Успешно загружено {len(LEVEL_TITLES)} названий уровней"
        ))
