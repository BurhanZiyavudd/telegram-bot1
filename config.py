import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")