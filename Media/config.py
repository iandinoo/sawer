import os
import logging
from os import getenv
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

load_dotenv(".env")

API_ID = getenv("API_ID", "")

API_HASH = getenv("API_HASH", "")

BOT_TOKEN = getenv("BOT_TOKEN", "")

MONGO_DB_URL = getenv("MONGO_DB_URL", "")

OWNER_ID = [int(x) for x in (os.environ.get("OWNER_ID", "").split())]

BOT_WORKERS = getenv("BOT_WORKERS", "4")

LOG_FILE_NAME = "kantorpos.txt"
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler(LOG_FILE_NAME, maxBytes=50000000, backupCount=10),
        logging.StreamHandler(),
    ],
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
