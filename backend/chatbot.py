import os
import re
import json
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from database import DB_connection

router = APIRouter()

# ─── Pydantic Models ──────────────────────────────────────────────────────────
class Message(BaseModel):
    role: str       # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = []

class ChatResponse(BaseModel):
    reply: str
    error: Optional[bool] = None

# ─── Helper Functions ─────────────────────────────────────────────────────────
def get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise Exception(
            "Missing GROQ_API_KEY in environment variables or .env file."
        )
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
        if 'connection' in locals() and connection:
            connection.close()


def build_reply_system_prompt(db_context: str) -> str:
    base = (
        "You are a friendly e-commerce customer support assistant.\n"
        "Answer the customer's question warmly and concisely in 2-3 sentences.\n"
        "Never mention SQL, databases, queries, or technical details. Speak naturally.\n\n"
    )
    if not db_context:
        return base + "Answer from general knowledge (returns, shipping, policies, etc)."

    if db_context.startswith("INVENTORY_EMPTY"):
        return (
            base
            + "The catalog has no products matching what they asked for. "
            "Tell them clearly we do not carry that item right now. "
            "Offer one brief alternative (e.g. browse other products). "
            "Do not say systems are down or ask for style/size to avoid answering.\n"
        )

    if db_context.startswith("INVENTORY_ERROR"):
        return (
            base
            + "Inventory lookup failed. Apologize once and ask them to try again shortly. "
            "Do not invent stock, pretend to search, or ask for style/size as a workaround.\n"
        )

    return base + f"Use this catalog data to answer accurately:\n{db_context}\n"


def ask_ai(input_messages: list) -> str:
    """
    Calls the Groq API.
    Accepts a list of message dicts.
    Uses Few-Shot prompting and Role Separation for best accuracy.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"

    response = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {get_api_key()}"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": input_messages,
            "temperature": 0.1
        },
        timeout=30
    )

    data = response.json()

    if "error" in data:
        raise Exception(data["error"].get("message", "Groq API error"))

    if not data.get("choices"):
        raise Exception("No response from Groq")

    return data["choices"][0]["message"]["content"].strip()


# ─── Chat Endpoint ────────────────────────────────────────────────────────────
@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    message = body.message.strip()
    history = body.history or []

    if not message:
        raise HTTPException(status_code=400, detail="No message provided")

    try:
        # ── Step 1: SQL Router ─────────────────────────────────────────────────
        # Prompt Engineering: System Role + Few-Shot Examples + Schema Definitions
        router_messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert SQL assistant for an e-commerce platform.\n"
                    "Your task is to analyze user queries and output ONLY a valid MySQL SELECT statement, "
                    "OR the exact word 'NODB' if no database lookup is needed.\n\n"
                    "Database Schema:\n"
                    "1. products (id INT, name VARCHAR, price DECIMAL, stock INT, image_url VARCHAR)\n"
                    "2. orders (id INT, user_id INT, created_at DATETIME)\n"
                    "3. order_items (id INT, order_id INT, product_id INT, quantity INT)\n"
                    "4. users (id INT, name VARCHAR, email VARCHAR, role VARCHAR)\n\n"
                    "Rules:\n"
                    "- For product/order/user inquiries, output ONLY the raw SQL query.\n"
                    "- Always use LIMIT 20.\n"
                    "- Do not use markdown backticks or explanations.\n"
                    "- If the question is general (greetings, policies), output NODB."
                )
            },
            # Few-Shot Examples
            {"role": "user",      "content": "Show me all products"},
            {"role": "assistant", "content": "SELECT * FROM products LIMIT 20"},
            {"role": "user",      "content": "What is your return policy?"},
            {"role": "assistant", "content": "NODB"},
            {"role": "user",      "content": "Which products are out of stock?"},
            {"role": "assistant", "content": "SELECT * FROM products WHERE stock = 0 LIMIT 20"},
            {"role": "user",      "content": "Do you have blue shirts?"},
            {"role": "assistant", "content": "SELECT * FROM products WHERE name LIKE '%blue%' AND name LIKE '%shirt%' LIMIT 20"},
            {"role": "user",      "content": "How many orders has user 3 made?"},
            {"role": "assistant", "content": "SELECT COUNT(*) as total_orders FROM orders WHERE user_id = 3 LIMIT 20"},
            # Actual user message
            {"role": "user", "content": message}
        ]

        intent = ask_ai(router_messages)

        # Clean up any markdown backticks the model might add
        clean_intent = re.sub(r"```sql", "", intent, flags=re.IGNORECASE)
        clean_intent = re.sub(r"```", "", clean_intent).strip()

        db_context = ""

        # ── Step 2: Run SQL against the database ───────────────────────────────
        if clean_intent.upper().startswith("SELECT"):
            try:
                db_context = run_select_query(clean_intent)
            except Exception as db_err:
                print(f"DB error: {db_err}")
                db_context = f"INVENTORY_ERROR: {db_err}"

        system_content = build_reply_system_prompt(db_context)

        reply_messages = [{"role": "system", "content": system_content}]

        # Inject conversation history for context awareness
        for h in history:
            reply_messages.append({"role": h.role, "content": h.content})

        reply_messages.append({"role": "user", "content": message})

        reply = ask_ai(reply_messages)
        return ChatResponse(reply=reply)

    except Exception as err:
        print(f"Chat error: {err}")
        raise HTTPException(status_code=500, detail=str(err))
