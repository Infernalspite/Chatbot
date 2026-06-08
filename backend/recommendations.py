"""
Recommendations router.

GET /recommendations/{product_id}?limit=4&exclude_ids=2,7

Returns up to `limit` products ranked by:
  1. Cosine similarity of Voyage AI embeddings  (primary, requires VOYAGE_API_KEY)
  2. Keyword / category / tag heuristic         (fallback when embeddings unavailable)
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from database import DB_connection

try:
    from embeddings import (
        batch_load_embeddings,
        cosine_similarity,
        get_embedding,
        get_embeddings_batch,
        product_text,
        upsert_embeddings_batch,
        upsert_product_embedding,
        VOYAGE_API_KEY,
    )
    EMBEDDINGS_ENABLED = bool(VOYAGE_API_KEY)
except ImportError:
    EMBEDDINGS_ENABLED = False

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# ── Fetch one product with all enrichment fields ──────────────────────────────
def _fetch_product(product_id: int) -> dict:
    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, price, stock, image_url,
                       category, sub_category, description, tags
                FROM   products
                WHERE  id = %s
            """, (product_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Product not found")
            return row
    finally:
        conn.close()


# ── Fetch all candidate products (excluding specified IDs) ────────────────────
def _fetch_candidates(exclude_ids: list[int]) -> list[dict]:
    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(exclude_ids))
            cur.execute(f"""
                SELECT id, name, price, stock, image_url,
                       category, sub_category, description, tags
                FROM   products
                WHERE  id NOT IN ({placeholders})
                  AND  stock > 0
            """, tuple(exclude_ids))
            return cur.fetchall()
    finally:
        conn.close()


# ── Strategy 1: Embedding-based cosine similarity ─────────────────────────────
def _recommend_by_embeddings(
    source: dict,
    candidates: list[dict],
    limit: int,
) -> list[dict]:
    """
    Ranks candidates by cosine similarity to the source product embedding.

    Optimised: loads ALL embeddings in a single DB round-trip, then generates
    any missing ones in one batched Voyage AI call.
    """
    all_ids      = [source["id"]] + [c["id"] for c in candidates]
    stored       = batch_load_embeddings(all_ids)   # single query

    # Ensure source embedding exists
    src_emb = stored.get(source["id"])
    if src_emb is None:
        src_emb = get_embedding(product_text(source))
        upsert_product_embedding(source["id"], src_emb)

    # Identify candidates that need embeddings generated
    missing = [c for c in candidates if c["id"] not in stored]
    if missing:
        texts    = [product_text(c) for c in missing]
        new_embs = get_embeddings_batch(texts)
        pairs    = [(c["id"], emb) for c, emb in zip(missing, new_embs)]
        upsert_embeddings_batch(pairs)
        for c, emb in zip(missing, new_embs):
            stored[c["id"]] = emb

    # Score all candidates
    scored: list[tuple[float, dict]] = []
    for cand in candidates:
        cand_emb = stored.get(cand["id"])
        if cand_emb is None:
            continue
        score = cosine_similarity(src_emb, cand_emb)
        scored.append((score, cand))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [p for _, p in scored[:limit]]


# ── Strategy 2: Keyword / category heuristic (no API needed) ─────────────────
def _recommend_by_keywords(
    source: dict,
    candidates: list[dict],
    limit: int,
) -> list[dict]:
    """
    Lightweight scoring using category, sub-category, tags, and name tokens.
    Used when VOYAGE_API_KEY is not configured or the embedding API fails.

    Scoring weights:
      +3.0  same category
      +2.0  same sub-category
      +1.0  per shared tag
      +0.2  per shared name token
    """
    src_category = (source.get("category") or "").lower()
    src_sub      = (source.get("sub_category") or "").lower()

    src_tags: set[str] = set()
    raw_tags = source.get("tags")
    if raw_tags:
        if isinstance(raw_tags, str):
            raw_tags = json.loads(raw_tags)
        src_tags = {t.lower() for t in raw_tags}

    src_tokens = set((source.get("name") or "").lower().split())

    scored: list[tuple[float, dict]] = []
    for cand in candidates:
        score = 0.0

        if src_category and (cand.get("category") or "").lower() == src_category:
            score += 3.0
        if src_sub and (cand.get("sub_category") or "").lower() == src_sub:
            score += 2.0

        raw_cand_tags = cand.get("tags")
        cand_tags: set[str] = set()
        if raw_cand_tags:
            if isinstance(raw_cand_tags, str):
                raw_cand_tags = json.loads(raw_cand_tags)
            cand_tags = {t.lower() for t in raw_cand_tags}
        score += len(src_tags & cand_tags)

        cand_tokens = set((cand.get("name") or "").lower().split())
        score += 0.2 * len(src_tokens & cand_tokens)

        scored.append((score, cand))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [p for _, p in scored[:limit]]


# ── Response serialiser ────────────────────────────────────────────────────────
def _format_product(p: dict) -> dict:
    return {
        "id":           p["id"],
        "name":         p["name"],
        "price":        float(p["price"]),
        "stock":        p["stock"],
        "image_url":    p.get("image_url"),
        "category":     p.get("category"),
        "sub_category": p.get("sub_category"),
    }


# ── Main endpoint ──────────────────────────────────────────────────────────────
@router.get("/{product_id}")
def get_recommendations(
    product_id: int,
    limit: int = Query(default=4, ge=1, le=12),
    exclude_ids: Optional[str] = Query(
        default=None,
        description="Comma-separated product IDs to exclude (e.g. cart items: '3,7,12')"
    ),
):
    """
    Returns up to `limit` products similar to `product_id`.

    Query params
    ------------
    limit        Number of results (1–12, default 4).
    exclude_ids  Comma-separated IDs to skip (always excludes the source itself).

    Response
    --------
    {
        "strategy":        "embeddings" | "keywords" | "keywords_fallback" | "none",
        "source_id":       5,
        "recommendations": [ { id, name, price, stock, image_url, … } ]
    }
    """
    # Build exclusion set — always skip the source product itself
    exclude_set: set[int] = {product_id}
    if exclude_ids:
        for raw in exclude_ids.split(","):
            raw = raw.strip()
            if raw.isdigit():
                exclude_set.add(int(raw))

    source     = _fetch_product(product_id)
    candidates = _fetch_candidates(list(exclude_set))

    if not candidates:
        return {"strategy": "none", "source_id": product_id, "recommendations": []}

    strategy = "keywords"
    try:
        if EMBEDDINGS_ENABLED:
            results  = _recommend_by_embeddings(source, candidates, limit)
            strategy = "embeddings"
        else:
            results  = _recommend_by_keywords(source, candidates, limit)
    except Exception:
        results  = _recommend_by_keywords(source, candidates, limit)
        strategy = "keywords_fallback"

    return {
        "strategy":        strategy,
        "source_id":       product_id,
        "recommendations": [_format_product(r) for r in results],
    }
