import os 
from dotenv import load_dotenv

load_dotenv() 

BOT_TOKEN = os.getenv("BOT_TOKEN") 

DB_HOST = os.getenv("DB_HOST")
DB_PORT =os.getenv("DB_PORT")
DB_NAME =os.getenv("DB_NAME")
DB_USER =os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Multiple channels support
REQUIRED_CHANNELS = [c.strip() for c in os.getenv("REQUIRED_CHANNELS", "").split(",") if c.strip()]
CHANNEL_URLS = [u.strip() for u in os.getenv("CHANNEL_URLS", "").split(",") if u.strip()]
