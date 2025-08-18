from mongoengine import connect
import os

def init_db():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/instagram_scraper")
    connect(host=mongo_uri)
    print(f"Connected to MongoDB at {mongo_uri}")