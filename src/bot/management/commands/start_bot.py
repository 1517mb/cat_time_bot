import logging
from difflib import get_close_matches

import requests
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ...models import Company, UserActivity

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

JOIN_CO, SELECT_CO = range(2)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Привет! Вот список доступных команд:\n"
        "/help - Показать это сообщение с инструкциями.\n"
        "/join <Организация> - Прибыть к указанной организации.\n"
        "/leave - Покинуть текущую организацию и записать затраченное время.\n"
        "/mew - Получить случайное фото кота."
    )
    await update.message.reply_text(help_text)


async def get_similar_companies(company_name):
    """
    Searches for companies with names similar to the given company_name
    and returns a list of the closest matches (up to 2 matches with a
    similarity cutoff of 0.6).

    :param company_name: The company name to search for.
    :return: A list of strings of the closest company name matches.
    """
    similar_companies = await sync_to_async(list)(
        Company.objects.filter(name__icontains=company_name).values_list(
            "name", flat=True)
    )
    return get_close_matches(company_name, similar_companies, n=2, cutoff=0.6)


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    company_name = " ".join(context.args)

    if not company_name:
        await update.message.reply_text(
            "Пожалуйста, укажите название организации после команды /join.")
        return ConversationHandler.END

    active_activity = await sync_to_async(UserActivity.objects.filter(
        user_id=user_id, leave_time__isnull=True).exists)()

    if active_activity:
        await update.message.reply_text(
            "Вы ещё не покинули предыдущую организацию.")
        return ConversationHandler.END

    company, created = await sync_to_async(
        Company.objects.get_or_create)(name=company_name)
    if created:
        await update.message.reply_text(
            f"Вы прибыли в организацию {company_name}")
        await sync_to_async(UserActivity.objects.create)(
            user_id=user_id,
            username=username,
            company=company
        )
        return ConversationHandler.END
    else:
        similar_companies = await get_similar_companies(company_name)
        if similar_companies:
            similar_companies_text = "\n".join(
                [f"{i + 1}. {company}" for i, company in enumerate(
                    similar_companies)])
            reply_keyboard = [
                [KeyboardButton(company)] for company in similar_companies
            ] + [[KeyboardButton("Добавить новую организацию")]]
            await update.message.reply_text(
                f"Организации с названием \"{company_name}\" не найдено."
                f"Возможно, вы имели в виду:\n{similar_companies_text}\n"
                "Выберите из списка или добавьте новую организацию.",
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True)
            )
            return SELECT_CO
        else:
            await update.message.reply_text(
                f"Вы прибыли в организацию {company_name}")
            await sync_to_async(UserActivity.objects.create)(
                user_id=user_id,
                username=username,
                company=company
            )
            return ConversationHandler.END


async def select_company(
        update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    selected_company = update.message.text

    if selected_company == "Добавить новую организацию":
        await update.message.reply_text(
            "Пожалуйста, введите название новой организации")
        return JOIN_CO

    active_activity = await sync_to_async(UserActivity.objects.filter(
        user_id=user_id, leave_time__isnull=True).exists)()

    if active_activity:
        await update.message.reply_text(
            "Вы ещё не покинули предыдущую организацию.")
        return ConversationHandler.END

    company, created = await sync_to_async(
        Company.objects.get_or_create)(name=selected_company)
    await update.message.reply_text(
        f"Вы прибыли в организацию {selected_company}.",
        reply_markup=ReplyKeyboardRemove()
    )
    await sync_to_async(UserActivity.objects.create)(
        user_id=user_id,
        username=username,
        company=company
    )
    return ConversationHandler.END


async def add_new_company(
        update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    company_name = update.message.text

    active_activity = await sync_to_async(UserActivity.objects.filter(
        user_id=user_id, leave_time__isnull=True).exists)()

    if active_activity:
        await update.message.reply_text(
            "Вы ещё не покинули предыдущую организацию.")
        return ConversationHandler.END

    company, created = await sync_to_async(
        Company.objects.get_or_create)(name=company_name)
    await update.message.reply_text(
        f"Вы присоединились к новой организации {company_name}.",
        reply_markup=ReplyKeyboardRemove()
    )
    await sync_to_async(UserActivity.objects.create)(
        user_id=user_id,
        username=username,
        company=company
    )
    return ConversationHandler.END


async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    username = update.message.from_user.username

    try:
        activity = await sync_to_async(UserActivity.objects.select_related(
            "company").filter(
                user_id=user_id,
                leave_time__isnull=True).latest)("join_time")

        activity.leave_time = timezone.now()
        await sync_to_async(activity.save)()

        company_name = activity.company.name
        spent_time = activity.get_spent_time

        await update.message.reply_text(
            f"Вы покинули организацию {company_name}. "
            f"Затраченное время: {spent_time}.")

    except UserActivity.DoesNotExist:
        await update.message.reply_text(
            "Вы не прибыли ни к одной организации.")
    except Exception as e:
        logging.error(f"Ошибка при выполнении команды /leave: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке вашего запроса.")


async def mew(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    response = requests.get("https://api.thecatapi.com/v1/images/search")
    if response.status_code == 200:
        cat_photo_url = response.json()[0]["url"]
        await update.message.reply_photo(photo=cat_photo_url)
    else:
        await update.message.reply_text("Не удалось получить фото котика :(")


class Command(BaseCommand):
    help = "Запуск бота Телеграмм"

    def handle(self, *args, **options):
        application = ApplicationBuilder().token(
            settings.TELEGRAM_BOT_TOKEN).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("join", join)],
            states={
                SELECT_CO: [MessageHandler(
                    filters.TEXT & ~filters.COMMAND, select_company)],
                JOIN_CO: [MessageHandler(
                    filters.TEXT & ~filters.COMMAND, add_new_company)],
            },
            fallbacks=[CommandHandler(
                "cancel", lambda update, context: ConversationHandler.END)],
        )

        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("help", help))
        application.add_handler(CommandHandler("leave", leave))
        application.add_handler(CommandHandler("mew", mew))

        application.run_polling(allowed_updates=Update.ALL_TYPES)
