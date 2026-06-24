# generate_products.py
# Run this ONE TIME to fill the database with 200,000 fake products.
# After that, you never need to run it again.
#
# How to run: python generate_products.py

import os
import random
import datetime
from supabase import create_client
from dotenv import load_dotenv

# Load our secret database keys from the .env file
load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))


# ── Step 1: Decide what fake products look like ────────────────────────────────
# Each category has a list of product types.
# We'll mix brands + product types together to make names like "Nova Wireless Mouse".

PRODUCTS = {
    "Electronics": ["Wireless Mouse", "Bluetooth Speaker", "Smart Watch", "Laptop Stand", "USB-C Charger"],
    "Clothing":    ["Cotton T-Shirt", "Denim Jeans", "Hooded Sweatshirt", "Wool Sweater", "Leather Jacket"],
    "Grocery":     ["Basmati Rice 5kg", "Olive Oil 1L", "Organic Honey", "Green Tea Bags", "Peanut Butter"],
    "Toys":        ["Building Blocks Set", "Remote Control Car", "Board Game", "Puzzle 1000 Pieces", "Action Figure"],
    "Books":       ["Mystery Novel", "Cookbook", "Biography", "Self Help Guide", "Poetry Collection"],
    "Shoes":       ["Running Shoes", "Leather Sandals", "Hiking Boots", "Canvas Sneakers", "Ankle Boots"],
}
CATEGORIES = list(PRODUCTS.keys())
BRANDS = ["Nova", "Urban", "Prime", "Zen", "Bolt", "Aria"]


# ── Step 2: Make all 200,000 products and insert in batches ───────────────────
# Why batches? Sending 200,000 products one-by-one would take hours.
# Sending 5,000 at a time takes a few minutes instead.

TOTAL      = 200_000   # how many products we want
BATCH_SIZE = 5_000     # how many we send to the database at once

batch = []  # this is our "tray" — we fill it up, send it, then refill

for i in range(TOTAL):

    # Pick random values for this product
    category   = random.choice(CATEGORIES)
    name       = random.choice(BRANDS) + " " + random.choice(PRODUCTS[category])
    price      = round(random.uniform(10, 5000), 2)

    # Give it a random date sometime in the last 2 years
    # (so the "newest first" sorting actually shows different products)
    days_ago   = random.randint(0, 730)
    created_at = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).isoformat()

    # Add this product to our tray
    batch.append({
        "name":       name,
        "category":   category,
        "price":      price,
        "image_url":  "https://placehold.co/300x300?text=" + name.replace(" ", "+"),
        "created_at": created_at,
        "updated_at": created_at,
    })

    # When the tray is full, send it to the database and empty it
    if len(batch) == BATCH_SIZE:
        supabase.table("products").insert(batch).execute()
        print(f"Inserted {i + 1:,} out of {TOTAL:,} products...")
        batch = []  # empty the tray

# Send whatever is left over in the tray at the very end
if batch:
    supabase.table("products").insert(batch).execute()

print("All done! 200,000 products are now in the database.")