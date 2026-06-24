# generate_products.py
# This script fills our database with 200,000 fake (but realistic-looking) products.

import os
import random
import datetime
from supabase import create_client
from dotenv import load_dotenv

# Step 1: Load our secret keys from the .env file
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Step 2: Connect to our Supabase database
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Step 3: Set up our fake product data
# Each category has a list of real-sounding product types
product_names = {
    "Electronics": ["Wireless Mouse", "Bluetooth Speaker", "Smart Watch", "Laptop Stand", "USB-C Charger"],
    "Clothing": ["Cotton T-Shirt", "Denim Jeans", "Hooded Sweatshirt", "Wool Sweater", "Leather Jacket"],
    "Grocery": ["Basmati Rice 5kg", "Olive Oil 1L", "Organic Honey", "Green Tea Bags", "Peanut Butter"],
    "Toys": ["Building Blocks Set", "Remote Control Car", "Board Game", "Puzzle 1000 Pieces", "Action Figure"],
    "Books": ["Mystery Novel", "Cookbook", "Biography", "Self Help Guide", "Poetry Collection"],
    "Shoes": ["Running Shoes", "Leather Sandals", "Hiking Boots", "Canvas Sneakers", "Ankle Boots"]
}

# A list of category names, taken from the dictionary above
all_categories = list(product_names.keys())

# Some made-up brand names to make products look more varied
brands = ["Nova", "Urban", "Prime", "Zen", "Bolt", "Aria"]


# Step 4: This function creates ONE fake product (as a dictionary)
def make_one_product():
    category = random.choice(all_categories)
    product_type = random.choice(product_names[category])
    brand = random.choice(brands)
    name = brand + " " + product_type

    price = round(random.uniform(10, 5000), 2)

    # A placeholder image that just shows the product name as text
    image_text = name.replace(" ", "+")
    image_url = "https://placehold.co/300x300?text=" + image_text

    # A random date sometime in the last 2 years
    days_ago = random.randint(0, 730)
    created_at = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).isoformat()

    product = {
        "name": name,
        "category": category,
        "price": price,
        "image_url": image_url,
        "created_at": created_at,
        "updated_at": created_at
    }
    return product


# Step 5: Create 200,000 products, but save them in batches of 5,000
# (saving 5,000 at once is much faster than saving them one by one)

total_products = 200000
batch_size = 5000
current_batch = []

for i in range(total_products):
    new_product = make_one_product()
    current_batch.append(new_product)

    # Once we have 5,000 products ready, save them all at once
    if len(current_batch) == batch_size:
        supabase.table("products").insert(current_batch).execute()
        print("Inserted", i + 1, "products so far...")
        current_batch = []   # empty the batch so we can fill it again

# Save any leftover products (less than 5,000) at the very end
if len(current_batch) > 0:
    supabase.table("products").insert(current_batch).execute()

print("All done! 200,000 products created.")
