import json
import os
import re
from typing import List, Literal, Optional

import requests
from fastapi import APIRouter, HTTPException
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


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=MAX_MESSAGE_LENGTH)


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=MAX_MESSAGE_LENGTH)
    history: Optional[List[Message]] = Field(default_factory=list, max_length=10)


class ChatResponse(BaseModel):
    reply: str
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


def build_reply_system_prompt(db_context: str) -> str:
    base = (
        SECURITY_RULES
        + "You are a friendly e-commerce customer support assistant.\n"
        "Answer the customer's question warmly and concisely in 2-3 sentences.\n"
        "Never mention SQL, databases, queries, or technical details. Speak naturally.\n\n"
    )
    if not db_context:
        return base + "Answer from general store knowledge, such as returns, shipping, or policies."

    if db_context.startswith("INVENTORY_EMPTY"):
        return (
            base
            + "The catalog has no products matching what they asked for. "
            "Tell them clearly we do not carry that item right now and offer one brief alternative.\n"
        )

    if db_context.startswith("INVENTORY_ERROR"):
        return (
            base
            + "Inventory lookup failed. Apologize once and ask them to try again shortly. "
            "Do not invent stock or product details.\n"
        )

    return base + wrap_catalog_context(db_context)


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


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    message = sanitize_message(body.message)
    history = validate_history(body.history or [])

    if not message:
        raise HTTPException(status_code=400, detail="No message provided")

    if detect_prompt_injection(message):
        return ChatResponse(reply=INJECTION_REPLY)

    if is_off_topic(message):
        return ChatResponse(reply=OFF_TOPIC_REPLY)

    try:
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
                    "1. products (id INT, name VARCHAR, price DECIMAL, stock INT, image_url VARCHAR)\n"
                    "2. orders (id INT, user_id INT, created_at DATETIME)\n"
                    "3. order_items (id INT, order_id INT, product_id INT, quantity INT)\n\n"
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
