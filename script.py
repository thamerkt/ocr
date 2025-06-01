import time
import csv
import os
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

CSV_FILE = 'rne_companies.csv'

def start_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Remove for debugging
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    return webdriver.Chrome(options=options)

def get_scraped_regions():
    scraped = set()
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                scraped.add(row['region'])
    return scraped

def scrape_rne_by_region():
    scraped_regions = get_scraped_regions()

    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=[
            'region', 'company_name_fr', 'commercial_name', 'name_arabic', 'full_name_arabic'
        ])
        if os.stat(CSV_FILE).st_size == 0:
            writer.writeheader()

        driver = None
        try:
            driver = start_driver()
            driver.set_page_load_timeout(180)
            wait = WebDriverWait(driver, 30)

            driver.get("https://www.registre-entreprises.tn/rne-public/#/recherche-pm")
            time.sleep(10)

            bureau_select = wait.until(EC.element_to_be_clickable((By.ID, "mat-select-5")))
            bureau_select.click()
            time.sleep(2)

            options_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'mat-option')))
            all_regions = [opt.text.strip() for opt in options_list]
            total = len(all_regions)
            print(f"🔎 Total regions found: {total}")

            for idx, region_name in enumerate(all_regions):
                progress = f"[{idx+1}/{total}] ({(idx+1)*100//total}%)"
                if region_name in scraped_regions:
                    print(f"{progress} ⏭️ Skipping already scraped: {region_name}")
                    continue

                success = False
                attempts = 0
                while not success and attempts < 3:
                    attempts += 1
                    try:
                        if driver is None:
                            driver = start_driver()
                            driver.set_page_load_timeout(180)
                            wait = WebDriverWait(driver, 30)

                        driver.get("https://www.registre-entreprises.tn/rne-public/#/recherche-pm")
                        time.sleep(10)

                        bureau_select = wait.until(EC.element_to_be_clickable((By.ID, "mat-select-5")))
                        bureau_select.click()
                        time.sleep(2)

                        options_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'mat-option')))
                        for opt in options_list:
                            if opt.text.strip() == region_name:
                                opt.click()
                                break

                        time.sleep(2)

                        search_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button/span[contains(text(), "Rechercher")]/..')))
                        search_button.click()
                        time.sleep(10)

                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        rows = soup.select('table.rne-table tbody tr')

                        if not rows:
                            print(f"{progress} ❌ No companies found in: {region_name}")
                            success = True  # Mark region as done even if empty
                            break

                        count = 0
                        for row in rows:
                            columns = row.find_all('td')
                            if len(columns) >= 4:
                                writer.writerow({
                                    'region': region_name,
                                    'company_name_fr': columns[0].text.strip(),
                                    'commercial_name': columns[1].text.strip(),
                                    'name_arabic': columns[2].text.strip(),
                                    'full_name_arabic': columns[3].text.strip()
                                })
                                count += 1

                        file.flush()
                        print(f"{progress} ✅ {count} companies saved from {region_name}")
                        success = True
                        time.sleep(5)

                    except Exception as region_error:
                        print(f"{progress} ⚠️ Error scraping {region_name} (attempt {attempts}): {region_error}")
                        time.sleep(10)
                        try:
                            if driver:
                                driver.quit()
                        except:
                            pass
                        driver = None

        except (TimeoutException, WebDriverException) as e:
            print("❗ Connection or timeout error:", str(e))

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            print("🛑 Browser closed")

if __name__ == "__main__":
    while True:
        try:
            scrape_rne_by_region()
            print("🎉 Scraping completed or up-to-date.")
            break
        except Exception as e:
            print("🔄 Unhandled error:", str(e))
            print("⏳ Retrying after 60 seconds...")
            time.sleep(60)
