from flask import request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from src.exception import CustomException
from bs4 import BeautifulSoup as bs
import pandas as pd
import os, sys
import time
from selenium.webdriver.chrome.options import Options
from urllib.parse import quote
import shutil
import requests


class ScrapeReviews:
    def __init__(self, product_name, no_of_products):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        chromedriver_path = shutil.which("chromedriver")
        if not chromedriver_path:
            raise Exception("Chromedriver not found in system PATH.")
        service = Service(chromedriver_path)
        self.driver = webdriver.Chrome(service=service, options=options)

        self.product_name = product_name
        self.no_of_products = no_of_products

    def scrape_product_urls(self, product_name):
        try:
            search_string = product_name.replace(" ", "-")
            encoded_query = quote(search_string)
            self.driver.get(
                f"https://www.myntra.com/{search_string}?rawQuery={encoded_query}"
            )
            myntra_text = self.driver.page_source
            myntra_html = bs(myntra_text, "html.parser")

            product_containers = myntra_html.findAll("div", {"class": "product-base"})

            product_urls = []
            for container in product_containers:
                href_tag = container.find("a", href=True)
                if href_tag:
                    t = href_tag["href"]
                    product_urls.append(t)

            return product_urls

        except Exception as e:
            raise CustomException(e, sys)

    def extract_reviews(self, product_link):
        try:
            productLink = "https://www.myntra.com/" + product_link
            self.driver.get(productLink)
            prodRes = self.driver.page_source
            prodRes_html = bs(prodRes, "html.parser")

            title_h = prodRes_html.find("title")
            self.product_title = title_h.text if title_h else "Unknown Product"

            overallRating = prodRes_html.find("div", {"class": "index-overallRating"})
            self.product_rating_value = (
                overallRating.find("div").text if overallRating else "N/A"
            )

            price = prodRes_html.find("span", {"class": "pdp-price"})
            self.product_price = price.text if price else "N/A"

            # Get product ID from URL
            try:
                product_id = product_link.split("/")[-1]
                if not product_id.isdigit():
                    return None
                return product_id
            except:
                return None

        except Exception as e:
            raise CustomException(e, sys)

    def fetch_reviews_api(self, product_id, pages=5):
        """Fetch reviews from Myntra review API instead of scrolling"""
        reviews = []
        for page in range(pages):
            url = f"https://www.myntra.com/reviews/{product_id}/page?offset={page*10}&pageSize=10"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                break
            data = resp.json()
            if "reviews" not in data or not data["reviews"]:
                break
            for r in data["reviews"]:
                reviews.append(
                    {
                        "Product Name": self.product_title,
                        "Over_All_Rating": self.product_rating_value,
                        "Price": self.product_price,
                        "Date": r.get("createdAt"),
                        "Rating": r.get("rating"),
                        "Name": r.get("user", {}).get("name", "Anonymous"),
                        "Comment": r.get("reviewText"),
                    }
                )
        return pd.DataFrame(reviews)

    def get_review_data(self) -> pd.DataFrame:
        try:
            product_urls = self.scrape_product_urls(product_name=self.product_name)
            product_details = []
            review_len = 0

            max_products = min(self.no_of_products, len(product_urls))

            while review_len < max_products:
                product_url = product_urls[review_len]
                product_id = self.extract_reviews(product_url)

                if product_id:
                    product_detail = self.fetch_reviews_api(product_id, pages=5)
                    if not product_detail.empty:
                        product_details.append(product_detail)
                review_len += 1

            self.driver.quit()

            if product_details:
                data = pd.concat(product_details, axis=0)
                data.to_csv("data.csv", index=False)
                return data
            else:
                print("⚠️ No reviews scraped, nothing to store.")
                return pd.DataFrame()

        except Exception as e:
            raise CustomException(e, sys)
