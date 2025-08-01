import os
import time
import re
import pandas as pd
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==============================
# 1. Load Environment Variables
# ==============================
load_dotenv()
IG_USERNAME = os.getenv("INSTAGRAM_USERNAME")
IG_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

# ==============================
# 2. Google Sheets Setup
# ==============================
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Instagram Food Creators").sheet1  # Use first sheet

# ==============================
# 3. Helper Function - Extract Email from Bio
# ==============================
def extract_email(text):
    email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    match = re.search(email_pattern, text)
    return match.group(0) if match else ""

# ==============================
# 4. Helper - Scrape posts for a hashtag
# ==============================
def scrape_hashtag_posts(page, tag, scrolls=10):
    print(f"Scraping posts for #{tag}...")
    page.goto(f"https://www.instagram.com/explore/tags/{tag}/")
    page.wait_for_selector("article a[href*='/p/']", timeout=15000)  # Wait for posts to load

    post_links = set()
    for _ in range(scrolls):  # Scroll multiple times to load more
        page.mouse.wheel(0, 3000)
        time.sleep(2)
        links = page.query_selector_all("article a[href*='/p/']")
        for link in links:
            href = link.get_attribute("href")
            if href and href.startswith("/p/"):
                post_links.add(href)
    return post_links

# ==============================
# 5. Main Function
# ==============================
def scrape_instagram_profiles():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        # Load previous session if available
        if os.path.exists("insta_session.json"):
            context = browser.new_context(storage_state="insta_session.json")
        else:
            context = browser.new_context()
        page = context.new_page()

        # ---- Login if first time ----
        if not os.path.exists("insta_session.json"):
            print("Logging in to Instagram...")
            page.goto("https://www.instagram.com/accounts/login/")
            time.sleep(5)
            page.fill("input[name='username']", IG_USERNAME)
            page.fill("input[name='password']", IG_PASSWORD)
            page.click("button[type='submit']")
            time.sleep(7)
            context.storage_state(path="insta_session.json")  # Save session

        # ---- Hashtags to search ----
        hashtags = ["nigerianfood", "naijafoodie", "nigerianchef", "foodie", 
        "africanfood", "food", "naijafood", "nigeria", "nigeriancuisine", "foodporn"]
        
        profile_links = set()
        for tag in hashtags:
            profile_links.update(scrape_hashtag_posts(page, tag))

        print(f"Collected {len(profile_links)} post links.")

        # ==============================
        # 6. Extract Profile Data
        # ==============================
        data = []
        for post_link in profile_links:
            try:
                page.goto(f"https://www.instagram.com{post_link}")
                time.sleep(3)

                # Get username from post
                username_element = page.query_selector("header a")
                if not username_element:
                    continue
                username = username_element.inner_text().strip()
                profile_url = "https://www.instagram.com/" + username

                # Go to profile
                page.goto(profile_url)
                time.sleep(4)

                # Extract profile info
                stats = page.query_selector_all("header li span")
                followers = stats[1].inner_text() if len(stats) > 1 else "0"
                following = stats[2].inner_text() if len(stats) > 2 else "0"
                posts = stats[0].inner_text() if len(stats) > 0 else "0"
                bio_element = page.query_selector("header section div.-vDIg span")
                bio = bio_element.inner_text() if bio_element else ""
                email = extract_email(bio)

                # Save data
                data.append([username, profile_url, bio, followers, following, posts, email])
                print(f"Scraped: {username}")
            except Exception as e:
                print(f"Error scraping {post_link}: {e}")

        browser.close()

    # ==============================
    # 7. Save to Google Sheets
    # ==============================
    df = pd.DataFrame(data, columns=["Username", "Profile URL", "Bio", "Followers", "Following", "Posts", "Email"])
    sheet.clear()
    sheet.append_row(df.columns.tolist())  # Add headers
    for row in df.values.tolist():
        sheet.append_row(row)

    print("Data pushed to Google Sheets successfully.")

# Run
if __name__ == "__main__":
    scrape_instagram_profiles()
