from fastapi import FastAPI, HTTPException, Path, Query, Depends, Header, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from schema import User, Product, Order, OrderItem, ItemData, RoleUpdate, LoginRequest
from typing import List, Optional
import pymysql
import pymysql.cursors
import os
import shutil
import uuid
from dotenv import load_dotenv

# Load env variables (such as GROQ_API_KEY) from .env file
load_dotenv()

from database import DB_connection
from auth import hash_password, verify_password, create_access_token
import rbac
import mange
import chatbot
import recommendations  # ← RECOMMENDATION ENGINE

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


# Include the refactored routers
app.include_router(rbac.router)
app.include_router(mange.router)
app.include_router(chatbot.router)
app.include_router(recommendations.router)  # ← RECOMMENDATION ENGINE


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
                oi.product_id
            FROM users u
            LEFT JOIN orders o       ON u.id          = o.user_id
            LEFT JOIN order_items oi ON o.id          = oi.order_id
            LEFT JOIN products p     ON oi.product_id = p.id
            WHERE u.id = %s
                   """
            cursor.execute(sql, (user_id,))
            result = cursor.fetchall()
            
            # If user has no orders, return just the user info
            if not result or all(item.get('order_id') is None for item in result):
                return [user_info]
            
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
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            sql = "SELECT id, name, email, role, password FROM users WHERE name = %s"
            cursor.execute(sql, (credentials.username,))
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
        connection.close()


@app.get("/products")
def get_products():
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            sql = "SELECT id, name, price, stock, image_url FROM products"
            cursor.execute(sql)
            result = cursor.fetchall()
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


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
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            sql_order = "INSERT INTO orders (user_id) VALUES (%s) RETURNING id"
            cursor.execute(sql_order, (payload.user_id,))
            order_id = cursor.fetchone()["id"]
            
            sql_item = "INSERT INTO order_items (order_id, product_id, quantity) VALUES (%s, %s, %s)"
            for item in payload.items:
                cursor.execute(sql_item, (order_id, item.product_id, item.quantity))
            
            connection.commit()
            return {"message": "Order created successfully"}
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
