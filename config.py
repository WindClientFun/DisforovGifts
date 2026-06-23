import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_БОТА")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x]
OWNER_USERNAME = "@disforov_sex"
OWNER_ID = int(os.getenv("OWNER_ID", "8599506400"))
ACTIVITY_CHAT_INVITE = "https://t.me/+lQJ9Jvf46cgyM2Iy"
ACTIVITY_CHAT_ID = int(os.getenv("ACTIVITY_CHAT_ID", "0"))
