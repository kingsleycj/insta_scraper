# db/connection.py
import os
from mongoengine import connect
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

def init_db():
    connect(
        db=MONGO_DB,
        host=MONGO_URI,
        alias="default"
    )
    print(f"Connected to MongoDB database: {MONGO_DB}")