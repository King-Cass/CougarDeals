import re
import time
import traceback
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin
cred = credentials.Certificate('/Users/michaelcassidy/Downloads/cougar-phone-deals-firebase-adminsdk-56e88-2edf050505.json')  
firebase_admin.initialize_app(cred)

# Firestore database client
db = firestore.client()

# Setup Selenium WebDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

def scrape_google_store(driver):
    try:
        # Explicitly navigate to the Google Store URL
        driver.get("https://store.google.com/product/pixel_8?hl=en-US")

        # Wait for all span elements that could contain pricing information
        price_elements = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span"))
        )
        
        # Iterate through the elements to find the one that contains the text 'From $'
        for element in price_elements:
            if 'From $' in element.text:
                # Split the text and take the first price part
                price = element.text.split()[1]
                return float(price.replace('$', '').replace(',', ''))
        return None
    except Exception as e:
        print(f"An error occurred while scraping Google Store: {e}")
        return None



def find_lowest_price(driver, url_list):
    prices = {}
    for retailer, url in url_list.items():
        if retailer == 'Google Store':
            prices[retailer] = scrape_google_store(driver)
      
    
    # Find the lowest price and its source
    lowest_price = min(filter(None, prices.values()))  # Filter out None values
    source = [k for k, v in prices.items() if v == lowest_price][0]
    return lowest_price, source


def main():
    try:
        # Dictionary of retailers and their URLs
        url_list = {
            'Google Store': 'https://store.google.com/product/pixel_8?hl=en-US',
        }

        lowest_price, source = find_lowest_price(driver, url_list)
        print(f'Lowest Price: {lowest_price} found at {source}')

        # Prepare data for upload
        data = {
            'model': 'Google Pixel 8',
            'price': lowest_price,
            'source': source,
            'timestamp': firestore.SERVER_TIMESTAMP
        }

        # Generate a document ID based on the model and timestamp
        document_id = f"{data['model']}_{int(time.time())}"

        # Add a new document to the smartphones collection with the specified document ID
        db.collection('smartphones').document(document_id).set(data)
        print(f"Data uploaded to Firestore with document ID: {document_id}. Price: {lowest_price}")

    except Exception as e:
        # Print the full exception traceback to get more details on the error
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f"An error occurred in {fname} at line {exc_tb.tb_lineno}: {e}")
        traceback.print_exc()

    finally:
        # Close the browser
        driver.quit()

if __name__ == '__main__':
    main()

