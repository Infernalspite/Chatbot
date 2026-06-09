from __future__ import annotations

import json
import os
import re
from collections import Counter
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Query

from database import DB_connection

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

PRODUCT_GROUPS = {
    "computer": {
        "mouse", "keyboard", "hub", "webcam", "monitor", "laptop", "desk",
        "office", "chair", "lamp", "arm", "table",
    },
    "audio": {"headphones", "speaker", "bluetooth", "noise", "canceling"},
    "charging": {"charging", "charger", "usb", "hub", "phone", "plug"},
    "fitness": {"fitness", "band", "bands", "yoga", "dumbbell", "foam", "roller", "resistance", "running"},
    "kitchen": {"coffee", "mug", "cups", "knife", "skillet", "cutting", "board", "frother", "press"},
    "travel": {"travel", "backpack", "passport", "umbrella", "pouch", "tote", "wallet", "sunglasses"},
    "home": {"diffuser", "candle", "bonsai", "planter", "pillow", "towel", "soap", "led"},
    "stationery": {"pen", "pens", "journal", "desk"},
}

COMPLEMENT_GROUPS = {
    "computer": {"charging", "audio", "stationery"},
    "audio": {"computer", "charging"},
    "charging": {"computer", "audio", "travel"},
    "fitness": {"travel"},
    "kitchen": {"home"},
    "travel": {"charging", "fitness"},
    "home": {"kitchen"},
    "stationery": {"computer"},
}


def _tokens(name: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    return {word for word in words if len(word) > 2}


def _groups(product: dict) -> set[str]:
    tokens = _tokens(product.get("name", ""))
    return {
        group
        for group, keywords in PRODUCT_GROUPS.items()
        if tokens & keywords
    }


def _format_product(product: dict) -> dict:
    return {
        "id": product["id"],
        "name": product["name"],
        "price": float(product["price"]),
        "stock": product["stock"],
        "image_url": product.get("image_url"),
    }


def _fetch_product(product_id: int) -> dict:
    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, price, stock, image_url
                FROM products
                WHERE id = %s
                """,
                (product_id,),
            )
            product = cur.fetchone()
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
            return product
    finally:
        conn.close()


def _fetch_candidates(exclude_ids: set[int]) -> list[dict]:
    if not exclude_ids:
        exclude_ids = {-1}

    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(exclude_ids))
            cur.execute(
                f"""
                SELECT
                    p.id,
                    p.name,
                    p.price,
                    p.stock,
                    p.image_url,
                    COALESCE(SUM(oi.quantity), 0) AS sold_count
                FROM products p
                LEFT JOIN order_items oi ON oi.product_id = p.id
                WHERE p.stock > 0
                  AND p.id NOT IN ({placeholders})
                GROUP BY p.id, p.name, p.price, p.stock, p.image_url
                """,
                tuple(exclude_ids),
            )
            return cur.fetchall()
    finally:
        conn.close()


def _co_purchase_counts(product_id: int, candidate_ids: set[int]) -> Counter[int]:
    if not candidate_ids:
        return Counter()

    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(candidate_ids))
            cur.execute(
                f"""
                SELECT oi2.product_id, SUM(oi2.quantity) AS score
                FROM order_items oi1
                JOIN order_items oi2 ON oi2.order_id = oi1.order_id
                WHERE oi1.product_id = %s
                  AND oi2.product_id IN ({placeholders})
                GROUP BY oi2.product_id
                """,
                (product_id, *candidate_ids),
            )
            return Counter(
                {row["product_id"]: int(row["score"] or 0) for row in cur.fetchall()}
            )
    finally:
        conn.close()


def _rank_products_locally(source: dict, candidates: list[dict]) -> list[dict]:
    source_tokens = _tokens(source["name"])
    source_groups = _groups(source)
    co_purchase_counts = _co_purchase_counts(
        source["id"], {candidate["id"] for candidate in candidates}
    )

    ranked = []
    for candidate in candidates:
        candidate_tokens = _tokens(candidate["name"])
        candidate_groups = _groups(candidate)
        sold_count = int(candidate.get("sold_count") or 0)
        stock = int(candidate.get("stock") or 0)

        score = 0.0
        score += co_purchase_counts[candidate["id"]] * 12.0
        score += len(source_tokens & candidate_tokens) * 2.0
        score += len(source_groups & candidate_groups) * 7.0

        complementary_groups = set()
        for group in source_groups:
            complementary_groups.update(COMPLEMENT_GROUPS.get(group, set()))
        score += len(complementary_groups & candidate_groups) * 2.5

        # Low-weight tie breakers only, so these do not make every product identical.
        score += min(sold_count, 10) * 0.03
        score += min(stock, 50) * 0.005

        ranked.append((score, candidate))

    ranked.sort(key=lambda item: (item[0], item[1]["stock"], item[1]["name"]), reverse=True)
    return [product for _, product in ranked]


def _groq_rank_products(source: dict, candidates: list[dict], limit: int) -> list[dict]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return []

    compact_candidates = [
        {
            "id": product["id"],
            "name": product["name"],
            "price": float(product["price"]),
            "stock": product["stock"],
        }
        for product in candidates[:40]
    ]

    prompt = (
        "Recommend products for a shopping cart based on the product the customer just added.\n"
        "Pick items that are similar, useful accessories, or commonly complementary.\n"
        "Return ONLY a JSON array of product ids, no markdown and no explanation.\n\n"
        f"Just added product:\n{json.dumps(_format_product(source), default=str)}\n\n"
        f"Candidate products:\n{json.dumps(compact_candidates, default=str)}\n\n"
        f"Return exactly {limit} ids if possible."
    )

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
                        "You are an e-commerce recommendation engine. "
                        "Use only the candidate product ids. Output valid JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        },
        timeout=20,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"].strip()
    ids = json.loads(re.sub(r"^```json|```$", "", content, flags=re.IGNORECASE).strip())
    if not isinstance(ids, list):
        return []

    by_id = {product["id"]: product for product in candidates}
    ranked = []
    seen = set()
    for raw_id in ids:
        try:
            product_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if product_id in by_id and product_id not in seen:
            ranked.append(by_id[product_id])
            seen.add(product_id)
        if len(ranked) >= limit:
            break
    return ranked


@router.get("/{product_id}")
def get_recommendations(
    product_id: int,
    limit: int = Query(default=4, ge=1, le=12),
    exclude_ids: Optional[str] = Query(
        default=None,
        description="Comma-separated product IDs to exclude, such as cart items.",
    ),
):
    exclude_set = {product_id}
    if exclude_ids:
        for raw_id in exclude_ids.split(","):
            raw_id = raw_id.strip()
            if raw_id.isdigit():
                exclude_set.add(int(raw_id))

    source = _fetch_product(product_id)
    candidates = _fetch_candidates(exclude_set)
    if not candidates:
        return {"strategy": "none", "source_id": product_id, "recommendations": []}

    local_ranked = _rank_products_locally(source, candidates)
    strategy = "database"
    try:
        recommendations = _groq_rank_products(source, local_ranked, limit)
        if recommendations:
            strategy = "groq_ai"
        else:
            recommendations = local_ranked[:limit]
    except Exception:
        recommendations = local_ranked[:limit]

    return {
        "strategy": strategy,
        "source_id": product_id,
        "recommendations": [_format_product(product) for product in recommendations],
    }
