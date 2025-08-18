import os
import time
import pandas as pd
from dotenv import load_dotenv
from instagrapi import Client
from db.connection import init_db
from db.models import InstagramProfile
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()

# Google Sheets setup
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
CLIENT = gspread.authorize(CREDS)

# MongoDB init
init_db()

# Instagram client
cl = Client()
cl.load_settings("insta_session.json")

try:
    cl.get_timeline_feed()  # test if session works
except Exception:
    print("⚠️ Session expired. Login again with credentials.")
    USERNAME = os.getenv("INSTA_USERNAME")
    PASSWORD = os.getenv("INSTA_PASSWORD")
    cl.login(USERNAME, PASSWORD)
    cl.dump_settings("insta_session.json")

# -------------------------------
# Scraping logic
# -------------------------------
def scrape_profiles(usernames):
    data = []
    for username in usernames:
        try:
            user = cl.user_info_by_username(username)
            profile = {
                "username": user.username,
                "profile_url": f"https://instagram.com/{user.username}",
                "bio": user.biography,
                "followers": user.follower_count,
                "following": user.following_count,
                "posts": user.media_count,
                "email": user.public_email if user.public_email else ""
            }

            # Save to MongoDB
            if not InstagramProfile.objects(username=user.username):
                InstagramProfile(**profile).save()
            else:
                print(f"⚠️ Skipping duplicate: {user.username}")

            data.append(profile)
            time.sleep(2)  # avoid Instagram ban
        except Exception as e:
            print(f"❌ Error scraping {username}: {e}")
    return data

# -------------------------------
# Extract usernames from hashtags
# -------------------------------
def get_usernames_from_hashtags(hashtags, posts_per_hashtag=20):
    usernames = set()
    for tag in hashtags:
        try:
            medias = cl.hashtag_medias_recent(tag, amount=posts_per_hashtag)
            for m in medias:
                usernames.add(m.user.username)
            print(f"✅ {len(medias)} posts fetched from #{tag}")
            time.sleep(5)  # avoid rate limiting
        except Exception as e:
            print(f"❌ Error fetching from #{tag}: {e}")
    return list(usernames)

# -------------------------------
# Save to Google Sheets
# -------------------------------
def save_to_google_sheets(data):
    df = pd.DataFrame(data)
    sheet = CLIENT.open_by_key(SHEET_ID).sheet1
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())
    print("✅ Data saved to Google Sheets!")

# -------------------------------
# MAIN
# -------------------------------
if __name__ == "__main__":
    hashtags_to_search = ["nigerianfood", "lagosfoodie", "naijafood"]  # change as needed
    usernames_to_scrape = get_usernames_from_hashtags(hashtags_to_search, posts_per_hashtag=10)

    print(f"🔎 Found {len(usernames_to_scrape)} unique usernames.")

    results = scrape_profiles(usernames_to_scrape)

    if results:
        save_to_google_sheets(results)
        print("✅ Scraping complete. Data stored in MongoDB + Google Sheets.")
    else:
        print("⚠️ No data scraped.")

