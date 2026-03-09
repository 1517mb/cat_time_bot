# cat_time_bot
![Лицензия](https://img.shields.io/github/license/hydrospirt/cat_time_bot)
<a href="https://www.python.org/" style="text-decoration: none;"><img src="https://img.shields.io/badge/Python-3.12.9-blue?style=flat&logo=python&logoColor=ffdd54" height="20" alt="python"></a>
<a href="https://www.djangoproject.com/" style="text-decoration: none;"><img src="https://img.shields.io/badge/Django-6.0.2-blue?style=flat&logo=django" height="20" alt="django"></a>
<br>
<a href="https://github.com/League-Of-Free-Internet/empty_project/branches" style="text-decoration: none;"><img src="https://img.shields.io/github/commit-activity/w/1517mb/cat_time_bot" height="20" alt="commit-activity"></a>
<a href="https://github.com/1517mb/cat_time_bot/branches" style="text-decoration: none;"><img src="https://img.shields.io/github/last-commit/1517mb/cat_time_bot" height="20" alt="last-commit"></a>
<a href="https://github.com/orgs/League-Of-Free-Internet/projects/2" style="text-decoration: none;"><img src="https://img.shields.io/github/issues/1517mb/cat_time_bot" height="20" alt="issues"></a>
<br>
<img src="https://img.shields.io/github/repo-size/1517mb/cat_time_bot" height="20" alt="repo-size">
    <img src="https://img.shields.io/github/languages/code-size/1517mb/cat_time_bot" height="20" alt="code-size">

### Текущая версия

**v0.6.5-alpha** -> [Скачать](https://github.com/1517mb/cat_time_bot/releases/tag/v0.6.5-alpha)

Список всех изменений: [Ссылка.](https://github.com/1517mb/cat_time_bot/blob/master/CHANGE_LIST.md)

⚠️ Статус проекта: MVP / В разработке > Обратите внимание: сам проект и данное README находятся в стадии активной разработки. На текущий момент бот запущен и функционирует в формате минимально жизнеспособного продукта (MVP).

### О проекте
**Cat Time Bot** - это Telegram-бот, предназначенный для учета времени и организации рабочего процесса. Главная задача проекта - автоматизация трекинга активности пользователей с возможностью последующего экспорта собранных данных в формате Excel через панель управления Django Admin. Бот сочетает в себе инструменты для повышения продуктивности с элементами игрофикации, помогая оптимизировать рабочий день.

### Преимущества

- 🤖 **Автоматизация учета:** Систематизация контроля рабочего времени для минимизации рутинных задач.
- 🛠️ **Администрирование и экспорт:** Централизованное управление данными и быстрая генерация отчетов через интегрированную панель Django Admin.
- 🌦️ **Метеорологическая сводка:** Встроенный модуль прогноза погоды с предоставлением актуальных данных (температура, влажность, атмосферное давление и направление ветра).
- 🐾 **Пользовательский интерфейс и вовлеченность:** Тематическая стилизация взаимодействия с использованием специализированных эмодзи и отправкой изображений котов для поддержания позитивного пользовательского опыта.

## Технологии
- Python 3.12
- Django 6
- django-import-export
- python-telegram-bot
- aiohttp (для асинхронных HTTP-запросов)
- APScheduler (для планирования задач)

## Инструкция

- Клонируйте проект на свой компьютер:
```
git clone git@github.com:hydrospirt/cat_time_bot.git
```
- Установите и активируйте виртуальное окружение c Python 3.12
```
cd ./src/ &&
py -3.12 -m venv venv
```
- Для Windows:
```
source venv/Scripts/Activate
```
- Для Linux
```
source venv/bin/activate
```
- Установите зависимости из файла requirements.txt
```
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```
- Создайте переменные окружения в основной папке проекта "cat_time_bot"
```
touch .env
```
- Добавьте ваши данные в файл .env
```
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost
SECRET_KEY=Секретный код Django
TELEGRAM_BOT_TOKEN=Секретный токен @BotFather
TRUSTED_ORIGINS=http://127.0.0.1,http://localhost и тд.
OPENWEATHER_API_KEY=ключ от API например: 1a2b3c4d5e6f7g8h
TELEGRAM_GROUP_CHAT_ID=ИД канала например: -1001234517895
```
## Инструкции для запуска на localhost
- Запустить скрипт:
```bash
chmod +x setup.sh

./setup.sh
```
- Запустить сервер и перейти:
```bash
python3 manage.py runserver
```
- Запустить Telegram бота:
```bash
python3 manage.py start_bot
```

## Проект разрабатывали:
| <!-- --> | <!-- -->      | <!-- -->    |
|----------|---------------|-------------|
| Эдуард Гумен | Python-разработчик | [Cтраница GitHub](https://github.com/hydrospirt) |


## Лицензия

Пожалуйста, ознакомьтесь с [MIT license](https://github.com/hydrospirt/cat_time_bot?tab=MIT-1-ov-file)
