# cat_time_bot
![Лицензия](https://img.shields.io/github/license/hydrospirt/cat_time_bot)

### Текущая версия

**0.4 alpha**

Список всех изменений: [Ссылка.](https://github.com/hydrospirt/cat_time_bot/blob/master/CHANGE_LIST.md)

### О проекте
**Cat Time Bot** — это телеграм-бот, который не только считает время вашего пребывания, но и отправляет милых котиков! Представьте себе, как удобно иметь автоматизированный процесс контроля времени, который мгновенно экспортирует данные в Excel таблицу через Django Admin. Этот бот станет вашим незаменимым помощником в организации рабочего времени и повысит вашу продуктивность. Не упустите возможность добавить немного радости и эффективности в свой рабочий день с **cat_time_bot**!

### Преимущества

- 🤖 **Автоматизация**: Автоматизированный процесс контроля времени, который экономит ваше время и усилия.
- 🛠️ **Удобство**: Мгновенный доступ к данным через Django Admin.
- 💪 **Мотивация**: Милые котики помогают поддерживать мотивацию и позитивное настроение.
- 🌦️ **Погода**: Встроенный прогноз погоды с указанием температуры, влажности, давления и направления ветра.
- 🐾 **Кошачий стиль**: Уникальные кошачьи смайлики и эмодзи для каждого действия.

## Технологии
- Python 3.12
- Django
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
cd ./pokemon-unite-site/ &&
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
- Создайте переменные окружения в основной папке проекта "pokemon-unite-site"
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
