from dotenv import load_dotenv
import os

load_dotenv() 

class Config:
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = os.getenv("PORT")
    REDIS_PASSWORD = os.getenv("PASSWORD")
