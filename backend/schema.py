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
    locality: Optional[str] = None          # Hyperlocal: vendor's neighborhood
    vendor_id: Optional[int] = None         # Vendor who owns this product
    low_stock_threshold: Optional[int] = 10 # Alert when stock <= this value


class ProductFilterRequest(BaseModel):
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    search: Optional[str] = None
    locality: Optional[str] = None


class Order(BaseModel):
    user_id: int
    items: List[dict]


class OrderItem(BaseModel):
    product_id: int
    quantity: int


class ItemData(BaseModel):
    items: List[dict]


class RoleUpdate(BaseModel):
    role: str


class LoginRequest(BaseModel):
    email: str
    password: str
