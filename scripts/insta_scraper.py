# scripts/insta_scraper.py
import os
import json
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from db.connection import init_db
from db.models import InstagramProfile

# -----------------------------
# Load Environment
# -----------------------------
load_dotenv()

SESSION_FILE = "session.json"
TARGET_HASHTAG = ["naijafoodie, lagosfood, igbofood, africanfood, africanmeal, nigerianfood"]  # Example: scrape profiles from #foodie
MAX_PROFILES = 1000        # target number of profiles

# -----------------------------
# Session Management
# -----------------------------
def save_session(context):
    storage = context.storage_state()
    with open(SESSION_FILE, "w") as f:
        json.dump(storage, f)
    print("💾 Session saved successfully.")

def load_session_if_exists(context):
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            storage_state = json.load(f)
        cookies = storage_state.get("cookies", [])
        if isinstance(cookies, list):
            context.add_cookies(cookies)
            print("✅ Session loaded successfully (cookies added).")
            return True
    return False

# -----------------------------
# Instagram Scraper
# -----------------------------
def login_instagram(page):
    print("🌍 Opening Instagram login page...")
    page.goto("https://www.instagram.com/accounts/login/", timeout=60000)

    print("🔑 Please log in manually within 60 seconds...")
    page.wait_for_timeout(60000)
    print("⏳ Login time finished, continuing...")

def scrape_instagram_profiles():
    print("🚀 Starting Instagram scraper...")

    # Init DB
    init_db()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        # Load or login session
        if not load_session_if_exists(context):
            page = context.new_page()
            login_instagram(page)
            save_session(context)
        else:
            page = context.new_page()
            page.goto("https://www.instagram.com/", timeout=120000)

        # Go to hashtag page
        hashtag_url = f"https://www.instagram.com/explore/tags/{TARGET_HASHTAG}/"
        print(f"📌 Navigating to hashtag page: {hashtag_url}")
        page.goto(hashtag_url, timeout=60000)

        scraped_profiles = set()
        while len(scraped_profiles) < MAX_PROFILES:
            # Extract profile links from visible posts
            links = page.locator("a").all()
            for link in links:
                href = link.get_attribute("href")
                if href and href.startswith("/") and len(href.split("/")) == 3:  # e.g. /username/
                    username = href.strip("/")
                    if username not in scraped_profiles:
                        scraped_profiles.add(username)
                        print(f"📸 Found profile: {username}")

                        # Save in DB
                        InstagramProfile(
                            username=username
                        ).save()

                        if len(scraped_profiles) >= MAX_PROFILES:
                            break

            # Scroll to load more
            page.mouse.wheel(0, 2000)
            time.sleep(2)

        browser.close()
        print(f"✅ Finished scraping {len(scraped_profiles)} profiles!")

# -----------------------------
# Run Script
# -----------------------------
if __name__ == "__main__":
    scrape_instagram_profiles()
