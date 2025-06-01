import time
import csv
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException, TimeoutException
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(filename='scraping_progress.log', level=logging.INFO)

# Your list of regions/bureaux
REGIONS = [
    "API Sfax", "API Sousse", "API Tunis", "Ariana", "Auto entrepreneur", "Baja", "Ben Arous", "Bizerte",
    "Gabes", "Gafsa", "Gasserine", "Grombalia", "Guchet Central", "Instance Tunisienne d'Investissement",
    "Jandouba", "Juridiction web", "Kairouan", "Kebelli", "Le Kef", "Mahdia", "Mannouba", "Mednine",
    "Monastir", "Nabeul", "RNE", "Seliana", "Sfax", "Sfax 2", "Sidi Bou Zid", "Sousse", "Sousse 2",
    "Tataouin", "Tozeur", "Tunis 1", "Tunis 2", "Zaghouan"
]



def scrape_company_data(company_name):
    """Scrapes company information from the official registry and saves it to a CSV."""
    
    if not company_name:
        logging.error('Company name is required.')
        return
    driver = None

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run headless for background execution
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    try:
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.registre-entreprises.tn/rne-public/#/recherche-pm")

        # Wait for the page to load properly
        time.sleep(3)

        # Open the <mat-select> dropdown for bureauRegional
        mat_select = driver.find_element(By.CSS_SELECTOR, 'mat-select[formcontrolname="bureauRegional"]')
        mat_select.click()

        # Wait for options to load
        time.sleep(1)

        # Find and select the bureauRegional based on company name (or part of it)
        try:
            company_option = driver.find_element(By.XPATH, f"//mat-option//span[contains(text(), '{company_name}')]")
            company_option.click()
            logging.info(f'Selected bureau: {company_name}')
        except Exception as e:
            logging.error(f'Error selecting bureau for {company_name}: {e}')
            return

        # Wait for the dropdown to close and the results to load
        time.sleep(3)

        # Submit the search
        search_button = driver.find_element(By.CSS_SELECTOR, 'button[type="button"]')
        search_button.click()
        logging.info('Search submitted.')

        # Wait for results to load
        time.sleep(5)

        last_height = driver.execute_script("return document.body.scrollHeight")
        logging.info('Starting scroll and data collection.')

        all_data = []
        while True:
            # Scroll down by a certain amount
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait for the page to load more companies
            time.sleep(7)

            # Get the new height after scrolling
            new_height = driver.execute_script("return document.body.scrollHeight")

            # If the height has not changed, we've reached the bottom of the page
            if new_height == last_height:
                break

            last_height = new_height

            # Scrape the results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            rows = soup.select('table.rne-table tbody tr')

            if not rows:
                logging.warning('No results found during scrolling.')

            for row in rows:
                columns = row.find_all('td')
                if len(columns) >= 4:
                    company_name_fr = columns[0].text.strip() if columns[0] else 'Nom non disponible'
                    company_name_commercial = columns[1].text.strip() if columns[1] else 'Nom commercial non disponible'
                    company_name_arabic = columns[2].text.strip() if columns[2] else 'Nom arabe non disponible'
                    company_name_arabic_full = columns[3].text.strip() if columns[3] else 'Nom arabe complet non disponible'
                    

                    all_data.append({
                        'company_name_fr': company_name_fr,
                        'company_name_commercial': company_name_commercial,
                        'company_name_arabic': company_name_arabic,
                        'company_name_arabic_full': company_name_arabic_full,
                        'region':company_name
                        
                    })
            logging.info(f'Collected {len(all_data)} records so far.')

        # Write to CSV after collecting all the data
        csv_filename = 'companies_data.csv'
        with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['company_name_fr', 'company_name_commercial', 'company_name_arabic', 'company_name_arabic_full','region'])
            writer.writeheader()
            writer.writerows(all_data)
        logging.info(f'CSV file created: {csv_filename}')

    except (WebDriverException, TimeoutException) as e:
        logging.error(f'Selenium error: {str(e)}')
    except Exception as e:
        logging.error(f'An error occurred: {str(e)}')
    finally:
        driver.quit()
        logging.info('Driver quit and process completed.')

def run_scraper():
    print("Starting full scraper loop...")
    while True:
        for region in REGIONS:
            print(f"Running scrape for region: {region}")
            scrape_company_data(region)
            print(f"Waiting 10 seconds before next region...")
            time.sleep(10)  # Short delay between regions
        print("Completed scraping all regions. Sleeping for 30 minutes...")
        time.sleep(30 * 60)  # Sleep for 30 minutes

if __name__ == "__main__":
    run_scraper()
