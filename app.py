# app.py
# This is our backend. It answers questions like "give me the next 50 products."

import os
import random
import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from supabase import create_client
from dotenv import load_dotenv

# Step 1: Load our secret keys and connect to Supabase
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Step 2: Start our Flask app
app = Flask(__name__)
CORS(app)   # allows our index.html page to talk to this backend

PAGE_SIZE = 50   # how many products we show per page


# Step 3: Serve our UI page when someone visits the homepage
@app.route("/", methods=["GET"])
def home():
    return send_file("index.html")


# Step 4: The main door — GET /products
# This single door handles: first page, next page, category filter,
# price filter, and search — all in one place.
@app.route("/products", methods=["GET"])
def get_products():

    # Read all the optional filters from the URL
    category = request.args.get("category")
    search_text = request.args.get("q")
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")
    cursor_time = request.args.get("cursor")      # created_at of the last product seen
    cursor_id = request.args.get("cursor_id")      # id of the last product seen (tiebreaker)

    # Start building our database question
    query = supabase.table("products").select("*")

    # Apply filters, one at a time, only if they were given
    if category:
        query = query.eq("category", category)

    if search_text:
        query = query.ilike("name", "%" + search_text + "%")

    if price_min:
        query = query.gte("price", float(price_min))

    if price_max:
        query = query.lte("price", float(price_max))

    # This is the important part: instead of "skip N rows" (which breaks
    # when new products are added), we say "give me products OLDER than
    # the last one I already saw." We use created_at AND id together,
    # in case two products share the exact same created_at.
    if cursor_time and cursor_id:
        query = query.or_(
            "created_at.lt." + cursor_time + ","
            "and(created_at.eq." + cursor_time + ",id.lt." + cursor_id + ")"
        )

    # Always show newest first, and use id to break any ties
    query = query.order("created_at", desc=True).order("id", desc=True)

    # Only fetch 50 products at a time
    query = query.limit(PAGE_SIZE)

    # Run the question and get the answer
    result = query.execute()
    products = result.data

    # Work out the cursor to send back, so the next request knows where to continue
    next_cursor = None
    next_cursor_id = None
    if len(products) > 0:
        last_product = products[-1]
        next_cursor = last_product["created_at"]
        next_cursor_id = last_product["id"]

    return jsonify({
        "products": products,
        "next_cursor": next_cursor,
        "next_cursor_id": next_cursor_id
    })


# Step 5: The admin demo door — POST /admin/add
# This lets us add new fake products right now, OR add one specific
# product if the request includes a name/category/price.
@app.route("/admin/add", methods=["POST"])
def admin_add_products():

    # Check if someone sent a specific product to add (the manual add form)
    manual_product = request.get_json(silent=True)

    if manual_product and "name" in manual_product:
        name = manual_product.get("name", "").strip()
        category = manual_product.get("category", "").strip()

        try:
            price = float(manual_product.get("price", 0))
        except (ValueError, TypeError):
            price = 0.0

        if not name or not category or price <= 0:
            return jsonify({"message": "Please provide a name, category, and valid price."}), 400

        # Don't add the exact same product name twice
        existing = supabase.table("products").select("id").eq("name", name).limit(1).execute()
        if existing.data:
            return jsonify({"message": "A product with that name already exists."}), 409

        now = datetime.datetime.now().isoformat()
        new_product = {
            "name": name,
            "category": category,
            "price": price,
            "image_url": "https://placehold.co/300x300?text=" + name.replace(" ", "+"),
            "created_at": now,
            "updated_at": now
        }
        result = supabase.table("products").insert(new_product).execute()
        return jsonify({"message": "Product added!", "product": result.data[0]}), 201

    # Otherwise, just add a few random fake products (the demo button)
    product_names = {
        "Electronics": ["Wireless Mouse", "Bluetooth Speaker", "Smart Watch"],
        "Clothing": ["Cotton T-Shirt", "Denim Jeans", "Hooded Sweatshirt"],
        "Grocery": ["Basmati Rice 5kg", "Olive Oil 1L", "Organic Honey"],
        "Toys": ["Building Blocks Set", "Remote Control Car", "Board Game"],
        "Books": ["Mystery Novel", "Cookbook", "Biography"],
        "Shoes": ["Running Shoes", "Leather Sandals", "Hiking Boots"]
    }
    brands = ["Nova", "Urban", "Prime", "Zen", "Bolt", "Aria"]

    count = int(request.args.get("count", 5))
    forced_category = request.args.get("category")
    if forced_category not in product_names:
        forced_category = None

    new_products = []
    for i in range(count):
        category = forced_category if forced_category else random.choice(list(product_names.keys()))
        product_type = random.choice(product_names[category])
        brand = random.choice(brands)
        name = brand + " " + product_type
        price = round(random.uniform(10, 5000), 2)
        now = datetime.datetime.now().isoformat()

        new_products.append({
            "name": name,
            "category": category,
            "price": price,
            "image_url": "https://placehold.co/300x300?text=" + name.replace(" ", "+"),
            "created_at": now,
            "updated_at": now
        })

    supabase.table("products").insert(new_products).execute()
    return jsonify({"message": "Added " + str(count) + " new products", "products": new_products})


# Step 6: Start the server
if __name__ == "__main__":
    app.run(debug=True, port=5000)
