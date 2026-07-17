from fastapi import BackgroundTasks, FastAPI, HTTPException, Path, Query, Depends, Header, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from schema import User, Product, ProductFilterRequest, Order, OrderItem, ItemData, RoleUpdate, LoginRequest
from typing import List, Optional
import pymysql
import pymysql.cursors
import os
import json
import re
import shutil
import uuid
import random
import requests as http_requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path as FilePath

# Load env variables (such as GROQ_API_KEY) from .env file
load_dotenv()
load_dotenv(FilePath(__file__).with_name(".env.txt"))

from database import DB_connection, DB_TYPE
from auth import hash_password, verify_password, create_access_token
import rbac
import mange
import chatbot
import recommendations  # ← RECOMMENDATION ENGINE
import analytics         # ← NEW: Admin analytics router
from setup_db import setup as setup_database
from product_classifier import (
    CATEGORIES,
    classify_and_update_product,
    ensure_product_ai_columns,
    process_uncategorized_products,
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
# Ensure static uploads directory exists
os.makedirs("static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def prepare_product_ai_fields():
    setup_database()
    ensure_product_ai_columns()
    process_uncategorized_products()


# Include the refactored routers
app.include_router(rbac.router)
app.include_router(mange.router)
app.include_router(chatbot.router)
app.include_router(recommendations.router)  # ← RECOMMENDATION ENGINE
app.include_router(analytics.router)         # ← NEW: Admin analytics


DELIVERY_STATUSES = [
    ("Preparing", "Warehouse A", "Order packed and waiting for pickup."),
    ("Shipped", "North Sorting Center", "Package has left the warehouse."),
    ("On the way", "City Distribution Hub", "Driver is moving toward the delivery address."),
    ("Out for delivery", "Near customer area", "Driver is scheduled to arrive today."),
]


def assign_delivery(cursor, order_id: int):
    cursor.execute("SELECT id FROM users WHERE role = %s ORDER BY id", ("driver",))
    drivers = cursor.fetchall()
    if not drivers:
        return None

    driver = random.choice(drivers)
    status, location, note = random.choice(DELIVERY_STATUSES)
    shipped_at = datetime.now() - timedelta(hours=random.randint(1, 30))
    estimated_delivery = datetime.now() + timedelta(days=random.randint(1, 4))
    cursor.execute(
        """
        INSERT INTO deliveries (
            order_id, driver_id, status, shipped_at,
            estimated_delivery, current_location, tracking_note
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            order_id,
            driver["id"],
            status,
            shipped_at,
            estimated_delivery,
            location,
            note,
        ),
    )
    return driver["id"]

@app.get("/users")
def get_users():
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            sql = "SELECT id, name, email, role FROM users"
            cursor.execute(sql)
            result = cursor.fetchall()
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@app.get("/users/{user_id}")
def get_user(user_id: int = Path(...)):
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            # First check if user exists
            check_sql = "SELECT id, name, email, role FROM users WHERE id = %s"
            cursor.execute(check_sql, (user_id,))
            user_info = cursor.fetchone()
            
            if not user_info:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get user's orders
            sql = """
                SELECT 
                u.id, u.name, u.email, u.role,
                p.name AS product_name,
                p.price, oi.quantity,
                o.id AS order_id,
                oi.product_id,
                d.status AS delivery_status,
                d.shipped_at,
                d.estimated_delivery,
                d.current_location,
                d.tracking_note,
                driver.name AS driver_name
            FROM users u
            LEFT JOIN orders o       ON u.id          = o.user_id
            LEFT JOIN order_items oi ON o.id          = oi.order_id
            LEFT JOIN products p     ON oi.product_id = p.id
            LEFT JOIN deliveries d    ON d.order_id   = o.id
            LEFT JOIN users driver    ON driver.id    = d.driver_id
            WHERE u.id = %s
                   """
            cursor.execute(sql, (user_id,))
            result = cursor.fetchall()
            
            # If user has no orders, return an empty order list.
            # The frontend order view expects every returned row to have order_id.
            if not result or all(item.get('order_id') is None for item in result):
                return []
            
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@app.post("/users")
def create_user(user: User):
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            # Hash password before storing it
            hashed_pwd = hash_password(user.password)
            sql = "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)"
            cursor.execute(sql, (user.name, user.email, hashed_pwd))
            connection.commit()
            return {"message": "User created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@app.post("/users/login")
def login(credentials: LoginRequest):
    connection = None
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            username = credentials.username.strip()
            sql = """
                SELECT id, name, email, role, password
                FROM users
                WHERE TRIM(name) = %s OR email = %s
            """
            cursor.execute(sql, (username, username))
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            db_password = user.get('password')
            if not verify_password(credentials.password, db_password):
                raise HTTPException(status_code=401, detail="Incorrect password")
            
            user.pop('password', None)
            
            # Generate JWT Access Token
            token = create_access_token({
                "id": user.get("id"),
                "name": user.get("name"),
                "email": user.get("email"),
                "role": user.get("role", "user")
            })
            
            # Return inside a list for backward compatibility with existing streamlit logic
            return [{
                "token": token,
                "id": user.get("id"),
                "name": user.get("name"),
                "email": user.get("email"),
                "role": user.get("role", "user")
            }]
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if connection:
            connection.close()


@app.get("/products")
def get_products():
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            sql = """SELECT id, name, price, stock, image_url, ai_category, ai_categories, ai_processed,
                           COALESCE(locality, '') AS locality, COALESCE(vendor_id, 0) AS vendor_id,
                           COALESCE(low_stock_threshold, 10) AS low_stock_threshold
                    FROM products"""
            cursor.execute(sql)
            result = cursor.fetchall()
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


# ── NEW: Bulk stock-status endpoint (hyperlocal real-time polling) ─────────────
@app.get("/products/stock-status")
def get_stock_status():
    """Return live stock levels for all products — used for real-time polling."""
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, name, stock,
                          COALESCE(low_stock_threshold, 10) AS low_stock_threshold,
                          COALESCE(locality, '') AS locality
                   FROM products ORDER BY id"""
            )
            rows = cursor.fetchall()
        result = []
        for r in rows:
            stock = int(r["stock"] or 0)
            threshold = int(r["low_stock_threshold"] or 10)
            if stock <= 0:
                status = "out_of_stock"
            elif stock <= threshold:
                status = "low_stock"
            else:
                status = "in_stock"
            result.append({
                "id": r["id"],
                "name": r["name"],
                "stock": stock,
                "low_stock_threshold": threshold,
                "locality": r["locality"],
                "status": status,
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


# ── NEW: Vendor products endpoint ─────────────────────────────────────────────
@app.get("/vendor/products")
def get_vendor_products(vendor_id: int = Query(...)):
    """Return only the products owned by a specific vendor (by user id)."""
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, name, price, stock, image_url, ai_category,
                          COALESCE(locality, '') AS locality,
                          COALESCE(low_stock_threshold, 10) AS low_stock_threshold
                   FROM products WHERE vendor_id = %s ORDER BY id DESC""",
                (vendor_id,),
            )
            return cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


# ── NEW: Get unique localities ─────────────────────────────────────────────────
@app.get("/products/localities")
def get_localities():
    """Return distinct locality values for the hyperlocal neighborhood filter."""
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT locality FROM products WHERE locality IS NOT NULL AND locality != '' ORDER BY locality"
            )
            rows = cursor.fetchall()
        return [r["locality"] for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@app.post("/api/products")
def create_product_api(product: Product, background_tasks: BackgroundTasks):
    connection = None
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            if DB_TYPE == "mysql":
                cursor.execute(
                    """INSERT INTO products (name, price, stock, image_url, locality, vendor_id, low_stock_threshold)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (product.name, product.price, product.stock, product.image_url,
                     product.locality, product.vendor_id, product.low_stock_threshold),
                )
                product_id = cursor.lastrowid
            else:
                cursor.execute(
                    """INSERT INTO products (name, price, stock, image_url, locality, vendor_id, low_stock_threshold)
                       VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (product.name, product.price, product.stock, product.image_url,
                     product.locality, product.vendor_id, product.low_stock_threshold),
                )
                product_id = cursor.fetchone()["id"]
            connection.commit()
        background_tasks.add_task(classify_and_update_product, product_id)
        return {"message": "Product created successfully", "product_id": product_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if connection:
            connection.close()


@app.get("/api/products/categorized")
def get_categorized_products():
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, price, stock, image_url, ai_category, ai_categories, ai_processed,
                       COALESCE(locality, '') AS locality
                FROM products
                ORDER BY ai_category, name
                """
            )
            products = cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()

    grouped = {category: [] for category in CATEGORIES}
    for product in products:
        raw_categories = product.get("ai_categories")
        categories = []
        if raw_categories:
            if isinstance(raw_categories, str):
                try:
                    categories = json.loads(raw_categories)
                except json.JSONDecodeError:
                    categories = []
            elif isinstance(raw_categories, list):
                categories = raw_categories

        if not categories:
            categories = [product.get("ai_category") or "Other"]

        valid_categories = [
            category for category in categories if category in grouped
        ] or ["Other"]

        product["ai_categories"] = valid_categories
        for category in valid_categories:
            grouped[category].append(product)
    return grouped


def _product_categories(product: dict) -> list[str]:
    raw_categories = product.get("ai_categories")
    categories = []
    if raw_categories:
        if isinstance(raw_categories, str):
            try:
                categories = json.loads(raw_categories)
            except json.JSONDecodeError:
                categories = []
        elif isinstance(raw_categories, list):
            categories = raw_categories
    if not categories:
        categories = [product.get("ai_category") or "Other"]
    return [category for category in categories if category in CATEGORIES] or ["Other"]


def _group_products(products: list[dict], allowed_categories: list[str] | None = None) -> dict:
    visible_categories = allowed_categories or CATEGORIES
    grouped = {category: [] for category in CATEGORIES}
    seen_by_category = {category: set() for category in CATEGORIES}
    for product in products:
        categories = _product_categories(product)
        product["ai_categories"] = categories
        for category in categories:
            if category not in visible_categories:
                continue
            if product["id"] not in seen_by_category[category]:
                grouped[category].append(product)
                seen_by_category[category].add(product["id"])
    return grouped


def _infer_filter_intent(filter_request: ProductFilterRequest) -> dict:
    query = (filter_request.query or "").strip()
    requested_category = filter_request.category if filter_request.category in CATEGORIES else None
    requested_sort = filter_request.sort_by or "ai"
    ignored_keywords = {
        "cheap", "cheaper", "lowest", "low", "expensive", "highest", "high",
        "under", "below", "above", "over", "products", "product", "items",
        "item", "category", "categories", "sort", "show", "find",
        *[category.lower() for category in CATEGORIES],
    }
    fallback = {
        "categories": [requested_category] if requested_category else [],
        "keywords": [
            word for word in re.findall(r"[a-z0-9]+", query.lower())
            if len(word) > 2 and word not in ignored_keywords and not word.isdigit()
        ],
        "min_price": None,
        "max_price": None,
        "in_stock_only": True,
        "sort_by": requested_sort,
    }

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not query:
        return fallback

    prompt = {
        "query": query,
        "selected_category": requested_category or "All",
        "selected_sort": requested_sort,
        "allowed_categories": CATEGORIES,
        "allowed_sort_by": ["ai", "name_asc", "price_low", "price_high", "stock_high"],
        "output_schema": {
            "categories": ["zero or more allowed categories"],
            "keywords": ["search words from the user's intent"],
            "min_price": "number or null",
            "max_price": "number or null",
            "in_stock_only": "boolean",
            "sort_by": "one allowed sort value",
        },
    }

    try:
        response = http_requests.post(
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
                            "Convert shopping filter text into strict JSON. "
                            "Use only allowed categories and sort values."
                        ),
                    },
                    {"role": "user", "content": json.dumps(prompt, default=str)},
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            timeout=15,
        )
        response.raise_for_status()
        intent = json.loads(response.json()["choices"][0]["message"]["content"])
    except Exception:
        return fallback

    categories = [
        category for category in intent.get("categories", [])
        if category in CATEGORIES
    ]
    if requested_category and requested_category not in categories:
        categories.insert(0, requested_category)

    sort_by = intent.get("sort_by") if intent.get("sort_by") in {
        "ai", "name_asc", "price_low", "price_high", "stock_high"
    } else requested_sort

    return {
        "categories": categories,
        "keywords": [
            str(word).lower()
            for word in intent.get("keywords", [])
            if str(word).strip()
            and str(word).lower() not in ignored_keywords
            and not str(word).isdigit()
        ],
        "min_price": intent.get("min_price"),
        "max_price": intent.get("max_price"),
        "in_stock_only": bool(intent.get("in_stock_only", True)),
        "sort_by": sort_by,
    }


@app.post("/api/products/filter")
def filter_products(filter_request: ProductFilterRequest):
    intent = _infer_filter_intent(filter_request)
    locality_filter = getattr(filter_request, "locality", None)
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, price, stock, image_url, ai_category, ai_categories, ai_processed,
                       COALESCE(locality, '') AS locality
                FROM products
                """
            )
            products = cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()

    filtered = []
    for product in products:
        categories = _product_categories(product)
        name = (product.get("name") or "").lower()
        price = float(product.get("price") or 0)
        stock = int(product.get("stock") or 0)
        locality = (product.get("locality") or "").lower()

        if intent["categories"] and not set(intent["categories"]) & set(categories):
            continue
        if intent["in_stock_only"] and stock <= 0:
            continue
        if intent["min_price"] is not None and price < float(intent["min_price"]):
            continue
        if intent["max_price"] is not None and price > float(intent["max_price"]):
            continue
        if intent["keywords"] and not all(word in name for word in intent["keywords"]):
            continue
        # Hyperlocal: neighborhood filter
        if locality_filter and locality_filter.lower() not in locality:
            continue

        product["ai_categories"] = categories
        filtered.append(product)

    sort_by = intent["sort_by"]
    if sort_by == "name_asc":
        filtered.sort(key=lambda product: product["name"])
    elif sort_by == "price_low":
        filtered.sort(key=lambda product: float(product["price"]))
    elif sort_by == "price_high":
        filtered.sort(key=lambda product: float(product["price"]), reverse=True)
    elif sort_by == "stock_high":
        filtered.sort(key=lambda product: int(product["stock"] or 0), reverse=True)
    else:
        filtered.sort(key=lambda product: (product.get("ai_category") or "Other", product["name"]))

    return {
        "intent": intent,
        "count": len(filtered),
        "grouped": _group_products(filtered, intent["categories"] or None),
    }


@app.post("/products/upload-image")
def upload_image(file: UploadFile = File(...)):
    """Upload product image file and return its hosted static URL"""
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Only JPEG, PNG, JPG, and WEBP files are allowed.")
        
        # Generate a unique filename to prevent conflicts
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Path where the file will be saved
        file_path = os.path.join("static/images", unique_filename)
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return the static URL
        url = f"http://localhost:8000/static/images/{unique_filename}"
        return {"image_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@app.post("/orders")
def create_order(payload: Order):
    """Create order with atomic stock reservation — prevents overselling."""
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            if DB_TYPE == "mysql":
                cursor.execute("INSERT INTO orders (user_id) VALUES (%s)", (payload.user_id,))
                order_id = cursor.lastrowid
            else:
                cursor.execute("INSERT INTO orders (user_id) VALUES (%s) RETURNING id", (payload.user_id,))
                order_id = cursor.fetchone()["id"]

            # ── Atomic stock reservation with concurrency guard ────────────
            sql_item = "INSERT INTO order_items (order_id, product_id, quantity) VALUES (%s, %s, %s)"
            for item in payload.items:
                # Atomically decrement stock only if sufficient quantity exists
                if DB_TYPE == "mysql":
                    cursor.execute(
                        """UPDATE products
                           SET stock = stock - %s
                           WHERE id = %s AND stock >= %s""",
                        (item.quantity, item.product_id, item.quantity),
                    )
                else:
                    cursor.execute(
                        """UPDATE products
                           SET stock = stock - %s
                           WHERE id = %s AND stock >= %s""",
                        (item.quantity, item.product_id, item.quantity),
                    )
                if cursor.rowcount == 0:
                    connection.rollback()
                    raise HTTPException(
                        status_code=409,
                        detail=f"Insufficient stock for product {item.product_id}. Order cancelled.",
                    )
                cursor.execute(sql_item, (order_id, item.product_id, item.quantity))

            driver_id = assign_delivery(cursor, order_id)
            connection.commit()
            return {
                "message": "Order created successfully",
                "order_id": order_id,
                "driver_id": driver_id,
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@app.get("/deliveries/order/{order_id}")
def get_delivery_for_order(order_id: int = Path(...)):
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    d.id AS delivery_id,
                    d.order_id,
                    d.driver_id,
                    driver.name AS driver_name,
                    d.status,
                    d.shipped_at,
                    d.estimated_delivery,
                    d.current_location,
                    d.tracking_note,
                    d.updated_at
                FROM deliveries d
                JOIN users driver ON driver.id = d.driver_id
                WHERE d.order_id = %s
                """,
                (order_id,),
            )
            delivery = cursor.fetchone()
            if not delivery:
                raise HTTPException(status_code=404, detail="Delivery not found")
            return delivery
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@app.get("/drivers/{driver_id}/deliveries")
def get_driver_deliveries(driver_id: int = Path(...)):
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    d.id AS delivery_id,
                    d.order_id,
                    d.status,
                    d.shipped_at,
                    d.estimated_delivery,
                    d.current_location,
                    d.tracking_note,
                    d.updated_at,
                    u.id AS customer_id,
                    u.name AS customer_name,
                    p.name AS product_name,
                    p.price,
                    oi.quantity
                FROM deliveries d
                JOIN orders o ON o.id = d.order_id
                JOIN users u ON u.id = o.user_id
                JOIN order_items oi ON oi.order_id = o.id
                JOIN products p ON p.id = oi.product_id
                WHERE d.driver_id = %s
                ORDER BY d.updated_at DESC, d.order_id DESC
                """,
                (driver_id,),
            )
            return cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@app.delete("/orders/{order_id}")
def delete_order(order_id: int = Path(...)):
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            sql_delete_items = "DELETE FROM order_items WHERE order_id = %s"
            cursor.execute(sql_delete_items, (order_id,))
            
            sql_delete_order = "DELETE FROM orders WHERE id = %s"
            cursor.execute(sql_delete_order, (order_id,))
            
            connection.commit()
            return {"message": "Order deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@app.put("/orders/{order_id}")
def update_order(order_id: int, payload: Order):
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            sql_delete_items = "DELETE FROM order_items WHERE order_id = %s"
            cursor.execute(sql_delete_items, (order_id,))
            
            sql_update_order = "UPDATE orders SET user_id = %s WHERE id = %s"
            cursor.execute(sql_update_order, (payload.user_id, order_id))
            
            sql_insert_item = "INSERT INTO order_items (order_id, product_id, quantity) VALUES (%s, %s, %s)"
            for item in payload.items:
                cursor.execute(sql_insert_item, (order_id, item.product_id, item.quantity))
            
            connection.commit()
            return {"message": "Order updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@app.get("/items", response_model=List[ItemData])
def get_items():
    """Get all items with Pydantic response model"""
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            sql = "SELECT id, name AS title, email AS description FROM users LIMIT 5"
            cursor.execute(sql)
            result = cursor.fetchall()
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()
