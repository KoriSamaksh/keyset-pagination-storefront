# 🛍️ Product Browsing Backend

A backend that lets you browse **200,000 products**, newest first, with category filtering, search, and price filtering — built to stay **fast** and **correct**, even while new products are being added or updated at the same time.

> 🎯 **The core challenge this solves:** normal `OFFSET`-based pagination breaks when rows are inserted while someone is browsing — it shows duplicates or skips products. This project uses **cursor-based (keyset) pagination** instead, which stays correct and fast no matter what.

---

## 📂 Project Files

| File | What it does |
|---|---|
| `generate_products.py` | 🏭 Creates 200,000 realistic-looking fake products and saves them into the database |
| `app.py` | ⚙️ The backend (Flask) — answers requests like *"give me the next 50 products"* |
| `index.html` | 🖥️ A simple browsing UI — filter, search, paginate, and a demo "add live products" panel |
| `requirements.txt` | 📦 Python packages this project needs |
| `.env.example` | 🔑 Shows which environment variables are required (no real secrets) |

---

## 🧭 How This Project Was Built — Step by Step

### 1️⃣ Planned the data model
Decided every product needs: `id`, `name`, `category`, `price`, `image_url`, `created_at`, `updated_at`. Picked **Supabase** (free hosted Postgres) as the database — free, fast to set up, and ships a simple Python client.

### 2️⃣ Created the Supabase project and table
1. Created a free project at [supabase.com](https://supabase.com).
2. Opened **SQL Editor** in the Supabase dashboard and ran:
   ```sql
   CREATE TABLE products (
       id SERIAL PRIMARY KEY,
       name TEXT,
       category TEXT,
       price NUMERIC,
       image_url TEXT,
       created_at TIMESTAMP,
       updated_at TIMESTAMP
   );
   ```
3. Disabled Row Level Security for this table (test project, no real user accounts):
   ```sql
   ALTER TABLE products DISABLE ROW LEVEL SECURITY;
   ```

### 3️⃣ Wrote `generate_products.py` to fill the database
- 🧠 Generates **realistic** product names — a brand (e.g. "Nova") + a real product type per category (e.g. "Wireless Mouse" for Electronics) — instead of random gibberish words.
- ⚡ Inserts in **batches of 5,000**, not one row at a time. Inserting 200,000 rows one-by-one means 200,000 separate trips to the database — far too slow. Batching cuts that to **40 trips total**.
- Run with:
  ```bash
  python generate_products.py
  ```

### 4️⃣ Wrote `app.py` — the backend
This is the heart of the project. It exposes:

| Endpoint | Method | Purpose |
|---|---|---|
| `/products` | `GET` | First page of products, newest first |
| `/products?cursor=...&cursor_id=...` | `GET` | Next page (cursor-based) |
| `/products?category=Shoes` | `GET` | Filter by category |
| `/products?q=shoe&price_min=100&price_max=2000` | `GET` | Search + price filter |
| `/admin/add?count=5` | `POST` | Adds 5 random new products (live demo) |
| `/admin/add` + JSON `{name, category, price}` | `POST` | Adds one specific product |

**🔑 The key design decision — cursor-based pagination:**

Instead of *"skip 50 rows, give me the next 50"* (which shifts and breaks when new rows are inserted mid-browse), each page request says:

> *"Give me the next 50 products older than the last one I already saw."*

The "last one seen" is remembered as **two values together** — `created_at` **and** `id`. The `id` acts as a tiebreaker, in case two products share the exact same `created_at`. This keeps pagination correct and fast (uses an index) no matter how many products are added while someone is browsing. ✅

### 5️⃣ Built the UI and linked it to the backend
- `index.html` is a single self-contained file (HTML + CSS + JS, no build tools) that calls the endpoints above via `fetch()`.
- `app.py` serves `index.html` directly at `/`, with CORS enabled — page and backend talk to each other with zero extra setup.
- 🤖 Built primarily with AI assistance, since this assessment doesn't grade UI code quality — only backend correctness and reasoning.
- Includes a **ℹ️ "How this demo works" popup** pointing to the admin panel, so anyone testing the app immediately knows where to simulate new products arriving.

### 6️⃣ Deployed 🚀
- Pushed this repo to GitHub.
- Deployed `app.py` on [Render](https://render.com) (free tier), with `SUPABASE_URL` and `SUPABASE_KEY` set as environment variables in Render's dashboard — **never** committed to GitHub (see `.env.example`).
- Start command: `gunicorn app:app`

---

## ▶️ Running This Locally

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd <repo-folder>

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create a .env file (see .env.example) with your Supabase URL + key

# 4. Create the products table in Supabase (see Step 2 above)

# 5. Fill the database
python generate_products.py

# 6. Start the backend
python app.py
```

Then open **http://127.0.0.1:5000** 🎉

---

## 🧪 Testing the Live-Update Behavior

1. Browse a few pages using **Load More / Next**.
2. Open the **admin panel** (gear ⚙️ icon, top-right) and click **Quick Add** to insert new random products.
3. Keep browsing — no duplicates, no skipped products. ✅
4. Go back to page 1 (or refresh) — the new products appear right at the top, since they're newest.

---

## 🔮 What I'd Improve With More Time

Add a composite database index on `(category, created_at, id)`. Right now, filtered queries (e.g. browsing by category) don't use an index as efficiently as the unfiltered "newest first" query does — this index would make filtered pagination just as fast at scale.

## 🤖 How AI Was Used

AI helped scaffold the Flask backend structure, explained and helped design the cursor-pagination logic, and built the entire UI (`index.html`), since UI code quality isn't graded for this task.

One AI-suggested feature — an offset-based "jump to page N" lookup — was identified and **removed** after review, since it reintroduced the exact duplicate/skip risk that cursor-based pagination was built to avoid in the first place, and it wasn't required by the task.
