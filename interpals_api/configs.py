from dotenv import load_dotenv
import os

load_dotenv() 

class Config:
    DB_URL = os.getenv("DATABASE_URL")
    API_KEY = os.getenv("API_KEY")
    DEBUG = os.getenv("DEBUG", "False") == "True"
