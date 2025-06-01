from ocr.celery_app import app
from .scriptt import scrape_company_data, REGIONS
import time

@app.task
def scrape_region(region_name):
    print(f"Starting scrape for {region_name}")
    scrape_company_data(region_name)
    print(f"Finished scrape for {region_name}")

@app.task
def continuous_scraping():
    print("Starting continuous region scraping loop...")
    while True:
        for region in REGIONS:
            scrape_region.delay(region)  # now valid, because scrape_region is a task
            print(f"Task scheduled for {region}")
            time.sleep(10)  # Wait 10s between regions
        print("Completed one full round of regions. Waiting 30 minutes...")
        time.sleep(30 * 60)  # Sleep 30 min before starting again
