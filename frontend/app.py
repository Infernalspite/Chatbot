# pyrefly: ignore [missing-import]
import streamlit as st
import json
import os
import requests
import pandas as pd
import time
from datetime import datetime

# Configure page
st.set_page_config(page_title="NextGen Commerce - Hyperlocal Marketplace", layout="wide")

# Backend API URL
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Custom CSS for Premium Look
st.markdown("""
<style>
    /* Dark Theme & Gradient Header */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0d0c1d 0%, #15142b 50%, #06050b 100%);
        color: #f1f1f1;
    }
    [data-testid="stHeader"] {
        background: rgba(0,0,0,0);
    }
    [data-testid="stSidebar"] {
        background-color: #0b0a14 !important;
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', 'Inter', sans-serif !important;
        font-weight: 700 !important;
    }
    
    .gradient-title {
        background: linear-gradient(90deg, #a855f7 0%, #ec4899 50%, #f43f5e 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem !important;
        font-weight: 800 !important;
        text-shadow: 0 4px 12px rgba(168, 85, 247, 0.15);
        margin-bottom: 0.5rem;
    }
    
    .gradient-subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* Product Cards Styling */
    div.element-container:has(.product-card) {
        margin-bottom: 1.5rem;
    }
    
    .product-card {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 16px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.25);
        backdrop-filter: blur(8px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .product-card:hover {
        transform: translateY(-6px);
        border-color: rgba(168, 85, 247, 0.4);
        box-shadow: 0 12px 35px rgba(168, 85, 247, 0.2);
    }
    
    /* Stock Badges with Pulse Animations */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .badge-in-stock {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .badge-low-stock {
        background: rgba(245, 158, 11, 0.15);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.3);
        animation: pulse-low-stock 2s infinite;
    }
    
    .badge-out-of-stock {
        background: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .badge-locality {
        background: rgba(139, 92, 246, 0.15);
        color: #a78bfa;
        border: 1px solid rgba(139, 92, 246, 0.3);
        margin-right: 5px;
    }

    @keyframes pulse-low-stock {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    /* Flash Sale Banner */
    .flash-sale-banner {
        background: linear-gradient(135deg, #f43f5e 0%, #fb7185 100%);
        border-radius: 12px;
        padding: 15px 25px;
        color: white;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 10px 25px rgba(244, 63, 94, 0.3);
        margin-bottom: 2rem;
        animation: shake 4s infinite;
    }

    @keyframes shake {
        0%, 100% { transform: rotate(0deg); }
        92% { transform: rotate(0.5deg); }
        94% { transform: rotate(-0.5deg); }
        96% { transform: rotate(0.5deg); }
        98% { transform: rotate(-0.5deg); }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "cart" not in st.session_state:
    st.session_state.cart = []
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "token" not in st.session_state:
    st.session_state.token = None
if "recommendations" not in st.session_state:
    st.session_state.recommendations = []
if "recommendation_source_id" not in st.session_state:
    st.session_state.recommendation_source_id = None
if "cart_ai_summary" not in st.session_state:
    st.session_state.cart_ai_summary = None
if "cart_ai_signature" not in st.session_state:
    st.session_state.cart_ai_signature = None
if "active_pill" not in st.session_state:
    st.session_state.active_pill = "All"

def cart_signature() -> tuple:
    return tuple(
        (item["product_id"], item["name"], float(item["price"]), int(item["quantity"]))
        for item in st.session_state.cart
    )

def cart_totals() -> tuple[int, float]:
    total_items = sum(int(item["quantity"]) for item in st.session_state.cart)
    total_price = sum(float(item["price"]) * int(item["quantity"]) for item in st.session_state.cart)
    return total_items, total_price

def fallback_cart_summary() -> dict:
    total_items, total_price = cart_totals()
    if total_items == 0:
        reply = "Your cart is empty. There are 0 items present."
    else:
        item_word = "item" if total_items == 1 else "items"
        products = ", ".join(
            f"{int(item['quantity'])} x {item['name']}"
            for item in st.session_state.cart
        )
        reply = f"Your cart has {total_items} {item_word}: {products}."
    return {
        "reply": reply,
        "item_count": total_items,
        "unique_count": len(st.session_state.cart),
        "total_price": round(total_price, 2),
        "error": True,
    }

def fetch_cart_ai_summary(force: bool = False):
    signature = cart_signature()
    if not force and st.session_state.cart_ai_signature == signature:
        return

    st.session_state.cart_ai_signature = signature
    if not st.session_state.cart:
        st.session_state.cart_ai_summary = fallback_cart_summary()
        return

    try:
        response = requests.post(
            f"{API_URL}/cart/summary",
            json={
                "items": [
                    {
                        "product_id": item["product_id"],
                        "name": item["name"],
                        "price": float(item["price"]),
                        "quantity": int(item["quantity"]),
                    }
                    for item in st.session_state.cart
                ]
            },
            timeout=20,
        )
        if response.status_code == 200:
            st.session_state.cart_ai_summary = response.json()
        else:
            st.session_state.cart_ai_summary = fallback_cart_summary()
    except Exception:
        st.session_state.cart_ai_summary = fallback_cart_summary()

def fetch_recommendations(product_id: int, limit: int = 4):
    cart_ids = ",".join(str(item["product_id"]) for item in st.session_state.cart)
    try:
        rec_res = requests.get(
            f"{API_URL}/recommendations/{product_id}",
            params={"limit": limit, "exclude_ids": cart_ids},
            timeout=5,
        )
        if rec_res.status_code == 200:
            st.session_state.recommendations = rec_res.json().get("recommendations", [])
            st.session_state.recommendation_source_id = product_id
        else:
            st.session_state.recommendations = []
            st.session_state.recommendation_source_id = None
    except Exception:
        st.session_state.recommendations = []
        st.session_state.recommendation_source_id = None

def add_item_to_cart(product: dict, quantity: int = 1):
    existing = next(
        (item for item in st.session_state.cart if item["product_id"] == product["id"]),
        None,
    )
    if existing:
        existing["quantity"] += quantity
    else:
        st.session_state.cart.append({
            "product_id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "quantity": quantity,
        })
    fetch_recommendations(product["id"])

def render_recommendations_for(source_id: int, key_prefix: str):
    if (
        st.session_state.recommendation_source_id != source_id
        or not st.session_state.recommendations
    ):
        return

    st.markdown("#### You Might Also Like")
    rec_cols = st.columns(min(len(st.session_state.recommendations), 2))
    for ri, rec in enumerate(st.session_state.recommendations):
        with rec_cols[ri % len(rec_cols)]:
            with st.container(border=True):
                rec_img = rec.get("image_url") or (
                    "https://images.unsplash.com/photo-1531403009284-440f080d1e12?w=500&auto=format&fit=crop&q=80"
                )
                st.image(rec_img, use_container_width=True)
                st.markdown(f"**{rec['name']}**")
                st.markdown(f"${rec['price']:.2f}")
                if st.button(
                    "Add to Cart",
                    key=f"{key_prefix}_rec_add_{source_id}_{rec['id']}_{ri}",
                    use_container_width=True,
                ):
                    add_item_to_cart(rec, 1)
                    st.success(f"Added {rec['name']}!")
                    st.rerun()

def response_detail(response, fallback: str = "Unknown error"):
    try:
        data = response.json()
        if isinstance(data, dict):
            return data.get("detail") or data.get("message") or fallback
        return fallback
    except ValueError:
        return response.text.strip() or fallback

def render_shop_product_card(product: dict, key_prefix: str):
    with st.container(border=True):
        img_url = product.get('image_url')
        default_placeholder = "https://images.unsplash.com/photo-1531403009284-440f080d1e12?w=500&auto=format&fit=crop&q=80"
        if not img_url:
            img_url = default_placeholder

        st.image(img_url, use_container_width=True)
        st.markdown(f"### {product['name']}")
        st.markdown(f"**Price:** ${product['price']:.2f}")

        # Locality Badge
        locality = product.get("locality") or "Global"
        
        # Real-time stock styling
        stock = int(product.get('stock', 0))
        threshold = int(product.get('low_stock_threshold', 10))
        
        if stock <= 0:
            badge_html = '<span class="badge badge-out-of-stock">🔴 Out of Stock</span>'
            is_disabled = True
        elif stock <= threshold:
            badge_html = f'<span class="badge badge-low-stock">🟡 Low Stock ({stock} left)</span>'
            is_disabled = False
        else:
            badge_html = f'<span class="badge badge-in-stock">🟢 In Stock ({stock})</span>'
            is_disabled = False
            
        st.markdown(f"""
        <div style="margin-bottom: 12px;">
            <span class="badge badge-locality">📍 {locality}</span>
            {badge_html}
        </div>
        """, unsafe_allow_html=True)

        qty = st.number_input(
            "Quantity",
            min_value=1,
            max_value=max(1, stock),
            value=1,
            disabled=is_disabled,
            key=f"{key_prefix}_qty_{product['id']}"
        )

        if st.button(
            "Add to Cart",
            key=f"{key_prefix}_add_{product['id']}",
            use_container_width=True,
            disabled=is_disabled,
        ):
            add_item_to_cart(product, qty)
            st.success(f"Added {qty} to cart!")
            st.rerun()

        render_recommendations_for(product["id"], key_prefix)

# =============== PRODUCT MANAGEMENT HELPERS ===============
def render_add_product(key_prefix: str, vendor_id: Optional[int] = None):
    st.markdown("### Add New Product")
    
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input("Product Name", placeholder="Enter product name", key=f"{key_prefix}_add_name")
    with col2:
        product_price = st.number_input("Price ($)", min_value=0.0, step=0.01, key=f"{key_prefix}_add_price")
    
    col3, col4 = st.columns(2)
    with col3:
        product_stock = st.number_input("Stock Quantity", min_value=0, step=1, key=f"{key_prefix}_add_stock")
    with col4:
        locality = st.text_input("Locality / Neighborhood", placeholder="e.g. Downtown, Uptown", key=f"{key_prefix}_add_locality")

    col5, col6 = st.columns(2)
    with col5:
        low_stock_threshold = st.number_input("Low Stock Threshold Alert", min_value=1, value=10, step=1, key=f"{key_prefix}_add_threshold")
    with col6:
        image_source = st.selectbox(
            "Product Image Option", 
            ["Auto-suggest beautiful stock image based on name", "Provide Image URL", "Upload Image from computer", "None"],
            key=f"{key_prefix}_add_img_source"
        )
    
    final_image_url = None
    if image_source == "Provide Image URL":
        final_image_url = st.text_input("Enter Web Image URL", placeholder="https://example.com/image.jpg", key=f"{key_prefix}_add_img_url")
    elif image_source == "Upload Image from computer":
        uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "webp"], key=f"{key_prefix}_add_uploader")
        if uploaded_file is not None:
            with st.spinner("Uploading image..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    upload_res = requests.post(f"{API_URL}/products/upload-image", files=files)
                    if upload_res.status_code == 200:
                        final_image_url = upload_res.json().get("image_url")
                        st.success("✅ Image uploaded successfully!")
                    else:
                        st.error("❌ Failed to upload image to backend.")
                except Exception as e:
                    st.error(f"❌ Upload error: {str(e)}")
    elif image_source == "Auto-suggest beautiful stock image based on name":
        if product_name:
            search_term = product_name.replace(" ", "")
            final_image_url = f"https://loremflickr.com/640/480/{search_term}"
            st.caption(f"✨ Suggested URL: `{final_image_url}`")
    
    if st.button("➕ Add Product", use_container_width=True, type="primary", key=f"{key_prefix}_add_btn"):
        if product_name and product_price >= 0 and product_stock >= 0:
            try:
                payload = {
                    "name": product_name, 
                    "price": product_price, 
                    "stock": product_stock,
                    "image_url": final_image_url,
                    "locality": locality,
                    "vendor_id": vendor_id,
                    "low_stock_threshold": low_stock_threshold
                }
                headers = {}
                if st.session_state.token:
                    headers["Authorization"] = f"Bearer {st.session_state.token}"
                response = requests.post(
                    f"{API_URL}/products",
                    json=payload,
                    headers=headers
                )
                if response.status_code == 200:
                    st.success(f"✅ Product '{product_name}' added successfully!")
                    st.rerun()
                else:
                    st.error(f"❌ Error: {response.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("⚠️ Please fill in all fields with valid values")

def render_manage_products(key_prefix: str, vendor_only: bool = False):
    st.markdown("### All Products")
    
    if st.button("🔄 Refresh Products", key=f"{key_prefix}_refresh_products"):
        st.rerun()
    
    try:
        if vendor_only:
            response = requests.get(f"{API_URL}/vendor/products?vendor_id={st.session_state.user_id}")
        else:
            response = requests.get(f"{API_URL}/products")
            
        if response.status_code == 200:
            products = response.json()
            
            if products:
                for product in products:
                    with st.expander(f"**{product['name']}** - ${product['price']:.2f} | Stock: {product['stock']} | Locality: {product.get('locality') or 'Global'}"):
                        if product.get('image_url'):
                            st.image(product.get('image_url'), width=150)
                        
                        col1, col2, col3 = st.columns([2, 2, 2])
                        with col1:
                            new_price = st.number_input(
                                "Price ($)",
                                min_value=0.0,
                                value=float(product['price']),
                                step=0.01,
                                key=f"{key_prefix}_price_{product['id']}"
                            )
                        with col2:
                            new_stock = st.number_input(
                                "Stock",
                                min_value=0,
                                value=int(product['stock']),
                                step=1,
                                key=f"{key_prefix}_stock_{product['id']}"
                            )
                        with col3:
                            new_threshold = st.number_input(
                                "Low Stock Threshold",
                                min_value=1,
                                value=int(product.get('low_stock_threshold', 10)),
                                step=1,
                                key=f"{key_prefix}_threshold_{product['id']}"
                            )
                            
                        col4, col5 = st.columns(2)
                        with col4:
                            new_locality = st.text_input(
                                "Locality / Area",
                                value=product.get('locality') or "",
                                key=f"{key_prefix}_locality_{product['id']}"
                            )
                        with col5:
                            image_update_source = st.selectbox(
                                "Update Image Option",
                                ["Keep Current Image", "Provide Image URL", "Upload Image from computer", "None/Remove Image"],
                                key=f"{key_prefix}_img_src_{product['id']}"
                            )
                        
                        updated_image_url = product.get('image_url')
                        if image_update_source == "Provide Image URL":
                            updated_image_url = st.text_input(
                                "New Image URL", 
                                value=product.get('image_url') or "", 
                                key=f"{key_prefix}_img_url_val_{product['id']}"
                            )
                        elif image_update_source == "None/Remove Image":
                            updated_image_url = None
                        elif image_update_source == "Upload Image from computer":
                            uploaded_file_edit = st.file_uploader(
                                "Choose a new image...", 
                                type=["jpg", "jpeg", "png", "webp"], 
                                key=f"{key_prefix}_file_uploader_{product['id']}"
                            )
                            if uploaded_file_edit is not None:
                                with st.spinner("Uploading new image..."):
                                    try:
                                        files = {"file": (uploaded_file_edit.name, uploaded_file_edit.getvalue(), uploaded_file_edit.type)}
                                        upload_res = requests.post(f"{API_URL}/products/upload-image", files=files)
                                        if upload_res.status_code == 200:
                                            updated_image_url = upload_res.json().get("image_url")
                                            st.success("✅ Image uploaded successfully!")
                                        else:
                                            st.error("❌ Failed to upload image.")
                                    except Exception as e:
                                        st.error(f"❌ Upload error: {str(e)}")
                        
                        col_update, col_delete = st.columns(2)
                        with col_update:
                            if st.button("💾 Update", key=f"{key_prefix}_update_{product['id']}", use_container_width=True):
                                try:
                                    headers = {}
                                    if st.session_state.token:
                                        headers["Authorization"] = f"Bearer {st.session_state.token}"
                                    response = requests.put(
                                        f"{API_URL}/products/{product['id']}",
                                        json={
                                            "name": product['name'], 
                                            "price": new_price, 
                                            "stock": new_stock,
                                            "image_url": updated_image_url,
                                            "locality": new_locality,
                                            "low_stock_threshold": new_threshold
                                        },
                                        headers=headers
                                    )
                                    if response.status_code == 200:
                                        st.success(f"✅ Product updated!")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Error: {response.json().get('detail', 'Unknown error')}")
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
                        
                        with col_delete:
                            if st.button("🗑️ Delete", key=f"{key_prefix}_delete_{product['id']}", use_container_width=True):
                                try:
                                    headers = {}
                                    if st.session_state.token:
                                        headers["Authorization"] = f"Bearer {st.session_state.token}"
                                    response = requests.delete(
                                        f"{API_URL}/products/{product['id']}",
                                        headers=headers
                                    )
                                    if response.status_code == 200:
                                        st.success(f"✅ Product deleted!")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Error: {response.json().get('detail', 'Unknown error')}")
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
            else:
                st.info("No products found")
        else:
            st.error("❌ Could not fetch products")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# =============== LOGIN VIEWS ===============
def handle_login(username, password, expected_role):
    if username and password:
        try:
            response = requests.post(
                f"{API_URL}/users/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                user_data = response.json()
                if user_data:
                    actual_role = user_data[0].get("role", "user")
                    if actual_role != expected_role:
                        st.error(f"❌ Unauthorized: This login section is for {expected_role.upper()} accounts only.")
                        return
                    st.session_state.user_id = user_data[0].get("id")
                    st.session_state.username = user_data[0].get("name", "User")
                    st.session_state.user_role = actual_role
                    st.session_state.token = user_data[0].get("token")
                    st.success(f"✅ Welcome, {st.session_state.username}!")
                    st.balloons()
                    st.rerun()
            elif response.status_code == 401:
                st.error("❌ Incorrect password. Please try again.")
            elif response.status_code == 404:
                st.error("❌ User not found. Please check your username.")
            else:
                st.error(f"❌ Login failed: {response_detail(response)}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    else:
        st.warning("⚠️ Please enter both Username and Password")

def user_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.title("🛍️ NextGen Commerce")
        st.markdown("### 🛒 User Portal")
        st.markdown("Welcome! Please login to continue.")
        st.markdown("---")
        
        user_username = st.text_input("Username", key="user_user", placeholder="e.g. John Doe")
        user_password = st.text_input("Password", type="password", key="user_pass", placeholder="••••")
        if st.button("Login as User", key="user_btn", type="primary", use_container_width=True):
            handle_login(user_username, user_password, "user")
            
        st.markdown("---")
        st.page_link(register_page, label="📝 Don't have an account? Register here", icon="📝")
        st.page_link(driver_login_page, label="🚴 Driver Login")
        st.page_link(vendor_login_page, label="🏬 Vendor Login")
        st.page_link(manager_login_page, label="📊 Manager Login")
        st.page_link(admin_login_page, label="👨‍💼 Admin Login")

def vendor_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.title("🛍️ NextGen Commerce")
        st.markdown("### 🏬 Vendor Portal")
        st.markdown("Authenticate to manage your local neighborhood shop.")
        st.markdown("---")
        
        vendor_username = st.text_input("Username", key="vendor_user", placeholder="e.g. Ravi Vendor")
        vendor_password = st.text_input("Password", type="password", key="vendor_pass", placeholder="••••")
        if st.button("Login as Vendor", key="vendor_btn", type="primary", use_container_width=True):
            handle_login(vendor_username, vendor_password, "vendor")
            
        st.markdown("---")
        st.page_link(user_login_page, label="🛒 Go back to User Login", icon="🛒")

def manager_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.title("🛍️ NextGen Commerce")
        st.markdown("### 📊 Manager Portal")
        st.markdown("Welcome! Please login to manage the store.")
        st.markdown("---")
        
        mgr_username = st.text_input("Username", key="mgr_user", placeholder="e.g. John Doe")
        mgr_password = st.text_input("Password", type="password", key="mgr_pass", placeholder="••••")
        if st.button("Login as Manager", key="mgr_btn", type="primary", use_container_width=True):
            handle_login(mgr_username, mgr_password, "manager")
            
        st.markdown("---")
        st.page_link(user_login_page, label="🛒 Go back to User Login", icon="🛒")

def admin_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.title("🛍️ NextGen Commerce")
        st.markdown("### 👨‍💼 Admin Portal")
        st.markdown("Administrator authentication required.")
        st.markdown("---")
        
        adm_username = st.text_input("Username", key="adm_user", placeholder="e.g. John Doe")
        adm_password = st.text_input("Password", type="password", key="adm_pass", placeholder="••••")
        if st.button("Login as Admin", key="adm_btn", type="primary", use_container_width=True):
            handle_login(adm_username, adm_password, "admin")
            
        st.markdown("---")
        st.page_link(user_login_page, label="🛒 Go back to User Login", icon="🛒")

def driver_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.title("🛍️ NextGen Commerce")
        st.markdown("### 🚴 Driver Portal")
        st.markdown("Login to view assigned deliveries.")
        st.markdown("---")

        drv_username = st.text_input("Username", key="drv_user", placeholder="e.g. Ravi Driver")
        drv_password = st.text_input("Password", type="password", key="drv_pass", placeholder="driver123")
        if st.button("Login as Driver", key="drv_btn", type="primary", use_container_width=True):
            handle_login(drv_username, drv_password, "driver")

        st.markdown("---")
        st.page_link(user_login_page, label="🛒 Go back to User Login")

def register_view():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.title("🛍️ NextGen Commerce")
        st.markdown("### 📝 Create New Account")
        st.markdown("Register below to join the store.")
        st.markdown("---")
        
        new_name = st.text_input("Full Name (Username)", key="reg_user", placeholder="John Doe")
        new_email = st.text_input("Email Address", key="reg_email", placeholder="john@example.com")
        new_password = st.text_input("Password", type="password", key="reg_pass", placeholder="Enter secure password")
        
        if st.button("Register", key="reg_btn", type="primary", use_container_width=True):
            if new_name and new_email and new_password:
                try:
                    response = requests.post(
                        f"{API_URL}/users",
                        json={"name": new_name, "email": new_email, "password": new_password}
                    )
                    if response.status_code == 200:
                        st.success("✅ Account created successfully!")
                        st.balloons()
                        st.info("📌 Redirecting you to the user login page...")
                        st.switch_page(user_login_page)
                    else:
                        st.error(f"❌ Error creating account: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please fill in all fields (Name, Email, and Password)")
                
        st.markdown("---")
        st.page_link(user_login_page, label="🛒 Already have an account? User Login", icon="🛒")

# =============== HOME PAGE ===============
def home_page():
    # Top header with user details & log out
    col_hdr1, col_hdr2, col_hdr3 = st.columns([3, 1, 1])
    with col_hdr1:
        st.markdown('<div class="gradient-title">NextGen Commerce</div>', unsafe_allow_html=True)
        st.markdown('<div class="gradient-subtitle">The Scalable Neighborhood Hyperlocal Marketplace</div>', unsafe_allow_html=True)
    with col_hdr3:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.user_role = None
            st.session_state.token = None
            st.session_state.cart = []
            st.session_state.recommendations = []
            st.success("✅ Logged out successfully!")
            st.rerun()
            
    st.info(f"👤 Welcome, **{st.session_state.username}** | Role: **{st.session_state.user_role.upper()}** | User ID: {st.session_state.user_id}")

    # FLASH SALE TRIGGER BANNER
    st.markdown("""
    <div class="flash-sale-banner">
        <div>
            <span style="font-size: 1.5rem; margin-right: 10px;">⚡</span>
            <span>HYPERLOCAL FLASH SALE LIVE: Get 10% off on nearby Midtown listings!</span>
        </div>
        <span class="badge" style="background: white; color: #f43f5e; border: none;">LIMITED STOCK</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Driver View ────────────────────
    if st.session_state.user_role == "driver":
        st.subheader("🚴 Assigned Deliveries")
        if st.button("Refresh Deliveries", use_container_width=True):
            st.rerun()

        try:
            response = requests.get(f"{API_URL}/drivers/{st.session_state.user_id}/deliveries")
            if response.status_code == 200:
                deliveries = response.json()
                if deliveries:
                    grouped = {}
                    for row in deliveries:
                        grouped.setdefault(row["order_id"], []).append(row)

                    for order_id, rows in grouped.items():
                        first = rows[0]
                        with st.container(border=True):
                            st.markdown(f"### Delivery for Order #{order_id}")
                            st.markdown(f"**Customer:** {first.get('customer_name')} (ID {first.get('customer_id')})")
                            st.markdown(f"**Status:** {first.get('status')}")
                            st.markdown(f"**Location:** {first.get('current_location')}")
                            st.markdown(f"**Shipped at:** {first.get('shipped_at')}")
                            st.markdown(f"**Estimated delivery:** {first.get('estimated_delivery')}")
                            st.caption(first.get("tracking_note") or "")

                            delivery_rows = []
                            for item in rows:
                                delivery_rows.append({
                                    "Product": item.get("product_name"),
                                    "Quantity": item.get("quantity"),
                                    "Price": item.get("price"),
                                })
                            st.dataframe(pd.DataFrame(delivery_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No deliveries assigned yet.")
            else:
                st.error(f"Could not fetch deliveries: {response_detail(response)}")
        except Exception as e:
            st.error(f"Error fetching deliveries: {str(e)}")
        return

    # ── Vendor View ────────────────────
    if st.session_state.user_role == "vendor":
        tab_v_manage, tab_v_alerts = st.tabs(["📦 Inventory Management CRUD", "🔔 Operational Insights & Alerts"])
        with tab_v_manage:
            render_manage_products("vendor_dash", vendor_only=True)
            st.divider()
            render_add_product("vendor_dash", vendor_id=st.session_state.user_id)
        with tab_v_alerts:
            st.markdown("### 🚨 Pending Low-Stock Alerts")
            try:
                response = requests.get(f"{API_URL}/vendor/products?vendor_id={st.session_state.user_id}")
                if response.status_code == 200:
                    products = response.json()
                    low_stock = [p for p in products if int(p.get("stock", 0)) <= int(p.get("low_stock_threshold", 10))]
                    if low_stock:
                        st.warning(f"⚠️ You have {len(low_stock)} items low on stock!")
                        alert_df = pd.DataFrame([{
                            "Product": p["name"],
                            "Stock": p["stock"],
                            "Threshold": p["low_stock_threshold"],
                            "Locality": p.get("locality") or "N/A"
                        } for p in low_stock])
                        st.dataframe(alert_df, use_container_width=True, hide_index=True)
                    else:
                        st.success("✅ All product stock levels are healthy!")
            except Exception as e:
                st.error(f"Error checking stock alerts: {str(e)}")
        return

    # ── Normal User / Manager / Admin Views ────────────────────
    tabs = ["🛒 Hyperlocal Storefront", "💳 Checkout Cart", "📦 Order History"]
    if st.session_state.user_role == "admin":
        tabs.append("👨‍💼 Admin Console")
        tabs.append("📈 Live Analytics")
    elif st.session_state.user_role == "manager":
        tabs.append("📊 Manager Panel")

    selected_tabs = st.tabs(tabs)

    # STOREFRONT TAB
    with selected_tabs[0]:
        st.subheader("📍 Browse Local Products")
        
        # Real-time polling / Autorefresh toggler
        col_ref1, col_ref2 = st.columns([6, 2])
        with col_ref2:
            auto_refresh = st.checkbox("🔄 Enable Auto-Refresh Stock (Polling)", value=False)
            if auto_refresh:
                st.caption("Auto-refreshing stock status every 5 seconds...")
                time.sleep(5)
                st.rerun()

        # Categorization, Locality & Search Bar filters
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            search_query = st.text_input("Search (Search bar & AI query)", placeholder="e.g. cheap keyboard under 50, organic fruits")
        with col2:
            # Locality filter
            try:
                loc_res = requests.get(f"{API_URL}/products/localities")
                localities = ["All Localities"] + loc_res.json() if loc_res.status_code == 200 else ["All Localities"]
            except Exception:
                localities = ["All Localities"]
            selected_locality = st.selectbox("📍 Filter by Locality / Area", localities)
        with col3:
            selected_sort = st.selectbox(
                "Sort Products By",
                ["AI best match", "Name A-Z", "Price low-high", "Price high-low", "Most stock"]
            )

        # Category filter pills
        categories_pills = ["All", "Electronics", "Furniture", "Cosmetics", "Other"]
        pill_cols = st.columns(len(categories_pills))
        for i, cat in enumerate(categories_pills):
            with pill_cols[i]:
                if st.button(cat, key=f"pill_{cat}", use_container_width=True, type="primary" if st.session_state.active_pill == cat else "secondary"):
                    st.session_state.active_pill = cat
                    st.rerun()

        # Price range slider
        price_range = st.slider("💰 Price Filter ($)", min_value=0.0, max_value=500.0, value=(0.0, 500.0), step=5.0)

        # Fetch products
        grouped_products = None
        with st.spinner("Syncing catalog inventory..."):
            try:
                sort_map = {
                    "AI best match": "ai",
                    "Name A-Z": "name_asc",
                    "Price low-high": "price_low",
                    "Price high-low": "price_high",
                    "Most stock": "stock_high",
                }
                payload = {
                    "query": search_query,
                    "category": None if st.session_state.active_pill == "All" else st.session_state.active_pill,
                    "sort_by": sort_map[selected_sort],
                    "locality": None if selected_locality == "All Localities" else selected_locality
                }
                response = requests.post(f"{API_URL}/api/products/filter", json=payload, timeout=20)
                if response.status_code == 200:
                    filter_payload = response.json()
                    grouped_products = filter_payload.get("grouped", {})
                else:
                    st.error(f"Catalog sync failed: {response_detail(response)}")
            except Exception as e:
                st.error(f"Connection failure: {str(e)}")

        if grouped_products:
            rendered_any = False
            active_cats = [st.session_state.active_pill] if st.session_state.active_pill != "All" else ["Electronics", "Furniture", "Cosmetics", "Other"]
            
            for category in active_cats:
                products = grouped_products.get(category, [])
                # Filter by price range locally
                products = [p for p in products if price_range[0] <= float(p.get("price", 0)) <= price_range[1]]
                
                if not products:
                    continue

                rendered_any = True
                st.markdown(f"## {category}")
                cols = st.columns(3)
                for idx, product in enumerate(products):
                    with cols[idx % 3]:
                        render_shop_product_card(product, f"{category.lower()}_{idx}")

            if not rendered_any:
                st.info("No products match your active filters.")

    # CART TAB
    with selected_tabs[1]:
        st.subheader("🛒 Shopping Cart")
        if st.session_state.cart:
            fetch_cart_ai_summary()
            summary = st.session_state.cart_ai_summary or fallback_cart_summary()
            st.info(summary.get("reply", fallback_cart_summary()["reply"]))
            
            total_price = 0
            col_h1, col_h2, col_h3, col_h4 = st.columns([4, 2, 2, 1])
            with col_h1:
                st.markdown("**Product**")
            with col_h2:
                st.markdown("**Quantity**")
            with col_h3:
                st.markdown("**Total**")
            with col_h4:
                st.markdown("**Action**")
            
            to_remove = None
            for idx, item in enumerate(st.session_state.cart):
                item_total = item['price'] * item['quantity']
                total_price += item_total
                
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
                    with col1:
                        st.markdown(f"**{item['name']}**")
                        st.caption(f"Price: ${item['price']:.2f}")
                    with col2:
                        new_qty = st.number_input(
                            "Quantity",
                            min_value=1,
                            value=item['quantity'],
                            key=f"cart_qty_{item['product_id']}_{idx}",
                            label_visibility="collapsed"
                        )
                        if new_qty != item['quantity']:
                            st.session_state.cart[idx]['quantity'] = new_qty
                            st.rerun()
                    with col3:
                        st.markdown(f"**${item_total:.2f}**")
                    with col4:
                        if st.button("🗑️", key=f"cart_del_{item['product_id']}_{idx}", use_container_width=True):
                            to_remove = idx
            
            if to_remove is not None:
                removed_item = st.session_state.cart.pop(to_remove)
                st.success(f"Removed {removed_item['name']} from cart!")
                st.rerun()
            
            st.divider()
            col_tot1, col_tot2 = st.columns([2, 1])
            with col_tot1:
                st.markdown(f"### Total: ${total_price:.2f}")
            with col_tot2:
                if st.button("Clear Cart", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()
            
            st.divider()
            # Checkout phase with stock reservation guard
            if st.button("Checkout & Reserve Stock", use_container_width=True, type="primary"):
                try:
                    order_payload = {
                        "user_id": st.session_state.user_id,
                        "items": [
                            {"product_id": item['product_id'], "quantity": item['quantity']}
                            for item in st.session_state.cart
                        ]
                    }
                    response = requests.post(f"{API_URL}/orders", json=order_payload)
                    if response.status_code == 200:
                        st.success("✅ Order placed successfully! Stock reserved.")
                        st.session_state.cart = []
                        st.rerun()
                    elif response.status_code == 409:
                        st.error(f"❌ Transaction conflict: {response.json().get('detail')}")
                    else:
                        st.error("❌ Checkout failed. Please review stock availability.")
                except Exception as e:
                    st.error(f"❌ Error during checkout: {str(e)}")
        else:
            st.info("💭 Your cart is empty. Start shopping! 🛍️")

    # ORDERS TAB
    with selected_tabs[2]:
        st.subheader("📦 Your Orders")
        if st.button("🔄 Refresh Orders"):
            st.rerun()
        
        try:
            response = requests.get(f"{API_URL}/users/{st.session_state.user_id}")
            if response.status_code == 200:
                orders = response.json()
                if orders:
                    orders_dict = {}
                    for item in orders:
                        order_id = item.get('order_id')
                        if order_id is None:
                            continue
                        orders_dict.setdefault(order_id, []).append(item)
                    
                    if orders_dict:
                        for order_id, items in orders_dict.items():
                            with st.container(border=True):
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.markdown(f"### Order #{order_id}")
                                with col2:
                                    st.markdown(f"**Items:** {len(items)}")
                                first_item = items[0]
                                if first_item.get("delivery_status"):
                                    st.caption(
                                        f"Delivery: {first_item.get('delivery_status')} | "
                                        f"Driver: {first_item.get('driver_name') or 'Not assigned'} | "
                                        f"Location: {first_item.get('current_location') or 'Updating'} | "
                                        f"ETA: {first_item.get('estimated_delivery') or 'Pending'}"
                                    )
                                
                                order_data = []
                                total = 0
                                for item in items:
                                    item_total = item['price'] * item['quantity']
                                    total += item_total
                                    order_data.append({
                                        "Product": item['product_name'],
                                        "Price": f"${item['price']:.2f}",
                                        "Quantity": item['quantity'],
                                        "Total": f"${item_total:.2f}"
                                    })
                                
                                df = pd.DataFrame(order_data)
                                st.dataframe(df, use_container_width=True, hide_index=True)
                                st.markdown(f"**Order Total:** ${total:.2f}")
                    else:
                        st.info("📦 No orders found.")
                else:
                    st.info("📦 No orders found.")
            else:
                st.error("❌ Could not retrieve order history.")
        except Exception as e:
            st.error(f"Error fetching orders: {str(e)}")

    # ── Admin Panel Tab ────────────────────
    if st.session_state.user_role == "admin":
        with selected_tabs[3]:
            st.subheader("👨‍💼 Admin Console")
            admin_sec = st.radio("Select Section", ["👥 Manage Users", "🔍 View All Orders", "➕ Add Product", "📝 Manage Products"])
            
            if admin_sec == "👥 Manage Users":
                st.markdown("### All Users")
                try:
                    response = requests.get(f"{API_URL}/users")
                    if response.status_code == 200:
                        users = response.json()
                        if users:
                            df = pd.DataFrame([{
                                "ID": u.get('id'),
                                "Name": u.get('name'),
                                "Email": u.get('email'),
                                "Role": u.get('role', 'user')
                            } for u in users])
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            
                            st.divider()
                            st.markdown("### Change User Role")
                            col_role1, col_role2, col_role3 = st.columns(3)
                            with col_role1:
                                user_id_change = st.number_input("Select User ID", min_value=1, step=1)
                            with col_role2:
                                new_role = st.selectbox("New Role", ["user", "manager", "admin", "vendor", "driver"])
                            with col_role3:
                                if st.button("Update Role", use_container_width=True, type="primary"):
                                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                                    res = requests.put(f"{API_URL}/users/{user_id_change}/role", json={"role": new_role}, headers=headers)
                                    if res.status_code == 200:
                                        st.success("Role updated!")
                                        st.rerun()
                                    else:
                                        st.error(res.json().get("detail", "Error changing role"))
                        else:
                            st.info("No users found")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            elif admin_sec == "🔍 View All Orders":
                st.markdown("### All Store Orders")
                try:
                    response = requests.get(f"{API_URL}/users")
                    if response.status_code == 200:
                        users = response.json()
                        all_orders = []
                        for user in users:
                            try:
                                o_res = requests.get(f"{API_URL}/users/{user['id']}")
                                if o_res.status_code == 200:
                                    for o in o_res.json():
                                        if o.get('order_id'):
                                            all_orders.append({
                                                "User": o.get('name'),
                                                "User ID": o.get('id'),
                                                "Order ID": o.get('order_id'),
                                                "Product": o.get('product_name'),
                                                "Price": f"${o.get('price', 0):.2f}",
                                                "Quantity": o.get('quantity'),
                                            })
                            except Exception:
                                pass
                        if all_orders:
                            st.dataframe(pd.DataFrame(all_orders), use_container_width=True, hide_index=True)
                        else:
                            st.info("No orders found.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            elif admin_sec == "➕ Add Product":
                render_add_product("admin")
            elif admin_sec == "📝 Manage Products":
                render_manage_products("admin")

        # ── Live Analytics Tab (Admin only) ────────────────────
        with selected_tabs[4]:
            st.subheader("📈 Real-Time Store Performance & Analytics")
            if st.button("🔄 Refresh Analytics"):
                st.rerun()
                
            try:
                res = requests.get(f"{API_URL}/admin/analytics")
                if res.status_code == 200:
                    data = res.json()
                    
                    # Metric cards
                    met1, met2, met3, met4 = st.columns(4)
                    with met1:
                        st.metric("Gross Revenue", f"${data['gross_revenue']:.2f}")
                    with met2:
                        st.metric("Total Orders", data["total_orders"])
                    with met3:
                        st.metric("Active Orders", data["active_orders"])
                    with met4:
                        st.metric("Completed Deliveries", data["completed_orders"])
                        
                    st.divider()
                    
                    # Pipelines & Sales Charts
                    col_ch1, col_ch2 = st.columns(2)
                    with col_ch1:
                        st.markdown("### 🛒 Order Fulfillment Pipeline")
                        pipeline_df = pd.DataFrame(data["pipeline"])
                        if not pipeline_df.empty:
                            st.bar_chart(pipeline_df, x="status", y="count", color="#ec4899")
                        else:
                            st.info("No pipeline data yet.")
                            
                    with col_ch2:
                        st.markdown("### 🏆 Top 10 Best Sellers")
                        top_df = pd.DataFrame(data["top_products"])
                        if not top_df.empty:
                            st.bar_chart(top_df, x="name", y="revenue", color="#8b5cf6")
                        else:
                            st.info("No sales data yet.")
                            
                    st.divider()
                    st.markdown("### 📅 Daily Sales Trend (Last 30 Days)")
                    daily_df = pd.DataFrame(data["daily_revenue"])
                    if not daily_df.empty:
                        st.line_chart(daily_df, x="day", y="revenue")
                    else:
                        st.info("No daily sales trend data available.")
                        
                else:
                    st.error("Could not fetch admin analytics.")
            except Exception as e:
                st.error(f"Error building analytics view: {str(e)}")

    # ── Manager Panel Tab ────────────────────
    if st.session_state.user_role == "manager":
        with selected_tabs[3]:
            st.subheader("📊 Manager Panel")
            manager_section = st.radio("Select Section", ["➕ Add Product", "📝 Manage Products", "👥 View Users & Managers"], key="manager_section")
            if manager_section == "➕ Add Product":
                render_add_product("manager")
            elif manager_section == "📝 Manage Products":
                render_manage_products("manager")
            elif manager_section == "👥 View Users & Managers":
                st.markdown("### Registered Users & Managers")
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    response = requests.get(f"{API_URL}/manager/users", headers=headers)
                    if response.status_code == 200:
                        users = response.json()
                        if users:
                            df = pd.DataFrame([{
                                "ID": u.get('id'),
                                "Name": u.get('name'),
                                "Email": u.get('email'),
                                "Role": u.get('role', 'user')
                            } for u in users])
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No users or managers found")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# =============== MAIN APP ROUTING ===============
user_login_page = st.Page(user_login, title="User Login", url_path="user", default=True)
manager_login_page = st.Page(manager_login, title="Manager Login", url_path="manager")
admin_login_page = st.Page(admin_login, title="Admin Login", url_path="admin")
driver_login_page = st.Page(driver_login, title="Driver Login", url_path="driver")
vendor_login_page = st.Page(vendor_login, title="Vendor Login", url_path="vendor")
register_page = st.Page(register_view, title="Register", url_path="register")
home_page_obj = st.Page(home_page, title="Home", url_path="home", default=True)

if st.session_state.user_id is None:
    pg = st.navigation([user_login_page, manager_login_page, admin_login_page, driver_login_page, vendor_login_page, register_page], position="hidden")
else:
    pg = st.navigation([home_page_obj], position="hidden")

pg.run()

# =============== FLOATING CHAT WIDGET ===============
import streamlit.components.v1 as components

if st.session_state.user_id is not None:
    chat_user_id = st.session_state.user_id
    chat_cart_items = json.dumps([
        {
            "product_id": item["product_id"],
            "name": item["name"],
            "price": float(item["price"]),
            "quantity": int(item["quantity"]),
        }
        for item in st.session_state.cart
    ])
    components.html(
        f"""
        <script>
        (function() {{
            var parentDoc = window.parent.document;
            var parentWin = window.parent;
            var chatUserId = {chat_user_id};
            var chatCartItems = {chat_cart_items};
            var appOrigin = (
                parentWin.location &&
                parentWin.location.origin &&
                parentWin.location.origin !== "null"
            ) ? parentWin.location.origin : window.location.origin;
            var chatUrl = appOrigin + "/chat";
            
            if (!parentWin.chatWidgetState) {{
                parentWin.chatWidgetState = {{
                    isOpen: false,
                    history: [],
                    messagesHtml: '<div class="message bot">Hello! I\\'m your shopping assistant. How can I help you find products or orders today?</div>',
                    inputText: ""
                }};
            }}
            
            var oldWidget = parentDoc.getElementById("floating-chat-widget");
            if (oldWidget) {{
                var oldInput = parentDoc.getElementById("chat-message-input");
                if (oldInput) {{
                    parentWin.chatWidgetState.inputText = oldInput.value;
                }}
                oldWidget.remove();
            }}
            
            var oldStyle = parentDoc.getElementById("floating-chat-widget-style");
            if (oldStyle) {{
                oldStyle.remove();
            }}
            
            var style = parentDoc.createElement("style");
            style.id = "floating-chat-widget-style";
            style.innerHTML = `
                .chat-btn {{
                    position: fixed;
                    bottom: 25px;
                    right: 25px;
                    width: 60px;
                    height: 60px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 28px;
                    cursor: pointer;
                    z-index: 999999;
                    transition: all 0.3s ease;
                }}
                .chat-btn:hover {{
                    transform: scale(1.1) rotate(5deg);
                }}
                .chat-window {{
                    position: fixed;
                    bottom: 95px;
                    right: 25px;
                    width: 370px;
                    height: 500px;
                    border-radius: 16px;
                    background: rgba(25, 20, 45, 0.95);
                    backdrop-filter: blur(10px);
                    -webkit-backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
                    display: flex;
                    flex-direction: column;
                    z-index: 999999;
                    overflow: hidden;
                    font-family: 'Inter', -apple-system, sans-serif;
                    transition: all 0.3s cubic-bezier(0.1, 0.8, 0.3, 1);
                }}
                .chat-header {{
                    background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%);
                    color: white;
                    padding: 15px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-weight: bold;
                }}
                .chat-header .title {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 16px;
                }}
                .chat-header .close-btn {{
                    cursor: pointer;
                    font-size: 20px;
                    font-weight: bold;
                    opacity: 0.8;
                    transition: opacity 0.2s;
                }}
                .chat-header .close-btn:hover {{
                    opacity: 1;
                }}
                .chat-messages {{
                    flex-grow: 1;
                    padding: 15px;
                    overflow-y: auto;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }}
                .message {{
                    max-width: 80%;
                    padding: 10px 14px;
                    border-radius: 12px;
                    font-size: 14px;
                    line-height: 1.4;
                    word-wrap: break-word;
                }}
                .message.user {{
                    align-self: flex-end;
                    background-color: #ec4899;
                    color: white;
                    border-bottom-right-radius: 2px;
                }}
                .message.bot {{
                    align-self: flex-start;
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #e2e8f0;
                    border-bottom-left-radius: 2px;
                }}
                .chat-input-area {{
                    padding: 12px;
                    background: rgba(15, 14, 30, 0.95);
                    border-top: 1px solid rgba(255,255,255,0.05);
                    display: flex;
                    gap: 8px;
                }}
                .chat-input {{
                    flex-grow: 1;
                    border: 1px solid rgba(255,255,255,0.2);
                    background: rgba(255,255,255,0.05);
                    color: white;
                    border-radius: 20px;
                    padding: 8px 16px;
                    font-size: 14px;
                    outline: none;
                    transition: border 0.2s;
                }}
                .chat-input:focus {{
                    border-color: #a855f7;
                }}
                .send-btn {{
                    background: #a855f7;
                    border: none;
                    color: white;
                    border-radius: 50%;
                    width: 36px;
                    height: 36px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    transition: background 0.2s;
                }}
                .send-btn:hover {{
                    background: #8b5cf6;
                }}
                .typing-indicator {{
                    display: flex;
                    gap: 4px;
                    padding: 6px 10px;
                    align-self: flex-start;
                    background: rgba(255,255,255,0.05);
                    border-radius: 10px;
                }}
                .typing-dot {{
                    width: 6px;
                    height: 6px;
                    background: #a855f7;
                    border-radius: 50%;
                    animation: bounce 1.3s infinite;
                }}
                .typing-dot:nth-child(2) {{ animation-delay: 0.15s; }}
                .typing-dot:nth-child(3) {{ animation-delay: 0.3s; }}
                @keyframes bounce {{
                    0%, 60%, 100% {{ transform: translateY(0); }}
                    30% {{ transform: translateY(-4px); }}
                }}
            `;
            parentDoc.head.appendChild(style);
            
            var widgetContainer = parentDoc.createElement("div");
            widgetContainer.id = "floating-chat-widget";
            widgetContainer.innerHTML = `
                <div class="chat-btn" id="chat-toggle-btn">💬</div>
                <div class="chat-window" id="chat-widget-window">
                    <div class="chat-header">
                        <div class="title">✨ Shopping Assistant</div>
                        <div class="close-btn" id="chat-close-btn">&times;</div>
                    </div>
                    <div class="chat-messages" id="chat-messages-container"></div>
                    <div class="chat-input-area">
                        <input type="text" class="chat-input" id="chat-message-input" placeholder="Type a message..." autocomplete="off">
                        <button class="send-btn" id="chat-send-btn">&#10148;</button>
                    </div>
                </div>
            `;
            parentDoc.body.appendChild(widgetContainer);
            
            var btn = parentDoc.getElementById("chat-toggle-btn");
            var windowEl = parentDoc.getElementById("chat-widget-window");
            var closeBtn = parentDoc.getElementById("chat-close-btn");
            var messagesContainer = parentDoc.getElementById("chat-messages-container");
            var inputEl = parentDoc.getElementById("chat-message-input");
            var sendBtn = parentDoc.getElementById("chat-send-btn");
            
            windowEl.style.display = parentWin.chatWidgetState.isOpen ? "flex" : "none";
            messagesContainer.innerHTML = parentWin.chatWidgetState.messagesHtml;
            inputEl.value = parentWin.chatWidgetState.inputText;
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            btn.onclick = function() {{
                if (windowEl.style.display === "none" || windowEl.style.display === "") {{
                    windowEl.style.display = "flex";
                    parentWin.chatWidgetState.isOpen = true;
                    inputEl.focus();
                }} else {{
                    windowEl.style.display = "none";
                    parentWin.chatWidgetState.isOpen = false;
                }}
            }};
            
            closeBtn.onclick = function() {{
                windowEl.style.display = "none";
                parentWin.chatWidgetState.isOpen = false;
            }};
            
            function sendMessage() {{
                var text = inputEl.value.trim();
                if (!text) return;
                
                appendMessage("user", text);
                inputEl.value = "";
                parentWin.chatWidgetState.inputText = "";
                
                var indicator = showTypingIndicator();
                
                fetch(chatUrl, {{
                    method: "POST",
                    headers: {{
                        "Content-Type": "application/json"
                    }},
                    body: JSON.stringify({{
                        message: text,
                        history: parentWin.chatWidgetState.history,
                        user_id: chatUserId,
                        cart_items: chatCartItems
                    }})
                }})
                .then(function(res) {{
                    return res.text().then(function(text) {{
                        try {{
                            return JSON.parse(text);
                        }} catch (err) {{
                            throw new Error("Chat endpoint returned non-JSON response: " + text.slice(0, 80));
                        }}
                    }});
                }})
                .then(function(data) {{
                    indicator.remove();
                    if (data && data.reply) {{
                        appendMessage("bot", data.reply);
                        parentWin.chatWidgetState.history.push({{role: "user", content: text}});
                        parentWin.chatWidgetState.history.push({{role: "assistant", content: data.reply}});
                    }} else {{
                        appendMessage("bot", "Sorry, I encountered an issue processing your request.");
                    }}
                }})
                .catch(function(err) {{
                    indicator.remove();
                    appendMessage("bot", "Could not reach the support server. Please try again later.");
                    console.error(err);
                }});
            }}
            
            sendBtn.onclick = sendMessage;
            inputEl.onkeypress = function(e) {{
                if (e.key === "Enter") {{
                    sendMessage();
                }}
            }};
            
            function appendMessage(sender, text) {{
                var msg = parentDoc.createElement("div");
                msg.className = "message " + sender;
                msg.innerText = text;
                messagesContainer.appendChild(msg);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                
                parentWin.chatWidgetState.messagesHtml = messagesContainer.innerHTML;
            }}
            
            function showTypingIndicator() {{
                var indicator = parentDoc.createElement("div");
                indicator.className = "typing-indicator";
                indicator.innerHTML = `
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                `;
                messagesContainer.appendChild(indicator);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                return indicator;
            }}
        }})();
        </script>
        """,
        height=0,
        width=0
    )
else:
    components.html(
        """
        <script>
        (function() {
            var parentDoc = window.parent.document;
            var oldWidget = parentDoc.getElementById("floating-chat-widget");
            if (oldWidget) {
                oldWidget.remove();
            }
            var oldStyle = parentDoc.getElementById("floating-chat-widget-style");
            if (oldStyle) {
                oldStyle.remove();
            }
            if (window.parent.chatWidgetState) {
                window.parent.chatWidgetState = null;
            }
        })();
        </script>
        """,
        height=0,
        width=0
    )
