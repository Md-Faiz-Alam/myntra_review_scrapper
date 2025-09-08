from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup as bs
import pandas as pd
import time
from urllib.parse import quote
import sys
from src.exception import CustomException
import chromedriver_binary  


class ScrapeReviews:
    def __init__(self, product_name: str, no_of_products: int):
        try:
            options = Options()
            options.add_argument("--headless")  # run Chrome in headless mode
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")

            self.driver = webdriver.Chrome(options=options)

            self.product_name = product_name
            self.no_of_products = no_of_products
        except Exception as e:
            raise CustomException(e, sys)

    def scrape_product_urls(self, product_name):
        try:
            search_string = product_name.replace(" ", "-")
            encoded_query = quote(search_string)
            self.driver.get(f"https://www.myntra.com/{search_string}?rawQuery={encoded_query}")

            page_html = bs(self.driver.page_source, "html.parser")
            product_list = page_html.findAll("ul", {"class": "results-base"})

            product_urls = []
            for ul in product_list:
                hrefs = ul.find_all("a", href=True)
                for h in hrefs:
                    product_urls.append(h["href"])

            return product_urls
        except Exception as e:
            raise CustomException(e, sys)

    def extract_reviews(self, product_link):
        try:
            url = "https://www.myntra.com/" + product_link
            self.driver.get(url)
            page_html = bs(self.driver.page_source, "html.parser")

            # Extract product info
            self.product_title = page_html.find("title").text
            overall_rating = page_html.find("div", {"class": "index-overallRating"})
            self.product_rating_value = overall_rating.find("div").text if overall_rating else "No Rating"
            price = page_html.find("span", {"class": "pdp-price"})
            self.product_price = price.text if price else "No Price"
            reviews_link = page_html.find("a", {"class": "detailed-reviews-allReviews"})
            if not reviews_link:
                return None
            return reviews_link
        except Exception as e:
            raise CustomException(e, sys)

    def scroll_to_load_reviews(self):
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
        except Exception as e:
            raise CustomException(e, sys)

    def extract_products(self, product_reviews):
        try:
            t2 = product_reviews["href"]
            review_url = "https://www.myntra.com" + t2
            self.driver.get(review_url)

            self.scroll_to_load_reviews()
            page_html = bs(self.driver.page_source, "html.parser")
            review_containers = page_html.findAll("div", {"class": "detailed-reviews-userReviewsContainer"})

            reviews = []
            for container in review_containers:
                try:
                    rating = container.find("span", class_="user-review-starRating").get_text(strip=True)
                except:
                    rating = "No rating Given"
                try:
                    comment = container.find("div", {"class": "user-review-reviewTextWrapper"}).text
                except:
                    comment = "No comment Given"
                try:
                    name_span = container.find("div", {"class": "user-review-left"}).find_all("span")
                    name = name_span[0].text if len(name_span) > 0 else "No Name given"
                    date = name_span[1].text if len(name_span) > 1 else "No Date given"
                except:
                    name = "No Name given"
                    date = "No Date given"

                reviews.append({
                    "Product Name": self.product_title,
                    "Over_All_Rating": self.product_rating_value,
                    "Price": self.product_price,
                    "Date": date,
                    "Rating": rating,
                    "Name": name,
                    "Comment": comment
                })

            return pd.DataFrame(reviews)
        except Exception as e:
            raise CustomException(e, sys)

    def get_review_data(self) -> pd.DataFrame:
        try:
            product_urls = self.scrape_product_urls(self.product_name)
            all_reviews = []

            review_count = 0
            while review_count < self.no_of_products:
                product_url = product_urls[review_count]
                review_link = self.extract_reviews(product_url)
                if review_link:
                    df = self.extract_products(review_link)
                    all_reviews.append(df)
                    review_count += 1
                else:
                    product_urls.pop(review_count)

            self.driver.quit()
            data = pd.concat(all_reviews, axis=0)
            data.to_csv("data.csv", index=False)
            return data
        except Exception as e:
            raise CustomException(e, sys)

