# 🧠 Real-Time Product Recommendation Engine
### For: intern-shopsite / mine--store (FastAPI + Streamlit + MySQL)

---

## Architecture Overview

```
User clicks "Add to Cart"
        │
        ▼
[Streamlit frontend]
  1. Appends product to st.session_state.cart  (existing logic)
  2. Fires GET /recommendations/{product_id}?exclude_ids=<cart_ids>
        │
        ▼
[FastAPI  /recommendations/{product_id}]
  3. Fetches source product from MySQL
  4. Fetches all other in-stock products
  5. Picks strategy:
       ┌─ voyageai installed & embedding exists? ──► Cosine similarity  ─┐
       └─ fallback ─────────────────────────────► Keyword / category   ──┤
  6. Returns top-N ranked products as JSON                               │
        │                                                                 │
        ▼                                                                 │
[Streamlit frontend]                                                      │
  7. Saves recs in st.session_state.recommendations                      │
  8. Renders "You Might Also Like" card grid below the product list ◄────┘
```

**No polling. No WebSockets.** Streamlit re-renders synchronously on button
click, so the recommendations appear immediately as part of the same
interaction — zero extra round-trips for the user.

---

## Files Delivered

| File | Purpose | Destination |
|------|---------|-------------|
| `migrate_recommendations.py` | DB migration (run once) | `backend/` |
| `embeddings.py` | Voyage embedding helpers | `backend/` |
| `recommendations.py` | FastAPI router | `backend/` |
| `main_py_changes.py` | Exact lines to add to main.py | reference |
| `app_py_changes.py` | Exact lines to add to app.py | reference |
| `requirements.txt` | Updated deps | project root |

---

## Step-by-Step Integration

### Prerequisites
```
VOYAGE_API_KEY=va-xxxx   # Get from https://dash.voyageai.com
```
Add this to your `.env` file (already loaded by `python-dotenv` in main.py).

---

### Step 1 — Install new dependency
```bash
pip install voyageai
# or update from the new requirements.txt:
pip install -r requirements.txt
```

---

### Step 2 — Copy new files into backend/
```bash
cp migrate_recommendations.py  backend/
cp embeddings.py               backend/
cp recommendations.py          backend/
```

---

### Step 3 — Run the DB migration
```bash
cd backend
python migrate_recommendations.py
# Output: ✅  Migration complete — columns & product_embeddings table ready.
```

This adds four optional columns to `products`:
- `category` VARCHAR(120)
- `sub_category` VARCHAR(120)
- `description` TEXT
- `tags` JSON

And creates the `product_embeddings` table (stores Voyage 1024-dim vectors).

> **Note:** The columns are nullable. Your existing products still work
> immediately via the keyword/category fallback. Fill them in gradually.

---

### Step 4 — Pre-build embeddings (optional, recommended)
```bash
cd backend
python embeddings.py
# Output: ✅  Building embeddings for 50 products …
#            ✔  product_id=1  Noise-Canceling Headphones
#            …
```

For the best similarity results, populate `category`, `description`, and
`tags` on your products first, then run this script. It only processes
products that don't yet have embeddings, so it's safe to re-run.

New products added later get their embedding generated on-the-fly on first
request to `/recommendations/{id}` (with ~200ms overhead once, then cached).

---

### Step 5 — Register the router in main.py

Open `backend/main.py`. Find:
```python
app.include_router(rbac.router)
app.include_router(mange.router)
app.include_router(chatbot.router)
```

Change to:
```python
import recommendations                       # ← ADD

app.include_router(rbac.router)
app.include_router(mange.router)
app.include_router(chatbot.router)
app.include_router(recommendations.router)   # ← ADD
```

---

### Step 6 — Patch the Streamlit frontend

Open `frontend/app.py`.

**6a.** Find the session-state init block (around line 14) and add:
```python
if "recommendations" not in st.session_state:
    st.session_state.recommendations = []
```

**6b.** Find the `"Add to Cart"` button handler (around line 440).
Replace the existing handler with the version in `app_py_changes.py`
(the `REPLACE ... WITH` section). The new handler does everything the
old one did, plus fires the recommendation API call.

**6c.** After the products grid `except` block, paste the
`# ── Recommendations panel (NEW)` section from `app_py_changes.py`.

---

### Step 7 — Restart and test
```bash
# Terminal 1 — backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && streamlit run app.py
```

1. Open the store, browse to any product.
2. Click **Add to Cart**.
3. A "✨ You Might Also Like" section appears below the product grid
   with 4 ranked recommendations.
4. Click **Add to Cart** on a recommendation card — recommendations
   refresh automatically, excluding everything already in your cart.

---

## API Reference

```
GET /recommendations/{product_id}

Query params:
  limit        int (1-12, default 4)  — number of results
  exclude_ids  str                    — comma-separated IDs to skip

Response:
{
  "strategy": "embeddings" | "keywords" | "keywords_fallback" | "none",
  "source_id": 5,
  "recommendations": [
    {
      "id": 12,
      "name": "Portable Bluetooth Speaker",
      "price": 39.99,
      "stock": 85,
      "image_url": "https://…",
      "category": "Electronics",
      "sub_category": "Audio"
    },
    …
  ]
}
```

The `strategy` field tells you which path was used — useful for debugging
or displaying a confidence indicator in your UI.

---

## Enriching Products for Better Recommendations

The more metadata you add, the better the AI similarity becomes.

```sql
-- Example: update a product with category + tags
UPDATE products SET
  category     = 'Electronics',
  sub_category = 'Audio',
  description  = 'Over-ear noise-canceling headphones with 30hr battery life.',
  tags         = JSON_ARRAY('wireless', 'noise-canceling', 'bluetooth', 'headphones')
WHERE id = 1;
```

After updating metadata, regenerate embeddings:
```bash
# Delete old embedding so it gets rebuilt
DELETE FROM product_embeddings WHERE product_id = 1;

# Or just re-run the full builder (skips already-embedded products)
python embeddings.py
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: voyageai` | `pip install voyageai` |
| Recommendations empty | Check `stock > 0` on products; check MySQL connection |
| `strategy: keywords_fallback` | VOYAGE_API_KEY missing in `.env`, or voyage API error |
| Column `category` doesn't exist | Run `migrate_recommendations.py` again |
| Slow first recommendation | First call embeds on-the-fly; pre-run `python embeddings.py` |
