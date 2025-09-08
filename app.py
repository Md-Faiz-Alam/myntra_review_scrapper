import pandas as pd
import streamlit as st
from src.cloud_io import MongoIO
from src.constants import SESSION_PRODUCT_KEY
from src.scrapper.scrape import ScrapeReviews
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(
    "myntra-review-scrapper"

)

st.title("Myntra Review Scrapper")
st.session_state["data"] = False


def form_input():
    product = st.text_input("Search Products")
    st.session_state[SESSION_PRODUCT_KEY] = product
    no_of_products = st.number_input("No of products to search",
                                            step=1,
                                            min_value=1)

    if st.button("Scrape Reviews"):
        scrapper = ScrapeReviews(
            product_name=product,
            no_of_products=int(no_of_products)
        )

        scrapped_data = scrapper.get_review_data()

        if scrapped_data is not None and not scrapped_data.empty:
            st.session_state["data"] = True
            st.write(f"🔎 Scraped {scrapped_data.shape[0]} rows")

            mongoio = MongoIO()
            mongoio.store_reviews(product_name=product, reviews=scrapped_data)
            st.success(f"✅ Stored {len(scrapped_data)} rows into MongoDB")

            # verify by reading back
            df_from_mongo = mongoio.mongo_ins.find(product.replace(" ", "_"))
            st.write("📂 Rows in Mongo after insert:", df_from_mongo.shape)

        else:
            st.warning("⚠️ No reviews scraped, nothing to store.")

        st.dataframe(scrapped_data)


if __name__ == "__main__":
    data = form_input()
