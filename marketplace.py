from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import csv

def scrape_facebook_marketplace(keyword, max_scrolls=5, location_id="108926339127575"):
    url = f"https://www.facebook.com/marketplace/{location_id}/search/?query={keyword}"

    options = Options()
    options.add_argument("--headless")  # Set to False if you want to see browser
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(3)

    for i in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        print(f"📜 Scroll {i + 1}/{max_scrolls}")
        time.sleep(3)

    print("⏳ Waiting 5 seconds before scraping...")
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    listings = [div for div in soup.find_all("div", class_="x9f619") if div.find("a", href=True)]
    print(f"\n✅ Found {len(listings)} potential listings.\n")

    # 📤 Prepare data for CSV
    data = [["Title", "Price", "Location", "Link", "Image"]]

    for idx, div in enumerate(listings, 1):
        try:
            link_tag = div.find("a", href=True)
            href = "https://www.facebook.com" + link_tag['href']

            title = div.find("span", class_="x1lliihq x6ikm8r x10wlt62 x1n2onr6")
            title_text = title.get_text(strip=True) if title else "N/A"

            price = div.find("span", string=lambda text: text and "TND" in text)
            price_text = price.get_text(strip=True) if price else "N/A"

            location = div.find_all("span", class_="x1lliihq x6ikm8r x10wlt62 x1n2onr6")
            location_text = location[1].get_text(strip=True) if len(location) > 1 else "N/A"

            image_tag = div.find("img")
            image_src = image_tag['src'] if image_tag else "No image"

            print(f"🔹 Item {idx}")
            print(f"📦 Title: {title_text}")
            print(f"💰 Price: {price_text}")
            print(f"📍 Location: {location_text}")
            print(f"🔗 Link: {href}")
            print(f"🖼️ Image: {image_src}")
            print("-" * 50)

            data.append([title_text, price_text, location_text, href, image_src])

        except Exception as e:
            print(f"⚠️ Error parsing item {idx}: {e}")

    driver.quit()

    # 💾 Save to CSV
    filename = f"facebook_marketplace_{keyword.replace(' ', '_')}.csv"
    with open(filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(data)

    print(f"\n🏁 Done scraping. Data saved to {filename}.")

if __name__ == "__main__":
    kw = input("🔎 Enter search keyword: ")
    scrolls = int(input("↕️ Enter scroll count (e.g., 5): "))
    scrape_facebook_marketplace(kw, scrolls)
