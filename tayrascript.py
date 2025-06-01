from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def scrape_tayara_with_selenium(keyword, max_pages=5):
    base_url = f"https://www.tayara.tn/en/search/?q={keyword}"

    options = Options()
    options.add_argument("--headless")  # Comment this to see browser
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    current_page = 1
    total_products = 0

    while True:
        search_url = f"{base_url}&page={current_page}"
        print(f"\n📄 Loading page {current_page} : {search_url}")
        driver.get(search_url)

        print("⏳ Waiting for page to load ...")
        time.sleep(5)  # JS rendering time

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_articles = soup.find_all("article", class_="mx-0")

        if not product_articles:
            print(f"❌ No products found on page {current_page}. Ending pagination.")
            break

        print(f"🟢 Found {len(product_articles)} products on page {current_page}.\n")

        for index, article in enumerate(product_articles, start=1):
            total_products += 1

            # Extract link
            a_tag = article.find("a", href=True)
            product_link = "https://www.tayara.tn" + a_tag["href"] if a_tag else "No link"

            # Extract image URL
            img_tag = article.find("img")
            img_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else "No image"

            # Extract title
            title_tag = article.find("h2", class_="card-title")
            title = title_tag.get_text(strip=True) if title_tag else "No title"

            # Extract price
            price_tag = article.find("data")
            price = price_tag.get_text(strip=True) if price_tag else "No price"

            # Extract category
            category_span = article.find_all("span", class_="truncate")
            category = category_span[0].get_text(strip=True) if category_span else "No category"

            # Extract location and time
            location_span = article.find_all("span", class_="line-clamp-1")
            location_time = location_span[0].get_text(strip=True) if location_span else "No location/time"

            # Display extracted data
            print(f"➡️ Product {total_products}:")
            print(f"🔗 Link: {product_link}")
            print(f"📦 Title: {title}")
            print(f"💰 Price: {price}")
            print(f"🖼️ Image: {img_url}")
            print(f"📂 Category: {category}")
            print(f"📍 Location/Time: {location_time}")
            print("-" * 60)

        # Stop if max_pages is reached
        if current_page >= max_pages:
            print(f"🛑 Reached max pages limit ({max_pages}). Stopping.")
            break

        current_page += 1

    driver.quit()
    print(f"\n✅ Scraping finished. Total products scraped: {total_products}")

if __name__ == "__main__":
    keyword = input("Enter product keyword to search on Tayara: ")
    max_pages = int(input("Enter max number of pages to scrape (ex: 3): "))
    scrape_tayara_with_selenium(keyword, max_pages)
