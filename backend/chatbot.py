import json
import os
import re
from typing import List, Literal, Optional

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from database import DB_connection
from security import (
    INJECTION_REPLY,
    MAX_MESSAGE_LENGTH,
    OFF_TOPIC_REPLY,
    ROUTER_SECURITY_RULES,
    SECURITY_RULES,
    detect_prompt_injection,
    filter_response_output,
    is_off_topic,
    sanitize_message,
    validate_history,
    validate_router_output,
    validate_sql_query,
    wrap_catalog_context,
    wrap_user_message,
)

router = APIRouter()


@router.get("/chat", response_class=HTMLResponse)
def chat_browser_help():
    return """
    <!doctype html>
    <html>
      <head><title>Shopsite Chat API</title></head>
      <body style="font-family: Arial, sans-serif; padding: 32px;">
        <h2>Shopsite chat API is running.</h2>
        <p>This address is the backend chat endpoint. Open the shop frontend instead.</p>
        <p><a href="http://127.0.0.1:8502">Open local shop frontend</a></p>
      </body>
    </html>
    """


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=MAX_MESSAGE_LENGTH)


class CartItem(BaseModel):
    product_id: int
    name: str = Field(..., max_length=120)
    price: float = Field(..., ge=0)
    quantity: int = Field(..., ge=1)


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=MAX_MESSAGE_LENGTH)
    history: Optional[List[Message]] = Field(default_factory=list, max_length=10)
    user_id: Optional[int] = None
    cart_items: List[CartItem] = Field(default_factory=list, max_length=50)


class ChatResponse(BaseModel):
    reply: str
    error: Optional[bool] = None


class CartSummaryRequest(BaseModel):
    items: List[CartItem] = Field(default_factory=list, max_length=50)


class CartSummaryResponse(BaseModel):
    reply: str
    item_count: int
    unique_count: int
    total_price: float
    error: Optional[bool] = None


def get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise Exception("Missing GROQ_API_KEY in environment variables or .env file.")
    return key


def run_select_query(sql: str) -> str:
    """Run a SELECT query and return context text for the reply model."""
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            if not rows:
                return "INVENTORY_EMPTY: No products matched the customer's question."
            return f"INVENTORY_DATA:\n{json.dumps(rows, indent=2, default=str)}"
    except Exception as e:
        return f"INVENTORY_ERROR: {str(e)}"
    finally:
        if "connection" in locals() and connection:
            connection.close()


def fetch_user_orders(user_id: Optional[int]) -> str:
    if not user_id:
        return "ORDER_CONTEXT: The customer is not logged in, so saved orders cannot be loaded."

    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    o.id AS order_id,
                    o.created_at,
                    p.id AS product_id,
                    p.name AS product_name,
                    p.price,
                    oi.quantity,
                    d.status AS delivery_status,
                    d.shipped_at,
                    d.estimated_delivery,
                    d.current_location,
                    d.tracking_note,
                    driver.name AS driver_name
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                JOIN products p ON p.id = oi.product_id
                LEFT JOIN deliveries d ON d.order_id = o.id
                LEFT JOIN users driver ON driver.id = d.driver_id
                WHERE o.user_id = %s
                ORDER BY o.id DESC, oi.id ASC
                LIMIT 50
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            if not rows:
                return "ORDER_CONTEXT: This customer has no saved orders yet."
            return f"ORDER_CONTEXT:\n{json.dumps(rows, indent=2, default=str)}"
    except Exception as e:
        return f"ORDER_CONTEXT_ERROR: {str(e)}"
    finally:
        if "connection" in locals() and connection:
            connection.close()


def build_cart_context(items: List[CartItem]) -> str:
    if not items:
        return "CART_CONTEXT: The customer's current cart is empty."

    total_items = sum(item.quantity for item in items)
    total_price = round(sum(item.price * item.quantity for item in items), 2)
    cart_rows = [
        {
            "product_id": item.product_id,
            "name": item.name,
            "quantity": item.quantity,
            "unit_price": item.price,
            "line_total": round(item.price * item.quantity, 2),
        }
        for item in items
    ]
    return (
        "CART_CONTEXT:\n"
        + json.dumps(
            {
                "total_item_count": total_items,
                "unique_product_count": len(items),
                "cart_total": total_price,
                "items": cart_rows,
            },
            indent=2,
            default=str,
        )
    )


def is_cart_question(message: str) -> bool:
    return bool(re.search(r"\b(cart|basket|bag|checkout|current items?|items? in my cart)\b", message, re.I))


def is_order_question(message: str) -> bool:
    return bool(re.search(
        r"\b(order|orders|ordered|purchase|purchases|bought|receipt|delivery|deliveries|shipping|shipped|tracking|status|driver)\b",
        message,
        re.I,
    ))


def build_reply_system_prompt(db_context: str, cart_context: str = "", order_context: str = "") -> str:
    base = (
        SECURITY_RULES
        + "You are a friendly e-commerce customer support assistant.\n"
        "Answer the customer's question warmly and concisely in 2-3 sentences.\n"
        "Use the provided cart context for current cart questions and order context for saved order questions.\n"
        "For delivery questions, answer from the delivery fields in order context: delivery_status, driver_name, shipped_at, estimated_delivery, current_location, and tracking_note.\n"
        "The cart is not the same as saved orders: cart items are not ordered yet.\n"
        "Never mention SQL, databases, queries, or technical details. Speak naturally.\n\n"
    )
    context_parts = [part for part in (cart_context, order_context, db_context) if part]
    if not context_parts:
        return base + "Answer from general store knowledge, such as returns, shipping, or policies."

    if db_context.startswith("INVENTORY_EMPTY"):
        return (
            base
            + wrap_catalog_context("\n\n".join(part for part in (cart_context, order_context) if part))
            + "\n"
            + "The catalog has no products matching what they asked for. "
            "Tell them clearly we do not carry that item right now and offer one brief alternative.\n"
        )

    if db_context.startswith("INVENTORY_ERROR"):
        return (
            base
            + wrap_catalog_context("\n\n".join(part for part in (cart_context, order_context) if part))
            + "\n"
            + "Inventory lookup failed. Apologize once and ask them to try again shortly. "
            "Do not invent stock or product details.\n"
        )

    return base + wrap_catalog_context("\n\n".join(context_parts))


def ask_ai(input_messages: list) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    try:
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {get_api_key()}",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": input_messages,
                "temperature": 0.1,
            },
            timeout=60,
        )
    except requests.Timeout:
        raise Exception("The AI service timed out. Please try again.")
    except requests.RequestException as exc:
        raise Exception(f"Could not reach the AI service: {exc}")

    try:
        data = response.json()
    except ValueError:
        raise Exception(f"AI service returned an invalid response (HTTP {response.status_code}).")

    if response.status_code != 200:
        msg = data.get("error", {}).get("message") if isinstance(data, dict) else None
        raise Exception(msg or f"AI service error (HTTP {response.status_code}).")

    if isinstance(data, dict) and "error" in data:
        raise Exception(data["error"].get("message", "Groq API error"))

    choices = data.get("choices") if isinstance(data, dict) else None
    if not choices:
        raise Exception("No response from Groq")

    content = choices[0].get("message", {}).get("content")
    if not content or not str(content).strip():
        raise Exception("Groq returned an empty response")

    return str(content).strip()


def build_cart_summary_fallback(items: List[CartItem]) -> str:
    item_count = sum(item.quantity for item in items)
    if item_count == 0:
        return "Your cart is empty. There are 0 items present."

    product_lines = ", ".join(f"{item.quantity} x {item.name}" for item in items)
    item_word = "item" if item_count == 1 else "items"
    return f"Your cart has {item_count} {item_word}: {product_lines}."


def build_order_fallback(order_context: str) -> str:
    if not order_context or order_context.startswith("ORDER_CONTEXT_ERROR"):
        return "I could not load your order details right now. Please try again in a moment."
    if "no saved orders" in order_context.lower():
        return "You do not have any saved orders yet."
    if "not logged in" in order_context.lower():
        return "Please log in first so I can check your order and delivery status."

    try:
        rows = json.loads(order_context.split("ORDER_CONTEXT:", 1)[1].strip())
    except Exception:
        return "Your order details are saved, but I could not format the delivery status right now."

    latest = next((row for row in rows if row.get("order_id")), None)
    if not latest:
        return "You do not have any saved orders yet."

    status = latest.get("delivery_status") or "Preparing"
    order_id = latest.get("order_id")
    driver = latest.get("driver_name") or "not assigned yet"
    location = latest.get("current_location") or "being updated"
    eta = latest.get("estimated_delivery") or "pending"
    note = latest.get("tracking_note") or "We will update tracking soon."
    return (
        f"Order #{order_id} is currently {status}. "
        f"Driver: {driver}. Location: {location}. Estimated delivery: {eta}. {note}"
    )


@router.post("/cart/summary", response_model=CartSummaryResponse)
def summarize_cart(body: CartSummaryRequest):
    items = body.items or []
    item_count = sum(item.quantity for item in items)
    unique_count = len(items)
    total_price = round(sum(item.price * item.quantity for item in items), 2)

    if not items:
        return CartSummaryResponse(
            reply="Your cart is empty. There are 0 items present.",
            item_count=0,
            unique_count=0,
            total_price=0,
        )

    cart_data = [
        {
            "name": item.name,
            "quantity": item.quantity,
            "unit_price": item.price,
            "line_total": round(item.price * item.quantity, 2),
        }
        for item in items
    ]

    try:
        reply = filter_response_output(
            ask_ai(
                [
                    {
                        "role": "system",
                        "content": (
                            SECURITY_RULES
                            + "You are a shopping cart assistant. "
                            "Use only the cart JSON provided by the app. "
                            "Briefly say exactly how many total items are present, "
                            "mention the product names and quantities, and include the cart total. "
                            "Do not recommend products, mention databases, or invent missing items."
                        ),
                    },
                    {
                        "role": "user",
                        "content": wrap_user_message(
                            "Summarize this cart for the customer:\n"
                            + json.dumps(
                                {
                                    "total_item_count": item_count,
                                    "unique_product_count": unique_count,
                                    "cart_total": total_price,
                                    "items": cart_data,
                                },
                                default=str,
                            )
                        ),
                    },
                ]
            )
        )
        return CartSummaryResponse(
            reply=reply,
            item_count=item_count,
            unique_count=unique_count,
            total_price=total_price,
        )
    except Exception as err:
        print(f"Cart summary error: {err}")
        return CartSummaryResponse(
            reply=build_cart_summary_fallback(items),
            item_count=item_count,
            unique_count=unique_count,
            total_price=total_price,
            error=True,
        )


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    message = sanitize_message(body.message)
    history = validate_history(body.history or [])
    cart_context = build_cart_context(body.cart_items)
    order_context = fetch_user_orders(body.user_id) if is_order_question(message) else ""

    if not message:
        raise HTTPException(status_code=400, detail="No message provided")

    if detect_prompt_injection(message):
        return ChatResponse(reply=INJECTION_REPLY)

    if is_off_topic(message):
        return ChatResponse(reply=OFF_TOPIC_REPLY)

    try:
        if is_cart_question(message) or is_order_question(message):
            reply_messages = [
                {
                    "role": "system",
                    "content": build_reply_system_prompt(
                        "",
                        cart_context if is_cart_question(message) or body.cart_items else "",
                        order_context,
                    ),
                }
            ]
            reply_messages.extend(history)
            reply_messages.append({"role": "user", "content": wrap_user_message(message)})
            reply = filter_response_output(ask_ai(reply_messages))
            return ChatResponse(reply=reply)

        router_messages = [
            {
                "role": "system",
                "content": (
                    ROUTER_SECURITY_RULES
                    + "You are an expert SQL assistant for an e-commerce platform.\n"
                    "Your task is to analyze user queries and output ONLY one of:\n"
                    "- a valid MySQL SELECT statement\n"
                    "- the exact word NODB for greetings, policies, or no database lookup\n"
                    "- the exact word OFFTOPIC for unrelated questions\n\n"
                    "Database Schema:\n"
                    "1. products (id INT, name VARCHAR, price DECIMAL, stock INT, image_url VARCHAR, locality VARCHAR, vendor_id INT, low_stock_threshold INT, category VARCHAR, sub_category VARCHAR, description TEXT, tags TEXT, ai_category VARCHAR)\n"
                    "2. orders (id INT, user_id INT, created_at DATETIME)\n"
                    "3. order_items (id INT, order_id INT, product_id INT, quantity INT)\n"
                    "4. deliveries (id INT, order_id INT, driver_id INT, status VARCHAR, shipped_at DATETIME, estimated_delivery DATETIME, current_location VARCHAR, tracking_note VARCHAR)\n\n"
                    "Rules:\n"
                    "- For product/order inquiries, output ONLY the raw SQL query.\n"
                    "- Always use LIMIT 20.\n"
                    "- Do not use markdown backticks or explanations.\n"
                    "- Do not query users or any table outside the schema above."
                ),
            },
            {"role": "user", "content": "Show me all products"},
            {"role": "assistant", "content": "SELECT * FROM products LIMIT 20"},
            {"role": "user", "content": "What is your return policy?"},
            {"role": "assistant", "content": "NODB"},
            {"role": "user", "content": "Which products are out of stock?"},
            {"role": "assistant", "content": "SELECT * FROM products WHERE stock = 0 LIMIT 20"},
            {"role": "user", "content": "Do you have blue shirts?"},
            {
                "role": "assistant",
                "content": "SELECT * FROM products WHERE name LIKE '%blue%' AND name LIKE '%shirt%' LIMIT 20",
            },
            {"role": "user", "content": "How many orders has user 3 made?"},
            {
                "role": "assistant",
                "content": "SELECT COUNT(*) as total_orders FROM orders WHERE user_id = 3 LIMIT 20",
            },
            {"role": "user", "content": wrap_user_message(message)},
        ]

        intent = ask_ai(router_messages)
        router_ok, clean_intent = validate_router_output(intent)
        if not router_ok:
            print(f"Router validation blocked: {clean_intent}")
            return ChatResponse(reply=OFF_TOPIC_REPLY)

        if clean_intent == "OFFTOPIC":
            return ChatResponse(reply=OFF_TOPIC_REPLY)

        db_context = ""
        if clean_intent.upper().startswith("SELECT"):
            is_valid, result = validate_sql_query(clean_intent)
            if not is_valid:
                print(f"SQL validation blocked: {result}")
                db_context = "INVENTORY_ERROR: query blocked for safety"
            else:
                db_context = run_select_query(result)

        reply_messages = [{"role": "system", "content": build_reply_system_prompt(db_context)}]
        reply_messages.extend(history)
        reply_messages.append({"role": "user", "content": wrap_user_message(message)})

        reply = filter_response_output(ask_ai(reply_messages))
        return ChatResponse(reply=reply)

    except Exception as err:
        print(f"Chat error: {err}")
        if is_cart_question(message):
            return ChatResponse(reply=build_cart_summary_fallback(body.cart_items), error=True)
        if is_order_question(message):
            return ChatResponse(reply=build_order_fallback(order_context), error=True)

        msg = str(err)
        lower_msg = msg.lower()
        if "groq_api_key" in lower_msg or "missing groq" in lower_msg:
            detail = "Missing API key. Add GROQ_API_KEY to your .env file."
        elif "invalid api key" in lower_msg or "unauthorized" in lower_msg:
            detail = "Invalid API key. Update GROQ_API_KEY with a valid Groq key."
        elif "ai service" in lower_msg or "groq" in lower_msg:
            detail = msg
        else:
            detail = "Something went wrong. Please try again."
        return ChatResponse(reply=detail, error=True)
