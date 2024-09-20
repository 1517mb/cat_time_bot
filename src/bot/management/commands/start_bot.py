import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Application
from django.utils import timezone
from difflib import get_close_matches

from ...models import Company, UserActivity

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

JOIN_CO, SELECT_CO = range(2)


def help(update: Update, context: CallbackContext) -> None:
    help_text = (
        "Привет! Вот список доступных команд:\n"
        "/help - Показать это сообщение с инструкциями.\n"
        "/join <Организация> - Присоединиться к указанной организации.\n"
        "/leave - Покинуть текущую организацию и записать затраченное время."
    )
    update.message.reply_text(help_text)


def get_similar_companies(company_name):
    companies = Company.objects.all()
    similar_companies = get_close_matches(company_name, [company.name for company in companies], n=2, cutoff=0.6)
    return similar_companies


def join(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    company_name = ' '.join(context.args)

    if not company_name:
        update.message.reply_text("Пожалуйста, укажите название организации после команды /join.")
        return ConversationHandler.END

    company, created = Company.objects.get_or_create(name=company_name)
    if created:
        update.message.reply_text(f"Вы прибыли в организацию {company_name}")
        UserActivity.objects.create(
            user_id=user_id,
            username=username,
            company=company
        )
        return ConversationHandler.END
    else:
        similar_companies = get_similar_companies(company_name)
        if similar_companies:
            similar_companies_text = "\n".join([f"{i + 1}. {company}" for i, company in enumerate(similar_companies)])
            reply_keyboard = [[KeyboardButton(company)] for company in similar_companies] + [[KeyboardButton("Добавить новую организацию")]]
            update.message.reply_text(
                f"Организации с названием \"{company_name}\" не найдено. Возможно, вы имели в виду:\n{similar_companies_text}\n"
                "Выберите из списка или добавьте новую организацию.",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            )
            return SELECT_CO
        else:
            update.message.reply_text(f"Вы прибыли в организацию {company_name}")
            UserActivity.objects.create(
                user_id=user_id,
                username=username,
                company=company
            )
            return ConversationHandler.END


def select_company(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    selected_company = update.message.text

    if select_company == "Добавить новую организацию":
        update.message.reply_text("Пожалуйста, введите название новой организации")
        return JOIN_CO
    company, created = Company.objects.get_or_create(name=selected_company)
    update.message.reply_text(f"Вы прибыли в организацию {selected_company}.")
    UserActivity.objects.create(
        user_id=user_id,
        username=username,
        company=company
    )
    return ConversationHandler.END

def add_new_company(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    company_name = update.message.text

    company, created = Company.objects.get_or_create(name=company_name)
    update.message.reply_text(f'Вы присоединились к новой организации {company_name}.')
    UserActivity.objects.create(
        user_id=user_id,
        username=username,
        company=company
    )
    return ConversationHandler.END

def leave(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    try:
        activity = UserActivity.objects.filter(user_id=user_id, leave_time__isnull=True).latest("join_time")
        activity.leave_time = timezone.now()
        activity.save()
        update.message.reply_text(f"Вы покинули организацию {activity.company.name}. Затраченное время: {activity.get_spent_time()}.")
    except UserActivity.DoesNotExist:
        update.message.reply_text("Вы не прибыли ни к одной организации.")


def main() -> None:
    application = Application.builder().token("TELEGRAM_BOT_TOKEN").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('join', join)],
        states={
            SELECT_CO: [MessageHandler(lambda message: not message.text.startswith('/'), select_company)],
            JOIN_CO: [MessageHandler(lambda message: not message.text.startswith('/'), add_new_company)],
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("leave", leave))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
