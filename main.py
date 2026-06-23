import logging
import asyncio
from threading import Thread

from telegram.ext import ApplicationBuilder

from config import BOT_TOKEN
from database import init_db
from handlers import get_handlers, schedule_jobs

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def run_health_server():
    try:
        import os
        from http.server import HTTPServer, BaseHTTPRequestHandler

        port = int(os.environ.get("PORT", "8000"))

        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")

            def log_message(self, *a):
                pass

        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        server.serve_forever()
    except Exception:
        pass


def main():
    if not BOT_TOKEN or BOT_TOKEN == "ВАШ_ТОКЕН_БОТА":
        logger.error("BOT_TOKEN не настроен!")
        return

    init_db()
    logger.info("База данных инициализирована")

    t = Thread(target=run_health_server, daemon=True)
    t.start()
    logger.info("Health-check сервер запущен на порту 8000")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    for handler in get_handlers():
        app.add_handler(handler)

    schedule_jobs(app)
    logger.info("Бот запущен!")

    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
