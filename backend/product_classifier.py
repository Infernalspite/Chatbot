from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

from database import DB_TYPE, DB_connection

CATEGORIES = ["Electronics", "Furniture", "Cosmetics", "Other"]

CATEGORY_KEYWORDS = {
    "Electronics": {
        "mouse", "keyboard", "usb", "hub", "webcam", "watch", "geforce",
        "rtx", "headphones", "charging", "charger", "speaker", "fitness",
        "band", "monitor", "laptop", "led", "plug", "phone",
    },
    "Furniture": {
        "chair", "desk", "lamp", "organizer", "arm", "stand", "mat",
        "table", "pillow", "towel", "planter", "bonsai", "fountain",
    },
    "Cosmetics": {
        "cosmetic", "cosmetics", "makeup", "lipstick", "mascara", "skin",
        "skincare", "cream", "serum", "lotion", "soap", "scented",
        "candle", "diffuser", "aromatherapy",
    },
}


def classify_product(
    name: str,
    description: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[str, list[str], bool]:
    """
    Return (primary_category, categories, ai_processed).

    ai_processed is True only when Groq returns valid structured categories.
    If the AI call fails, callers still get safe deterministic categories and
    ai_processed=False so the product can be retried later.
    """
    try:
        ai_categories = _classify_with_groq(name, description, metadata or {})
    except Exception:
        ai_categories = []
    if ai_categories:
        return ai_categories[0], ai_categories, True
    local_categories = _classify_locally(name, description, metadata or {})
    return local_categories[0], local_categories, False


def classify_and_update_product(product_id: int):
    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, price, stock, image_url FROM products WHERE id = %s",
                (product_id,),
            )
            product = cur.fetchone()
            if not product:
                return

            primary_category, categories, processed = classify_product(
                product.get("name", ""),
                metadata={
                    "price": float(product.get("price") or 0),
                    "stock": product.get("stock"),
                    "image_url": product.get("image_url"),
                },
            )
            cur.execute(
                """
                UPDATE products
                SET ai_category = %s, ai_categories = %s, ai_processed = %s
                WHERE id = %s
                """,
                (primary_category, json.dumps(categories), processed, product_id),
            )
            conn.commit()
    finally:
        conn.close()


def ensure_product_ai_columns():
    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            if DB_TYPE == "mysql":
                cur.execute("SHOW COLUMNS FROM products LIKE 'ai_category'")
                if not cur.fetchone():
                    cur.execute("ALTER TABLE products ADD COLUMN ai_category VARCHAR(40) NULL")

                cur.execute("SHOW COLUMNS FROM products LIKE 'ai_categories'")
                if not cur.fetchone():
                    cur.execute("ALTER TABLE products ADD COLUMN ai_categories JSON NULL")

                cur.execute("SHOW COLUMNS FROM products LIKE 'ai_processed'")
                if not cur.fetchone():
                    cur.execute(
                        "ALTER TABLE products ADD COLUMN ai_processed BOOLEAN NOT NULL DEFAULT FALSE"
                    )

                cur.execute("SHOW INDEX FROM products WHERE Key_name = 'idx_products_ai_category'")
                if not cur.fetchone():
                    cur.execute("CREATE INDEX idx_products_ai_category ON products (ai_category)")
            else:
                cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS ai_category VARCHAR(40)")
                cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS ai_categories JSON")
                cur.execute(
                    "ALTER TABLE products ADD COLUMN IF NOT EXISTS ai_processed BOOLEAN NOT NULL DEFAULT FALSE"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_products_ai_category ON products (ai_category)"
                )
            conn.commit()
    finally:
        conn.close()


def process_uncategorized_products(limit: int = 100):
    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM products
                WHERE ai_categories IS NULL OR ai_categories = ''
                LIMIT %s
                """,
                (limit,),
            )
            product_ids = [row["id"] for row in cur.fetchall()]
    finally:
        conn.close()

    for product_id in product_ids:
        classify_and_update_product(product_id)


def _classify_with_groq(
    name: str,
    description: str | None,
    metadata: dict[str, Any],
) -> list[str]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    prompt = {
        "task": "Classify an e-commerce product into one or more allowed categories.",
        "allowed_categories": CATEGORIES,
        "product": {
            "name": name,
            "description": description or "",
            "metadata": metadata,
        },
        "output_schema": {
            "ai_categories": [
                "one or more of Electronics, Furniture, Cosmetics, Other"
            ]
        },
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You classify products for a store layout. "
                        "Return only valid JSON matching {\"ai_categories\": string[]}. "
                        "Choose every allowed category that reasonably applies. "
                        "Use Other only when none of the specific categories fit. "
                        "Never invent categories outside the allowed list."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, default=str)},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        },
        timeout=20,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    raw_categories = parsed.get("ai_categories", [])
    if isinstance(raw_categories, str):
        raw_categories = [raw_categories]
    categories = _normalize_categories(raw_categories)
    return categories


def _classify_locally(
    name: str,
    description: str | None,
    metadata: dict[str, Any],
) -> list[str]:
    text = " ".join(
        [
            name or "",
            description or "",
            json.dumps(metadata or {}, default=str),
        ]
    ).lower()
    tokens = set(re.findall(r"[a-z0-9]+", text))

    scores = {
        category: len(tokens & keywords)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    categories = [
        category
        for category, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if score > 0
    ]
    return categories or ["Other"]


def _normalize_categories(raw_categories: list[Any]) -> list[str]:
    normalized = []
    for raw_category in raw_categories:
        category = str(raw_category).strip()
        if category in CATEGORIES and category not in normalized:
            normalized.append(category)

    if "Other" in normalized and len(normalized) > 1:
        normalized = [category for category in normalized if category != "Other"]
    return normalized or ["Other"]
