# app.py
# This is the backend. Think of it like a librarian.
# When the website asks "give me the next 50 products in Electronics",
# the librarian goes and finds exactly those products — fast, and without
# ever handing out the same product twice, even if new ones are being
# added to the shelf right now.

import os
import random
import datetime

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from supabase import create_client
from dotenv import load_dotenv

# ── Setup ──────────────────────────────────────────────────────────────
# Load secret keys from the .env file (like reading a locked diary)
load_dotenv()

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

app = Flask(__name__)
CORS(app)  # lets the website talk to this backend

HOW_MANY_PER_PAGE = 50  # we show 50 products at a time

# ── Fake product data, used only when adding demo products ─────────────
PRODUCT_NAMES = {
    "Electronics": ["Wireless Mouse", "Bluetooth Speaker", "Smart Watch"],
    "Clothing": ["Cotton T-Shirt", "Denim Jeans", "Hooded Sweatshirt"],
    "Grocery": ["Basmati Rice 5kg", "Olive Oil 1L", "Organic Honey"],
    "Toys": ["Building Blocks Set", "Remote Control Car", "Board Game"],
    "Books": ["Mystery Novel", "Cookbook", "Biography"],
    "Shoes": ["Running Shoes", "Leather Sandals", "Hiking Boots"],
}
BRANDS = ["Nova", "Urban", "Prime", "Zen", "Bolt", "Aria"]


# ── Helper: check the "bookmark" the website sent us is safe to use ─────
# The website remembers its place with a bookmark: the created_at time
# and id of the last product it saw. Before we trust that bookmark and
# put it into a database query, we make sure it's actually a real date
# and a real whole number. Never trust raw user input directly.
def read_the_bookmark(raw_time, raw_id):
    if not raw_time or not raw_id:
        return None, None  # no bookmark = start from the very first page
    try:
        datetime.datetime.fromisoformat(raw_time)  # must be a real timestamp
        safe_id = str(int(raw_id))                  # must be a real whole number
        return raw_time, safe_id
    except (ValueError, TypeError):
        return "INVALID", None  # tells the caller "reject this request"


# ── Helper: ask the database for one page of products ───────────────────
# "last_time" and "last_id" together are the bookmark.
def get_one_page(category, search, price_min, price_max, last_time, last_id):
    query = supabase.table("products").select("*")

    # Add filters only if the user actually picked them
    if category:
        query = query.eq("category", category)
    if search:
        query = query.ilike("name", "%" + search + "%")
    if price_min:
        query = query.gte("price", float(price_min))
    if price_max:
        query = query.lte("price", float(price_max))

    # THE IMPORTANT PART — this is the whole point of the assignment:
    #
    # Instead of saying "skip 100 rows, give me the next 50" (which breaks
    # the moment someone inserts a new row — you either see a repeat or
    # miss one), we say:
    #
    #   "Give me products that come AFTER the last one I already saw,
    #    in newest-first order."
    #
    # We compare BOTH created_at AND id together, because two products
    # could in theory share the exact same created_at — id never repeats,
    # so it breaks the tie and guarantees a strict, total order.
    #
    # New products being inserted right now always land ABOVE this
    # bookmark (they're newer), so they never interfere with a page
    # the user already fetched. No duplicates, nothing skipped.
    if last_time and last_id:
        query = query.or_(
            "created_at.lt." + last_time + ","
            "and(created_at.eq." + last_time + ",id.lt." + last_id + ")"
        )

    # Newest first, id as the tiebreaker — this matches the index
    # created in setup.sql, so the database doesn't have to sort
    # all 200,000 rows on every request.
    query = query.order("created_at", desc=True).order("id", desc=True)
    query = query.limit(HOW_MANY_PER_PAGE)

    return query.execute().data


# ── Route: serve the website ─────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return send_file("index.html")


# ── Route: GET /products ─────────────────────────────────────────────────
# The website calls this to get the next page of products.
# Example: /products?category=Books&cursor=2024-01-01T00:00:00&cursor_id=5
@app.route("/products", methods=["GET"])
def get_products():
    category = request.args.get("category")
    search = request.args.get("q")
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")

    raw_time = request.args.get("cursor")      # bookmark: time of last product seen
    raw_id = request.args.get("cursor_id")      # bookmark: id of last product seen

    last_time, last_id = read_the_bookmark(raw_time, raw_id)
    if last_time == "INVALID":
        return jsonify({"error": "cursor and cursor_id must be a valid timestamp and integer"}), 400

    products = get_one_page(category, search, price_min, price_max, last_time, last_id)

    # Make a new bookmark pointing at the last product on THIS page,
    # so the next request knows exactly where to continue.
    next_time, next_id = None, None
    if products:
        last_product = products[-1]
        next_time = last_product["created_at"]
        next_id = last_product["id"]

    return jsonify({
        "products": products,
        "next_cursor": next_time,
        "next_cursor_id": next_id,
    })


# ── Route: POST /admin/add ───────────────────────────────────────────────
# Adds new products to the database. Used by the admin panel on the
# website to simulate new products arriving while someone is browsing —
# this is how you prove pagination stays correct while data changes.
@app.route("/admin/add", methods=["POST"])
def admin_add_products():
    body = request.get_json(silent=True)

    # CASE 1: someone filled in the manual form with a specific product
    if body and "name" in body:
        name = body.get("name", "").strip()
        category = body.get("category", "").strip()
        try:
            price = float(body.get("price", 0))
        except (TypeError, ValueError):
            price = 0.0

        if not name or not category or price <= 0:
            return jsonify({"message": "Please provide a name, category, and valid price."}), 400

        already_exists = supabase.table("products").select("id").eq("name", name).limit(1).execute()
        if already_exists.data:
            return jsonify({"message": "A product with that name already exists."}), 409

        now = datetime.datetime.now().isoformat()
        result = supabase.table("products").insert({
            "name": name,
            "category": category,
            "price": price,
            "image_url": "https://placehold.co/300x300?text=" + name.replace(" ", "+"),
            "created_at": now,
            "updated_at": now,
        }).execute()

        return jsonify({"message": "Product added!", "product": result.data[0]}), 201

    # CASE 2: the "Add Random Products" demo button was clicked
    count = int(request.args.get("count", 5))
    forced_category = request.args.get("category")
    if forced_category not in PRODUCT_NAMES:
        forced_category = None

    new_products = []
    for _ in range(count):
        cat = forced_category or random.choice(list(PRODUCT_NAMES.keys()))
        name = random.choice(BRANDS) + " " + random.choice(PRODUCT_NAMES[cat])
        now = datetime.datetime.now().isoformat()
        new_products.append({
            "name": name,
            "category": cat,
            "price": round(random.uniform(10, 5000), 2),
            "image_url": "https://placehold.co/300x300?text=" + name.replace(" ", "+"),
            "created_at": now,
            "updated_at": now,
        })

    supabase.table("products").insert(new_products).execute()
    return jsonify({"message": f"Added {count} new products", "products": new_products})


# ── Start the server ─────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)