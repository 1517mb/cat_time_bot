# cat_time_bot
![Лицензия](https://img.shields.io/github/license/hydrospirt/cat_time_bot)

### Версия

0.0.1 alpha

### О проекте
cat_time_bot - это телеграм считающий время пребывания и отправляющий котов.
Приложение помогает автоматизировать процесс контроля времени для последущего экспорта в Excel таблицу.

## Технологии
- Python
- Django
- django-import-export
- python-telegram-bot

## Инструкция

## Установка для разработки:<a name="installation"></a>
- Клонируйте проект на свой компьютер:
```
git clone git@github.com:hydrospirt/cat_time_bot.git
```
- Установите и активируйте виртуальное окружение c Python 3.12
```
cd ./pokemon-unite-site/ &&
py -3.12 -m venv venv
```
Для Windows:
```
source venv/Scripts/Activate
```
Для Linux
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
SECRET_KEY="Секретный код Django"
TELEGRAM_BOT_TOKEN="Секретный токен @BotFather"
```
## Инструкции для запуска на localhost
- Запустить скрипт:
```bash
chmod +x setup.sh

./setup.sh
```
- Запустить сервер и перейти http://127.0.0.1:8000/:
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
