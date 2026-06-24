# app.py
# This is the backend — like a librarian.
# The website asks "give me the next 50 products", and this finds them.

import os
import random
import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from supabase import create_client
from dotenv import load_dotenv

# ── Setup ──────────────────────────────────────────────────────────────────────

load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

app = Flask(__name__)
CORS(app)  # lets the website talk to this backend

PAGE_SIZE = 50  # show 50 products per page

PRODUCT_TYPES = {
    "Electronics": ["Wireless Mouse", "Bluetooth Speaker", "Smart Watch"],
    "Clothing":    ["Cotton T-Shirt", "Denim Jeans", "Hooded Sweatshirt"],
    "Grocery":     ["Basmati Rice 5kg", "Olive Oil 1L", "Organic Honey"],
    "Toys":        ["Building Blocks Set", "Remote Control Car", "Board Game"],
    "Books":       ["Mystery Novel", "Cookbook", "Biography"],
    "Shoes":       ["Running Shoes", "Leather Sandals", "Hiking Boots"],
}
BRANDS = ["Nova", "Urban", "Prime", "Zen", "Bolt", "Aria"]


# ── Route: serve the website ───────────────────────────────────────────────────

@app.route("/")
def home():
    return send_file("index.html")


# ── Route: GET /products ───────────────────────────────────────────────────────
# Returns the next 50 products.
# Optional filters: category, search (q), price_min, price_max
# Pagination: pass cursor + cursor_id from the previous response to get the next page

@app.route("/products")
def get_products():

    # What is the user asking for?
    category  = request.args.get("category")
    search    = request.args.get("q")
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")

    # These two together are our "bookmark" — where did we stop last time?
    last_time = request.args.get("cursor")
    last_id   = request.args.get("cursor_id")

    # Start building the database question
    query = supabase.table("products").select("*")

    # Add filters only if the user chose them
    if category:  query = query.eq("category", category)
    if search:    query = query.ilike("name", "%" + search + "%")
    if price_min: query = query.gte("price", float(price_min))
    if price_max: query = query.lte("price", float(price_max))

    # THE KEY IDEA — cursor pagination:
    # Instead of "skip 100 rows" (which breaks if new products arrive),
    # we say: "give me products OLDER than the last one I saw."
    # We use BOTH created_at AND id as the bookmark, because two products
    # could have the exact same created_at time — the id breaks that tie.
    if last_time and last_id:
        query = query.or_(
            "created_at.lt." + last_time + ","
            "and(created_at.eq." + last_time + ",id.lt." + last_id + ")"
        )

    # Newest first, id as tiebreaker. Only grab one page worth.
    query = query.order("created_at", desc=True).order("id", desc=True).limit(PAGE_SIZE)

    products = query.execute().data

    # Save the bookmark pointing to the last product on this page
    # so the next request knows where to continue
    next_cursor    = None
    next_cursor_id = None
    if products:
        next_cursor    = products[-1]["created_at"]
        next_cursor_id = products[-1]["id"]

    return jsonify({
        "products":       products,
        "next_cursor":    next_cursor,
        "next_cursor_id": next_cursor_id,
    })


# ── Route: POST /admin/add ─────────────────────────────────────────────────────
# Adds new products to the database.
# Used by the admin panel on the website to simulate live updates.

@app.route("/admin/add", methods=["POST"])
def admin_add_products():

    body = request.get_json(silent=True)

    # CASE 1: Someone filled in the form with a specific product
    if body and "name" in body:

        name     = body.get("name", "").strip()
        category = body.get("category", "").strip()
        try:
            price = float(body.get("price", 0))
        except:
            price = 0.0

        # Make sure all fields are filled in
        if not name or not category or price <= 0:
            return jsonify({"message": "Please provide a name, category, and valid price."}), 400

        # Don't add the same product name twice
        already_exists = supabase.table("products").select("id").eq("name", name).limit(1).execute()
        if already_exists.data:
            return jsonify({"message": "A product with that name already exists."}), 409

        now = datetime.datetime.now().isoformat()
        result = supabase.table("products").insert({
            "name":       name,
            "category":   category,
            "price":      price,
            "image_url":  "https://placehold.co/300x300?text=" + name.replace(" ", "+"),
            "created_at": now,
            "updated_at": now,
        }).execute()

        return jsonify({"message": "Product added!", "product": result.data[0]}), 201

    # CASE 2: The "Add Random Products" button was clicked
    count           = int(request.args.get("count", 5))
    forced_category = request.args.get("category")

    if forced_category not in PRODUCT_TYPES:
        forced_category = None

    new_products = []
    for _ in range(count):
        cat  = forced_category or random.choice(list(PRODUCT_TYPES.keys()))
        name = random.choice(BRANDS) + " " + random.choice(PRODUCT_TYPES[cat])
        now  = datetime.datetime.now().isoformat()
        new_products.append({
            "name":       name,
            "category":   cat,
            "price":      round(random.uniform(10, 5000), 2),
            "image_url":  "https://placehold.co/300x300?text=" + name.replace(" ", "+"),
            "created_at": now,
            "updated_at": now,
        })

    supabase.table("products").insert(new_products).execute()
    return jsonify({"message": f"Added {count} new products", "products": new_products})


# ── Start the server ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)