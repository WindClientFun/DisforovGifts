import logging
from telegram.ext import ApplicationBuilder

from config import BOT_TOKEN
from database import init_db
from handlers import get_handlers, schedule_jobs

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    if not BOT_TOKEN or BOT_TOKEN == "ВАШ_ТОКЕН_БОТА":
        logger.error("BOT_TOKEN не настроен! Укажите токен в .env")
        return

    init_db()
    logger.info("База данных инициализирована")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    for handler in get_handlers():
        app.add_handler(handler)

    schedule_jobs(app)
    logger.info("Бот запущен!")

    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
