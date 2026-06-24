# app.py
# This is the backend. Think of it like a librarian.
# When the website asks "give me page 3 of Electronics books",
# the librarian goes and finds exactly those products.

import os
import random
import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from supabase import create_client
from dotenv import load_dotenv

# ── Setup ──────────────────────────────────────────────────────────────────────
# Load secret keys from the .env file (like reading a locked diary)
load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

app = Flask(__name__)
CORS(app)  # lets the website talk to this backend

HOW_MANY_PER_PAGE = 50  # we show 50 products at a time


# ── The product data we use when adding fake products ─────────────────────────
PRODUCT_NAMES = {
    "Electronics": ["Wireless Mouse", "Bluetooth Speaker", "Smart Watch"],
    "Clothing":    ["Cotton T-Shirt", "Denim Jeans", "Hooded Sweatshirt"],
    "Grocery":     ["Basmati Rice 5kg", "Olive Oil 1L", "Organic Honey"],
    "Toys":        ["Building Blocks Set", "Remote Control Car", "Board Game"],
    "Books":       ["Mystery Novel", "Cookbook", "Biography"],
    "Shoes":       ["Running Shoes", "Leather Sandals", "Hiking Boots"],
}
BRANDS = ["Nova", "Urban", "Prime", "Zen", "Bolt", "Aria"]


# ── Helper: ask the database for one page of products ─────────────────────────
# This is a helper function so we don't write the same code twice.
# "last_time" and "last_id" are like a bookmark — they tell us where to continue.
def get_one_page(category, search, price_min, price_max, last_time, last_id):

    # Start building the database question
    query = supabase.table("products").select("*")

    # Add filters only if the user actually picked them
    if category:   query = query.eq("category", category)
    if search:     query = query.ilike("name", "%" + search + "%")
    if price_min:  query = query.gte("price", float(price_min))
    if price_max:  query = query.lte("price", float(price_max))

    # THE IMPORTANT PART:
    # Instead of saying "skip 100 rows" (which breaks when new products are added),
    # we say "give me products that are OLDER than the last one I saw."
    # We use both the time AND the id, in case two products were added at the exact same second.
    if last_time and last_id:
        query = query.or_(
            "created_at.lt." + last_time + ","
            "and(created_at.eq." + last_time + ",id.lt." + last_id + ")"
        )

    # Newest products first, use id to break ties
    query = query.order("created_at", desc=True).order("id", desc=True)

    # Only get 50 at a time
    query = query.limit(HOW_MANY_PER_PAGE)

    return query.execute().data  # actually run the question and return the list


# ── Route: serve the website ───────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return send_file("index.html")  # just send the HTML file


# ── Route: GET /products ───────────────────────────────────────────────────────
# The website calls this to get the next page of products.
# Example: /products?category=Books&cursor=2024-01-01&cursor_id=5
@app.route("/products", methods=["GET"])
def get_products():

    # Read what the website is asking for
    category  = request.args.get("category")
    search    = request.args.get("q")
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")
    last_time = request.args.get("cursor")       # bookmark: time of last product seen
    last_id   = request.args.get("cursor_id")    # bookmark: id of last product seen

    # Go get the products
    products = get_one_page(category, search, price_min, price_max, last_time, last_id)

    # Make a new bookmark pointing to the last product in this page,
    # so the next request knows where to continue
    next_time = None
    next_id   = None
    if products:
        last_product = products[-1]       # the very last product in the list
        next_time = last_product["created_at"]
        next_id   = last_product["id"]

    return jsonify({
        "products":       products,
        "next_cursor":    next_time,
        "next_cursor_id": next_id,
    })


# ── Route: GET /products/jump?page=56 ─────────────────────────────────────────
# This lets someone jump straight to page 56 (or any page number).
#
# HOW JUMPING WORKS (important to understand):
#   With our bookmark system, there's no such thing as "page 56" stored anywhere.
#   To get to page 56, we have to flip through pages 1, 2, 3 ... 55 first,
#   just collecting the bookmark at the end of each page (not the full products).
#   Then on page 56 we fetch the real products.
#
#   It's like a book with no page numbers — to find chapter 56,
#   you have to count 55 chapter endings first.
#
@app.route("/products/jump", methods=["GET"])
def jump_to_page():

    # Read the page number they want
    try:
        target_page = int(request.args.get("page", 1))
    except ValueError:
        return jsonify({"error": "page must be a number"}), 400

    # Basic safety checks
    if target_page < 1:
        return jsonify({"error": "page must be 1 or higher"}), 400
    if target_page > 500:
        return jsonify({"error": "page must be 500 or lower"}), 400

    category  = request.args.get("category")
    search    = request.args.get("q")
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")

    # Start with no bookmark (beginning of the list)
    last_time = None
    last_id   = None

    # Flip through pages 1 to (target_page - 1), only grabbing the bookmark each time
    for page_number in range(1, target_page):

        # Ask for just the id and time (not all columns) — faster since we don't need full data
        query = supabase.table("products").select("id, created_at")

        if category:   query = query.eq("category", category)
        if search:     query = query.ilike("name", "%" + search + "%")
        if price_min:  query = query.gte("price", float(price_min))
        if price_max:  query = query.lte("price", float(price_max))

        if last_time and last_id:
            query = query.or_(
                "created_at.lt." + last_time + ","
                "and(created_at.eq." + last_time + ",id.lt." + last_id + ")"
            )

        query = query.order("created_at", desc=True).order("id", desc=True).limit(HOW_MANY_PER_PAGE)
        rows = query.execute().data

        # If we got nothing, the page they asked for doesn't exist
        if not rows:
            return jsonify({
                "products": [],
                "next_cursor": None,
                "next_cursor_id": None,
                "page": target_page,
            })

        # Save the bookmark for the next hop
        last_time = rows[-1]["created_at"]
        last_id   = rows[-1]["id"]

    # Now fetch the actual products for the target page
    products = get_one_page(category, search, price_min, price_max, last_time, last_id)

    # Make the bookmark for the page after this one
    next_time = None
    next_id   = None
    if products:
        next_time = products[-1]["created_at"]
        next_id   = products[-1]["id"]

    return jsonify({
        "products":       products,
        "next_cursor":    next_time,
        "next_cursor_id": next_id,
        "page":           target_page,
    })


# ── Route: POST /admin/add ─────────────────────────────────────────────────────
# Adds new products to the database.
# Used by the admin panel on the website.
@app.route("/admin/add", methods=["POST"])
def admin_add_products():

    body = request.get_json(silent=True)

    # CASE 1: Someone filled in the manual form with a specific product
    if body and "name" in body:
        name     = body.get("name", "").strip()
        category = body.get("category", "").strip()
        try:    price = float(body.get("price", 0))
        except: price = 0.0

        # Check all fields are filled in properly
        if not name or not category or price <= 0:
            return jsonify({"message": "Please provide a name, category, and valid price."}), 400

        # Don't add the same product name twice
        already_exists = supabase.table("products").select("id").eq("name", name).limit(1).execute()
        if already_exists.data:
            return jsonify({"message": "A product with that name already exists."}), 409

        now = datetime.datetime.now().isoformat()
        result = supabase.table("products").insert({
            "name":      name,
            "category":  category,
            "price":     price,
            "image_url": "https://placehold.co/300x300?text=" + name.replace(" ", "+"),
            "created_at": now,
            "updated_at": now,
        }).execute()
        return jsonify({"message": "Product added!", "product": result.data[0]}), 201

    # CASE 2: The "Add Random Products" demo button was clicked
    count          = int(request.args.get("count", 5))
    forced_category = request.args.get("category")
    if forced_category not in PRODUCT_NAMES:
        forced_category = None

    new_products = []
    for _ in range(count):
        cat  = forced_category or random.choice(list(PRODUCT_NAMES.keys()))
        name = random.choice(BRANDS) + " " + random.choice(PRODUCT_NAMES[cat])
        now  = datetime.datetime.now().isoformat()
        new_products.append({
            "name":      name,
            "category":  cat,
            "price":     round(random.uniform(10, 5000), 2),
            "image_url": "https://placehold.co/300x300?text=" + name.replace(" ", "+"),
            "created_at": now,
            "updated_at": now,
        })

    supabase.table("products").insert(new_products).execute()
    return jsonify({"message": f"Added {count} new products", "products": new_products})


# ── Start the server ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)