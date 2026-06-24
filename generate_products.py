# generate_products.py
# Run this ONE TIME to fill the database with 200,000 fake products.
# How to run: python generate_products.py

import os
import random
import datetime
from supabase import create_client
from dotenv import load_dotenv

# Read the secret keys from the .env file (so we can talk to the database)
load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# ── What kinds of products exist? ──────────────────────────────────────────────

CATEGORIES = ["Electronics", "Clothing", "Grocery", "Toys", "Books", "Shoes"]

PRODUCT_TYPES = {
    "Electronics": ["Wireless Mouse", "Bluetooth Speaker", "Smart Watch"],
    "Clothing":    ["Cotton T-Shirt", "Denim Jeans", "Hooded Sweatshirt"],
    "Grocery":     ["Basmati Rice 5kg", "Olive Oil 1L", "Organic Honey"],
    "Toys":        ["Building Blocks Set", "Remote Control Car", "Board Game"],
    "Books":       ["Mystery Novel", "Cookbook", "Biography"],
    "Shoes":       ["Running Shoes", "Leather Sandals", "Hiking Boots"],
}

BRANDS = ["Nova", "Urban", "Prime", "Zen", "Bolt", "Aria"]

# ── Make 200,000 products and save them ───────────────────────────────────────
# We don't send them one-by-one (too slow).
# Instead we collect 5,000 at a time on a "tray", then send the whole tray.

TOTAL      = 200_000   # how many products to make
BATCH_SIZE = 5_000     # how many to send at once

tray = []  # products waiting to be sent

for i in range(TOTAL):

    # Pick random values
    category = random.choice(CATEGORIES)
    name     = random.choice(BRANDS) + " " + random.choice(PRODUCT_TYPES[category])
    price    = round(random.uniform(10, 5000), 2)

    # Give it a random date in the last 2 years
    # (so that "newest first" sorting actually shows different products)
    days_ago   = random.randint(0, 730)
    created_at = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).isoformat()

    tray.append({
        "name":       name,
        "category":   category,
        "price":      price,
        "image_url":  "https://placehold.co/300x300?text=" + name.replace(" ", "+"),
        "created_at": created_at,
        "updated_at": created_at,
    })

    # When the tray is full, send it and empty it
    if len(tray) == BATCH_SIZE:
        supabase.table("products").insert(tray).execute()
        print(f"Saved {i + 1:,} / {TOTAL:,} products...")
        tray = []

# Send whatever is left at the end
if tray:
    supabase.table("products").insert(tray).execute()

print("Done! 200,000 products are now in the database.")