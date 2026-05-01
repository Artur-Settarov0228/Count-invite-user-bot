import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime

logger = logging.getLogger("app_logger")
logger.setLevel(logging.DEBUG)

if not os.path.exists("logs"):
    os.makedirs("logs")

# format
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
)

# console
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# file (7 kunda o‘chadi)
file_handler = TimedRotatingFileHandler(
    f"logs/app.log {datetime.now().strftime('%Y-%m-%d')}",
    when="D",        # har kuni yangi file
    interval=1,
    backupCount=7    # faqat 7 kun saqlaydi
)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)
