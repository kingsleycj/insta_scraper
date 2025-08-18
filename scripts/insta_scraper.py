import os
import requests
import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from db.connection import init_db
from db.models import InstagramProfile

# Initialize DB
init_db()

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
SESSION_ID = os.getenv("INSTAGRAM_SESSION_ID")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# Setup MongoDB
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
profiles = db["profiles"]

# Setup Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google_service.json", scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open_by_key(GOOGLE_SHEET_ID).sheet1

# Instagram headers
headers = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": f"sessionid={SESSION_ID};"
}

def fetch_hashtag_posts(hashtag, limit=20):
    """Fetch posts from a hashtag JSON endpoint"""
    url = f"https://www.instagram.com/explore/tags/{hashtag}/?__a=1&__d=dis"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"Failed to fetch {hashtag}: {r.status_code}")
        return []
    
    try:
        data = r.json()
        edges = data["graphql"]["hashtag"]["edge_hashtag_to_media"]["edges"]
        posts = [edge["node"]["owner"]["id"] for edge in edges[:limit]]
        return posts
    except Exception as e:
        print("Error parsing hashtag JSON:", e)
        return []

def fetch_profile(username):
    """Fetch Instagram profile info via JSON"""
    url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"Failed to fetch profile {username}")
        return None

    try:
        data = r.json()["graphql"]["user"]
        profile = {
            "username": data["username"],
            "full_name": data.get("full_name", ""),
            "bio": data.get("biography", ""),
            "followers": data["edge_followed_by"]["count"],
            "following": data["edge_follow"]["count"],
            "posts_count": data["edge_owner_to_timeline_media"]["count"],
            "email": data.get("business_email", ""),
            "profile_pic": data.get("profile_pic_url_hd", ""),
            "last_scraped": datetime.datetime.utcnow()
        }
        return profile
    except Exception as e:
        print("Error parsing profile JSON:", e)
        return None

def save_to_mongo(profile):
    """Insert or update profile in MongoDB"""
    if not profile:
        return
    profiles.update_one(
        {"username": profile["username"]},
        {"$set": profile},
        upsert=True
    )

def export_to_sheets():
    """Export MongoDB data to Google Sheets"""
    all_profiles = list(profiles.find())
    rows = [["Username", "Full Name", "Bio", "Followers", "Following", "Posts", "Email", "Profile Pic"]]
    for p in all_profiles:
        rows.append([
            p["username"], p["full_name"], p["bio"], p["followers"], 
            p["following"], p["posts_count"], p["email"], p["profile_pic"]
        ])
    sheet.clear()
    sheet.append_rows(rows)

if __name__ == "__main__":
    hashtags = ["nigerianfood", "naijafoodie", "nigerianchef", "lagosfoodie"]
    scraped = set()

    for tag in hashtags:
        print(f"Scraping #{tag}...")
        user_ids = fetch_hashtag_posts(tag)
        for uid in user_ids:
            # Normally you'd need to map UID -> username (IG obfuscates this now)
            # For now, placeholder usernames
            username = f"user_{uid}"
            if username not in scraped:
                profile = fetch_profile(username)
                if profile:
                    save_to_mongo(profile)
                scraped.add(username)

    export_to_sheets()
    print("✅ Scraping complete. Data in MongoDB + Google Sheets.")
# This script scrapes Instagram profiles based on hashtags, saves them to MongoDB, and exports the data to Google Sheets.
# Make sure to set up your environment variables and Google Sheets API credentials before running.