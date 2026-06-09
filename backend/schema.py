from pydantic import BaseModel
from typing import List, Optional

class User(BaseModel):
    name: str
    email: str
    password: str

class Product(BaseModel):
    name: str
    price: float
    stock: int
    image_url: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class ProductFilterRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    sort_by: Optional[str] = "ai"

class ItemData(BaseModel):
    id: int
    title: str
    description: str

class OrderItem(BaseModel):
    product_id: int
    quantity: int

class Order(BaseModel):
    user_id: int
    items: List[OrderItem]

class RoleUpdate(BaseModel):
    role: str  # "user", "manager", or "admin"

class LoginRequest(BaseModel):
    username: str
    password: str
