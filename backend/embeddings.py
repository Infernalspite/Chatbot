"""
Embedding utilities.

• Uses Voyage AI's voyage-3 model via the voyageai SDK.
• Falls back to keyword/category matching if VOYAGE_API_KEY is not set.
• Run   python3.11 embeddings.py   once to pre-build all embeddings.
"""

import json
import math
import os
from typing import Optional

from database import DB_connection

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
EMBED_MODEL    = "voyage-3"
EMBED_DIM      = 1024


# ── Voyage client (singleton) ──────────────────────────────────────────────────
def _client():
    import voyageai
    return voyageai.Client(api_key=VOYAGE_API_KEY)


# ── Text fingerprint for a product ────────────────────────────────────────────
def product_text(product: dict) -> str:
    """
    Concatenates all searchable fields into a single string for embedding.
    Gracefully handles missing fields.
    """
    parts = [
        product.get("name", ""),
        product.get("category", "") or "",
        product.get("sub_category", "") or "",
        product.get("description", "") or "",
    ]
    tags = product.get("tags")
    if tags:
        if isinstance(tags, str):
            tags = json.loads(tags)
        if isinstance(tags, list):
            parts.append(" ".join(str(t) for t in tags))
    return " | ".join(p for p in parts if p)


# ── Cosine similarity ──────────────────────────────────────────────────────────
def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x * x for x in a))
    nb  = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


# ── Generate a single embedding via Voyage AI ──────────────────────────────────
def get_embedding(text: str) -> list[float]:
    result = _client().embed([text], model=EMBED_MODEL, input_type="document")
    return result.embeddings[0]


# ── Batch-generate embeddings for multiple texts ───────────────────────────────
def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Send all texts to Voyage in one API call — much faster than one-by-one."""
    result = _client().embed(texts, model=EMBED_MODEL, input_type="document")
    return result.embeddings


# ── Upsert embedding for one product ──────────────────────────────────────────
def upsert_product_embedding(product_id: int, embedding: list[float]):
    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO product_embeddings (product_id, embedding)
                VALUES (%s, %s)
                ON CONFLICT (product_id) DO UPDATE
                    SET embedding  = EXCLUDED.embedding,
                        updated_at = CURRENT_TIMESTAMP
            """, (product_id, json.dumps(embedding)))
        conn.commit()
    finally:
        conn.close()


# ── Batch upsert embeddings for multiple products ─────────────────────────────
def upsert_embeddings_batch(id_embedding_pairs: list[tuple[int, list[float]]]):
    """Insert or update embeddings for multiple products in one transaction."""
    if not id_embedding_pairs:
        return
    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            for product_id, embedding in id_embedding_pairs:
                cur.execute("""
                    INSERT INTO product_embeddings (product_id, embedding)
                    VALUES (%s, %s)
                    ON CONFLICT (product_id) DO UPDATE
                        SET embedding  = EXCLUDED.embedding,
                            updated_at = CURRENT_TIMESTAMP
                """, (product_id, json.dumps(embedding)))
        conn.commit()
    finally:
        conn.close()


# ── Load stored embedding for a single product ────────────────────────────────
def load_embedding(product_id: int) -> Optional[list[float]]:
    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT embedding FROM product_embeddings WHERE product_id = %s",
                (product_id,)
            )
            row = cur.fetchone()
            if row:
                raw = row["embedding"]
                return json.loads(raw) if isinstance(raw, str) else raw
            return None
    finally:
        conn.close()


# ── Batch-load stored embeddings for multiple products ────────────────────────
def batch_load_embeddings(product_ids: list[int]) -> dict[int, list[float]]:
    """
    Fetch all stored embeddings for the given IDs in a SINGLE database query.
    Returns a dict mapping product_id → embedding vector.
    Missing IDs are simply absent from the result.
    """
    if not product_ids:
        return {}
    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(product_ids))
            cur.execute(
                f"SELECT product_id, embedding FROM product_embeddings "
                f"WHERE product_id IN ({placeholders})",
                tuple(product_ids)
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    result = {}
    for row in rows:
        raw = row["embedding"]
        result[row["product_id"]] = json.loads(raw) if isinstance(raw, str) else raw
    return result


# ── Pre-build ALL embeddings (run once after setup) ───────────────────────────
def build_all_embeddings():
    """
    Call this script directly:   python3.11 embeddings.py
    Embeds every product that doesn't yet have a stored embedding.
    """
    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.id, p.name, p.category, p.sub_category,
                       p.description, p.tags
                FROM   products p
                LEFT   JOIN product_embeddings pe ON pe.product_id = p.id
                WHERE  pe.product_id IS NULL
            """)
            products = cur.fetchall()
    finally:
        conn.close()

    if not products:
        print("All products already have embeddings.")
        return

    print(f"Building embeddings for {len(products)} products ...")
    texts = [product_text(p) for p in products]
    embeddings = get_embeddings_batch(texts)

    pairs = [(p["id"], emb) for p, emb in zip(products, embeddings)]
    upsert_embeddings_batch(pairs)

    for p in products:
        print(f"  product_id={p['id']}  {p['name']}")

    print("Done.")


if __name__ == "__main__":
    build_all_embeddings()
