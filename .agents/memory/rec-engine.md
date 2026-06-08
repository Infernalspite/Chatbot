---
name: Recommendation engine optimisation
description: Embedding-based product similarity uses batch DB load and batch Voyage AI calls; keyword fallback requires no API.
---

## Rule
Use `batch_load_embeddings(ids)` (single query) then `get_embeddings_batch(texts)` (single Voyage API call) for missing embeddings. Never loop `load_embedding()` per product.

**Why:** The original code opened one DB connection per candidate product (N+1 problem). With 56 products, that was 56 sequential round-trips. Batching reduces this to 1 DB query + at most 1 Voyage API call.

## How to apply
- `batch_load_embeddings(ids)` → `dict[product_id → vector]` (one query)
- `upsert_embeddings_batch(pairs)` → one transaction for all missing embeddings
- `EMBEDDINGS_ENABLED = bool(VOYAGE_API_KEY)` — set `VOYAGE_API_KEY` secret to activate; keyword fallback works without it.
- Keyword fallback weights: +3.0 same category, +2.0 same sub_category, +1.0 per shared tag, +0.2 per shared name token.
