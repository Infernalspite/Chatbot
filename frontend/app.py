# pyrefly: ignore [missing-import]
import streamlit as st
import json
import os
import requests
import pandas as pd
from datetime import datetime

# Configure page
st.set_page_config(page_title="Shopping Store", layout="wide")

# Backend API URL
API_URL = os.getenv("API_URL", "http://localhost:8000")


def apply_app_theme():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

            :root {
                --shop-ink: #16202a;
                --shop-muted: #64748b;
                --shop-line: rgba(15, 23, 42, 0.08);
                --shop-panel: rgba(255, 255, 255, 0.94);
                --shop-accent: #0f766e;
                --shop-accent-2: #2563eb;
                --shop-warm: #f59e0b;
                --shop-danger: #dc2626;
            }

            html, body, [class*="css"], .stApp {
                font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                color: var(--shop-ink);
            }

            .stApp {
                background:
                    radial-gradient(circle at 10% 20%, rgba(37, 99, 235, 0.08), transparent 40rem),
                    radial-gradient(circle at 90% 10%, rgba(15, 118, 110, 0.10), transparent 35rem),
                    linear-gradient(180deg, #f8fafc 0%, #f1f5f9 50%, #f8fafc 100%);
            }

            [data-testid="stHeader"] {
                background: rgba(248, 250, 252, 0.72);
                backdrop-filter: blur(14px);
            }

            .block-container {
                max-width: 1220px;
                padding-top: 2rem;
                padding-bottom: 4rem;
            }

            h1, h2, h3, h4, h5, h6 {
                letter-spacing: -0.02em;
                color: var(--shop-ink);
                font-weight: 700;
            }

            p, label, .stMarkdown, [data-testid="stCaptionContainer"] {
                color: var(--shop-ink);
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                border: 1px solid var(--shop-line);
                border-radius: 12px;
                background: var(--shop-panel);
                box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
                transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.22s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.22s ease;
            }

            div[data-testid="stVerticalBlockBorderWrapper"]:hover {
                transform: translateY(-2px);
                box-shadow: 0 20px 40px rgba(15, 23, 42, 0.08);
                border-color: rgba(15, 118, 110, 0.22);
            }

            div[data-testid="stAlert"] {
                border-radius: 10px;
                border: 1px solid rgba(15, 118, 110, 0.18);
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 12px;
                border-bottom: 2px solid var(--shop-line);
                padding: 4px 0;
            }

            .stTabs [data-baseweb="tab"] {
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: 600;
                color: var(--shop-muted);
                transition: all 0.2s ease;
                border: none !important;
            }

            .stTabs [data-baseweb="tab"]:hover {
                color: var(--shop-accent-2);
                background: rgba(37, 99, 235, 0.05);
            }

            .stTabs [aria-selected="true"] {
                color: var(--shop-accent) !important;
                background: rgba(15, 118, 110, 0.08) !important;
                font-weight: 700;
            }

            .stButton > button {
                border-radius: 8px;
                border: 1px solid rgba(15, 23, 42, 0.12);
                font-weight: 600;
                background-color: white;
                color: var(--shop-ink);
                padding: 0.5rem 1rem;
                transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            }

            .stButton > button:hover {
                transform: translateY(-1px);
                border-color: var(--shop-accent);
                color: var(--shop-accent);
                box-shadow: 0 4px 12px rgba(15, 118, 110, 0.08);
            }

            .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, var(--shop-accent) 0%, var(--shop-accent-2) 100%);
                border: none;
                color: white !important;
            }

            .stButton > button[kind="primary"]:hover {
                color: white !important;
                box-shadow: 0 6px 18px rgba(37, 99, 235, 0.25);
                filter: brightness(1.05);
            }

            .stTextInput input,
            .stNumberInput input,
            .stSelectbox div[data-baseweb="select"] > div {
                border-radius: 8px;
                border-color: rgba(15, 23, 42, 0.12);
                background: rgba(255, 255, 255, 0.98);
                font-family: 'Outfit', sans-serif;
            }

            .shop-hero {
                border: 1px solid var(--shop-line);
                border-radius: 14px;
                background:
                    linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(37, 99, 235, 0.10)),
                    rgba(255,255,255,0.72);
                padding: 22px 24px;
                margin-bottom: 24px;
                box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
            }

            .shop-hero h1 {
                margin: 0;
                font-size: 2.2rem;
                letter-spacing: -0.03em;
            }

            .shop-hero p {
                margin: 8px 0 0 0;
                color: var(--shop-muted);
                font-size: 1.05rem;
            }

            .category-header {
                font-size: 1.4rem;
                font-weight: 800;
                border-bottom: 2px solid var(--shop-accent);
                padding-bottom: 0.3rem;
                margin-top: 1.8rem;
                margin-bottom: 1.2rem;
                display: flex;
                align-items: center;
                gap: 8px;
                color: var(--shop-ink);
            }

            .product-title {
                font-size: 1.12rem;
                font-weight: 800;
                min-height: 2.6rem;
                margin: 0.45rem 0 0.2rem;
                letter-spacing: -0.01em;
            }

            .product-price {
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                padding: 5px 12px;
                background: rgba(37, 99, 235, 0.08);
                color: #2563eb;
                font-weight: 800;
                margin-bottom: 0.35rem;
                font-size: 0.95rem;
            }

            .stock-badge {
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 0.82rem;
                font-weight: 700;
                margin: 0.25rem 0 0.65rem;
            }

            .stock-good {
                background: rgba(15, 118, 110, 0.10);
                color: #0f766e;
            }

            .stock-low {
                background: rgba(245, 158, 11, 0.12);
                color: #b45309;
            }

            .stock-out {
                background: rgba(220, 38, 38, 0.08);
                color: #b91c1c;
            }

            .section-label {
                color: var(--shop-muted);
                font-size: 0.86rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                margin-bottom: -0.2rem;
            }

            @media (max-width: 760px) {
                .block-container {
                    padding-left: 1rem;
                    padding-right: 1rem;
                }

                .shop-hero h1 {
                    font-size: 1.55rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_app_theme()

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
if "recommendations" not in st.session_state:       # ← RECOMMENDATION ENGINE
    st.session_state.recommendations = []            # ← RECOMMENDATION ENGINE

if "recommendation_source_id" not in st.session_state:
    st.session_state.recommendation_source_id = None
if "cart_ai_summary" not in st.session_state:
    st.session_state.cart_ai_summary = None
if "cart_ai_signature" not in st.session_state:
    st.session_state.cart_ai_signature = None


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
                    "https://images.unsplash.com/photo-1531403009284"
                    "-440f080d1e12?w=500&auto=format&fit=crop&q=80"
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

        stock = product['stock']
        if stock > 10:
            st.markdown(f"🟢 **Stock:** {stock} units")
        elif 0 < stock <= 10:
            st.markdown(f"🟡 **Stock:** Low Stock ({stock} left!)")
        else:
            st.markdown("🔴 **Stock:** Out of Stock")

        qty = st.number_input(
            "Quantity",
            min_value=1,
            max_value=max(1, product['stock']),
            value=1,
            disabled=product['stock'] <= 0,
            key=f"{key_prefix}_qty_{product['id']}"
        )

        if st.button(
            "Add to Cart",
            key=f"{key_prefix}_add_{product['id']}",
            use_container_width=True,
            disabled=product['stock'] <= 0,
        ):
            add_item_to_cart(product, qty)
            st.success(f"Added {qty} to cart!")

        render_recommendations_for(product["id"], key_prefix)


# =============== PRODUCT MANAGEMENT HELPERS ===============
def render_add_product(key_prefix: str):
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
        image_source = st.selectbox(
            "Product Image Option", 
            ["Auto-suggest beautiful stock image based on name", "Provide Image URL", "Upload Image from computer", "None"],
            key=f"{key_prefix}_add_img_source"
        )
    
    # Image source inputs
    final_image_url = None
    
    if image_source == "Provide Image URL":
        final_image_url = st.text_input("Enter Web Image URL", placeholder="https://example.com/image.jpg", key=f"{key_prefix}_add_img_url")
    
    elif image_source == "Upload Image from computer":
        uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "webp"], key=f"{key_prefix}_add_uploader")
        if uploaded_file is not None:
            # Upload file to the backend
            with st.spinner("Uploading image..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    upload_res = requests.post(f"{API_URL}/products/upload-image", files=files)
                    if upload_res.status_code == 200:
                        final_image_url = upload_res.json().get("image_url")
                        st.success("✅ Image uploaded successfully!")
                        st.image(final_image_url, width=150)
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
                    "image_url": final_image_url
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


def render_manage_products(key_prefix: str):
    st.markdown("### All Products")
    
    if st.button("🔄 Refresh Products", key=f"{key_prefix}_refresh_products"):
        st.rerun()
    
    try:
        response = requests.get(f"{API_URL}/products")
        if response.status_code == 200:
            products = response.json()
            
            if products:
                # Display products in expandable sections
                for product in products:
                    with st.expander(f"**{product['name']}** - ${product['price']:.2f} | Stock: {product['stock']}"):
                        # Show current image
                        if product.get('image_url'):
                            st.image(product.get('image_url'), width=150)
                        
                        col1, col2, col3 = st.columns([2, 2, 2])
                        
                        with col1:
                            new_price = st.number_input(
                                "Price ($)",
                                min_value=0.0,
                                value=product['price'],
                                step=0.01,
                                key=f"{key_prefix}_price_{product['id']}"
                            )
                        
                        with col2:
                            new_stock = st.number_input(
                                "Stock",
                                min_value=0,
                                value=product['stock'],
                                step=1,
                                key=f"{key_prefix}_stock_{product['id']}"
                            )
                            
                        with col3:
                            # Image source option
                            image_update_source = st.selectbox(
                                "Update Image Option",
                                ["Keep Current Image", "Provide Image URL", "Upload Image from computer", "None/Remove Image"],
                                key=f"{key_prefix}_img_src_{product['id']}"
                            )
                        
                        # Handle updating the image URL
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
                                            "image_url": updated_image_url
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
    col1, col2, col3 = st.columns([1, 2.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; margin-bottom: 0.2rem;'>🛍️ Shopping Store</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: var(--shop-muted); margin-bottom: 1.5rem;'>🛒 User Portal &bull; Welcome back!</p>", unsafe_allow_html=True)
            
            user_username = st.text_input("Username", key="user_user", placeholder="e.g. John Doe")
            user_password = st.text_input("Password", type="password", key="user_pass", placeholder="••••")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("Login as User", key="user_btn", type="primary", use_container_width=True):
                handle_login(user_username, user_password, "user")
                
            st.markdown("<div style='margin: 1.2rem 0; border-top: 1px solid var(--shop-line);'></div>", unsafe_allow_html=True)
            st.page_link(register_page, label="📝 Create an Account", use_container_width=True)
            
            col_links = st.columns(3)
            with col_links[0]:
                st.page_link(driver_login_page, label="🚚 Driver", use_container_width=True)
            with col_links[1]:
                st.page_link(manager_login_page, label="📊 Manager", use_container_width=True)
            with col_links[2]:
                st.page_link(admin_login_page, label="👨‍💼 Admin", use_container_width=True)

def manager_login():
    col1, col2, col3 = st.columns([1, 2.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; margin-bottom: 0.2rem;'>🛍️ Shopping Store</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: var(--shop-muted); margin-bottom: 1.5rem;'>📊 Manager Portal &bull; Welcome back!</p>", unsafe_allow_html=True)
            
            mgr_username = st.text_input("Username", key="mgr_user", placeholder="e.g. John Doe")
            mgr_password = st.text_input("Password", type="password", key="mgr_pass", placeholder="••••")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("Login as Manager", key="mgr_btn", type="primary", use_container_width=True):
                handle_login(mgr_username, mgr_password, "manager")
                
            st.markdown("<div style='margin: 1.2rem 0; border-top: 1px solid var(--shop-line);'></div>", unsafe_allow_html=True)
            st.page_link(user_login_page, label="🛒 Back to User Login", use_container_width=True)

def admin_login():
    col1, col2, col3 = st.columns([1, 2.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; margin-bottom: 0.2rem;'>🛍️ Shopping Store</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: var(--shop-muted); margin-bottom: 1.5rem;'>👨‍💼 Admin Portal &bull; Auth required</p>", unsafe_allow_html=True)
            
            adm_username = st.text_input("Username", key="adm_user", placeholder="e.g. John Doe")
            adm_password = st.text_input("Password", type="password", key="adm_pass", placeholder="••••")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("Login as Admin", key="adm_btn", type="primary", use_container_width=True):
                handle_login(adm_username, adm_password, "admin")
                
            st.markdown("<div style='margin: 1.2rem 0; border-top: 1px solid var(--shop-line);'></div>", unsafe_allow_html=True)
            st.page_link(user_login_page, label="🛒 Back to User Login", use_container_width=True)


def driver_login():
    col1, col2, col3 = st.columns([1, 2.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; margin-bottom: 0.2rem;'>Shopping Store</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: var(--shop-muted); margin-bottom: 1.5rem;'>🚚 Driver Portal &bull; Deliveries lookup</p>", unsafe_allow_html=True)

            drv_username = st.text_input("Username", key="drv_user", placeholder="e.g. Ravi Driver")
            drv_password = st.text_input("Password", type="password", key="drv_pass", placeholder="driver123")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("Login as Driver", key="drv_btn", type="primary", use_container_width=True):
                handle_login(drv_username, drv_password, "driver")

            st.markdown("<div style='margin: 1.2rem 0; border-top: 1px solid var(--shop-line);'></div>", unsafe_allow_html=True)
            st.page_link(user_login_page, label="🛒 Back to User Login", use_container_width=True)

def register_view():
    col1, col2, col3 = st.columns([1, 2.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; margin-bottom: 0.2rem;'>🛍️ Shopping Store</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: var(--shop-muted); margin-bottom: 1.5rem;'>📝 Create New Account</p>", unsafe_allow_html=True)
            
            new_name = st.text_input("Full Name (Username)", key="reg_user", placeholder="John Doe")
            new_email = st.text_input("Email Address", key="reg_email", placeholder="john@example.com")
            new_password = st.text_input("Password", type="password", key="reg_pass", placeholder="Enter secure password")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            
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
                    
            st.markdown("<div style='margin: 1.2rem 0; border-top: 1px solid var(--shop-line);'></div>", unsafe_allow_html=True)
            st.page_link(user_login_page, label="🛒 Already have an account? User Login", use_container_width=True)


# =============== HOME PAGE ===============
def home_page():
    """Main home page after login"""
    # Sleek header bar with logout and user details
    col_hdr1, col_hdr2 = st.columns([4, 1])
    with col_hdr1:
        st.markdown(
            f"<div style='padding-top: 0.5rem;'>"
            f"👤 Welcome back, <strong>{st.session_state.username}</strong>! "
            f"<span style='color: var(--shop-muted); font-size: 0.9rem;'>&bull; Role: {st.session_state.user_role.upper()} &bull; ID: #{st.session_state.user_id}</span>"
            f"</div>",
            unsafe_allow_html=True
        )
    with col_hdr2:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.user_role = None
            st.session_state.token = None
            st.session_state.cart = []
            st.session_state.recommendations = []   # ← RECOMMENDATION ENGINE
            st.success("Logged out!")
            st.rerun()

    st.markdown(
        """
        <div class="shop-hero">
            <div class="section-label">AI powered shopping</div>
            <h1>Shopping Store</h1>
            <p>Browse curated products, get cart-aware recommendations, and track delivery updates in one place.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.user_role == "driver":
        st.subheader("Assigned Deliveries")
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
                            st.markdown(f"**Status:** {first.get('status')} | **Location:** {first.get('current_location')}")
                            st.markdown(f"**Shipped:** {first.get('shipped_at')} | **ETA:** {first.get('estimated_delivery')}")
                            if first.get("tracking_note"):
                                st.caption(first.get("tracking_note"))

                            st.markdown("#### Items to Deliver")
                            for item in rows:
                                item_total = item.get('price', 0) * item.get('quantity', 0)
                                col_del1, col_del2, col_del3 = st.columns([3, 1, 1])
                                with col_del1:
                                    st.markdown(f"**{item.get('product_name')}**")
                                with col_del2:
                                    st.markdown(f"{item.get('quantity')}x")
                                with col_del3:
                                    st.markdown(f"**${item_total:.2f}**")
                else:
                    st.info("No deliveries assigned yet.")
            else:
                st.error(f"Could not fetch deliveries: {response_detail(response)}")
        except Exception as e:
            st.error(f"Error fetching deliveries: {str(e)}")
        return
    
    # Main tabs - vary based on role
    if st.session_state.user_role == "admin":
        tab_shop, tab_cart, tab_orders, tab_admin = st.tabs(["🛒 Shop", "💳 Cart", "📦 Orders", "👨‍💼 Admin Panel"])
    elif st.session_state.user_role == "manager":
        tab_shop, tab_cart, tab_orders, tab_manager = st.tabs(["🛒 Shop", "💳 Cart", "📦 Orders", "📊 Manager Panel"])
    else:
        tab_shop, tab_cart, tab_orders = st.tabs(["🛒 Shop", "💳 Cart", "📦 Orders"])
    
    # SHOP TAB
    with tab_shop:
        st.subheader("Available Products")
        
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        with col1:
            search_name = st.text_input("AI filter", placeholder="e.g. cheap electronics, desk items under 50")
        with col2:
            selected_category = st.selectbox(
                "Category",
                ["All", "Electronics", "Furniture", "Cosmetics", "Other"],
                key="shop_category_filter",
            )
        with col3:
            selected_sort = st.selectbox(
                "Sort",
                ["AI best match", "Name A-Z", "Price low-high", "Price high-low", "Most stock"],
                key="shop_sort_filter",
            )
        with col4:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            refresh = st.button("Refresh", use_container_width=True)
        
        categories = ["Electronics", "Furniture", "Cosmetics", "Other"]
        category_labels = {
            "Electronics": "Electronics",
            "Furniture": "Furniture",
            "Cosmetics": "Cosmetics",
            "Other": "Other",
        }

        grouped_products = None
        with st.spinner("Filtering products..."):
            try:
                sort_map = {
                    "AI best match": "ai",
                    "Name A-Z": "name_asc",
                    "Price low-high": "price_low",
                    "Price high-low": "price_high",
                    "Most stock": "stock_high",
                }
                response = requests.post(
                    f"{API_URL}/api/products/filter",
                    json={
                        "query": search_name,
                        "category": None if selected_category == "All" else selected_category,
                        "sort_by": sort_map[selected_sort],
                    },
                    timeout=20,
                )
                if response.status_code == 200:
                    filter_payload = response.json()
                    grouped_products = filter_payload.get("grouped", {})
                    if search_name or selected_category != "All" or selected_sort != "AI best match":
                        match_count = filter_payload.get("count", 0)
                        st.caption(f"AI filter found {match_count} matching products")
                else:
                    st.error(f"Could not filter products: {response_detail(response)}")
            except Exception as e:
                st.error(f"Error filtering products: {str(e)}")

        if grouped_products:
            rendered_any = False
            for category in categories:
                products = grouped_products.get(category, [])

                if not products:
                    continue

                rendered_any = True
                category_icons = {
                    "Electronics": "💻",
                    "Furniture": "🛋️",
                    "Cosmetics": "💅",
                    "Other": "📦"
                }
                st.markdown(
                    f"<div class='category-header'>{category_icons.get(category, '📦')} {category_labels[category]}</div>", 
                    unsafe_allow_html=True
                )
                cols = st.columns(3)
                for idx, product in enumerate(products):
                    with cols[idx % 3]:
                        render_shop_product_card(product, f"{category.lower()}_{idx}")

            if not rendered_any:
                st.info("No products found")

        # ── Recommendations panel ← RECOMMENDATION ENGINE ────────────────────
        if False and st.session_state.recommendations:
            st.divider()
            st.subheader("✨ You Might Also Like")
            rec_cols = st.columns(min(len(st.session_state.recommendations), 4))
            for ri, rec in enumerate(st.session_state.recommendations):
                with rec_cols[ri % 4]:
                    with st.container(border=True):
                        rec_img = rec.get("image_url") or (
                            "https://images.unsplash.com/photo-1531403009284"
                            "-440f080d1e12?w=500&auto=format&fit=crop&q=80"
                        )
                        st.image(rec_img, use_container_width=True)
                        st.markdown(f"**{rec['name']}**")
                        st.markdown(f"${rec['price']:.2f}")
                        if st.button(
                            "Add to Cart",
                            key=f"rec_add_{rec['id']}_{ri}",
                            use_container_width=True,
                        ):
                            existing = next(
                                (i for i in st.session_state.cart
                                 if i['product_id'] == rec['id']),
                                None,
                            )
                            if existing:
                                existing['quantity'] += 1
                            else:
                                st.session_state.cart.append({
                                    'product_id': rec['id'],
                                    'name':       rec['name'],
                                    'price':      rec['price'],
                                    'quantity':   1,
                                })
                            st.success(f"✅ Added {rec['name']}!")
                            # Refresh recommendations for the newly added item
                            try:
                                new_ids = ",".join(
                                    str(i['product_id']) for i in st.session_state.cart
                                )
                                r2 = requests.get(
                                    f"{API_URL}/recommendations/{rec['id']}",
                                    params={"limit": 4, "exclude_ids": new_ids},
                                    timeout=5,
                                )
                                if r2.status_code == 200:
                                    st.session_state.recommendations = (
                                        r2.json().get("recommendations", [])
                                    )
                            except Exception:
                                pass
                            st.rerun()
    
    # CART TAB
    with tab_cart:
        st.subheader("Shopping Cart")
        
        if st.session_state.cart:
            fetch_cart_ai_summary()
            summary = st.session_state.cart_ai_summary or fallback_cart_summary()
            st.info(summary.get("reply", fallback_cart_summary()["reply"]))
            st.caption(
                f"AI cart count: {summary.get('item_count', 0)} total items "
                f"across {summary.get('unique_count', 0)} product types."
            )

            total_price = 0
            
            to_remove = None
            
            with st.container(border=True):
                # Column headers for visual layout
                col_h1, col_h2, col_h3, col_h4 = st.columns([4, 2, 2, 1])
                with col_h1:
                    st.markdown("**Product**")
                with col_h2:
                    st.markdown("**Quantity**")
                with col_h3:
                    st.markdown("**Total**")
                with col_h4:
                    st.markdown("**Delete**")
                
                st.markdown("<div style='margin-bottom: 0.6rem; border-top: 1px solid var(--shop-line);'></div>", unsafe_allow_html=True)
                
                for idx, item in enumerate(st.session_state.cart):
                    item_total = item['price'] * item['quantity']
                    total_price += item_total
                    
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
                        st.markdown(f"<div style='padding-top: 8px;'><strong>${item_total:.2f}</strong></div>", unsafe_allow_html=True)
                    with col4:
                        if st.button("🗑️", key=f"cart_del_{item['product_id']}_{idx}", use_container_width=True):
                            to_remove = idx
                            
                    if idx < len(st.session_state.cart) - 1:
                        st.markdown("<div style='margin: 0.5rem 0; border-top: 1px solid rgba(15, 23, 42, 0.04);'></div>", unsafe_allow_html=True)
            
            if to_remove is not None:
                removed_item = st.session_state.cart.pop(to_remove)
                st.success(f"Removed {removed_item['name']} from cart!")
                st.rerun()
            
            st.divider()
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"### Total: ${total_price:.2f}")
            
            with col2:
                if st.button("Clear Cart", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()
            
            st.divider()
            
            # Checkout
            if st.button("✅ Checkout", use_container_width=True, type="primary"):
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
                        st.success("✅ Order placed successfully!")
                        st.session_state.cart = []
                        st.rerun()
                    else:
                        st.error("❌ Error placing order")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.info("💭 Your cart is empty. Start shopping! 🛍️")
    
    # ORDERS TAB
    with tab_orders:
        st.subheader("Your Orders")
        
        if st.button("🔄 Refresh Orders"):
            st.rerun()
        
        try:
            response = requests.get(f"{API_URL}/users/{st.session_state.user_id}")
            if response.status_code == 200:
                orders = response.json()
                
                if orders:
                    # Group by order_id
                    orders_dict = {}
                    for item in orders:
                        order_id = item.get('order_id')
                        if order_id is None:
                            continue
                        if order_id not in orders_dict:
                            orders_dict[order_id] = []
                        orders_dict[order_id].append(item)
                    
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
                                
                                total = 0
                                st.markdown("<div style='margin-bottom: 0.5rem; border-top: 1px solid var(--shop-line);'></div>", unsafe_allow_html=True)
                                for item in items:
                                    item_total = item['price'] * item['quantity']
                                    total += item_total
                                    
                                    col_item1, col_item2, col_item3 = st.columns([3, 1, 1])
                                    with col_item1:
                                        st.markdown(f"**{item['product_name']}**")
                                        st.caption(f"Unit Price: ${item['price']:.2f}")
                                    with col_item2:
                                        st.markdown(f"<div style='padding-top: 4px;'>{item['quantity']}x</div>", unsafe_allow_html=True)
                                    with col_item3:
                                        st.markdown(f"<div style='padding-top: 4px;'><strong>${item_total:.2f}</strong></div>", unsafe_allow_html=True)
                                
                                st.markdown("<div style='margin: 0.6rem 0; border-top: 1px dotted var(--shop-line);'></div>", unsafe_allow_html=True)
                                st.markdown(f"<div style='text-align: right;'><strong>Order Total: <span style='font-size: 1.15rem; color: var(--shop-accent-2);'>${total:.2f}</span></strong></div>", unsafe_allow_html=True)
                    else:
                        st.info("📦 No orders yet. Start shopping! 🛍️")
                else:
                    st.info("📦 No orders yet. Start shopping! 🛍️")
            else:
                st.error("❌ Could not fetch orders")
        except Exception as e:
            st.error(f"❌ Error fetching orders: {str(e)}")
    
    # =============== ADMIN PANEL TAB ===============
    if st.session_state.user_role == "admin":
        with tab_admin:
            st.subheader("👨‍💼 Admin Dashboard")
            
            admin_section = st.radio("Select Section", ["👥 Manage Users", "🔍 View All Orders", "➕ Add Product", "📝 Manage Products"], key="admin_section", horizontal=True)
            
            # MANAGE USERS SECTION
            if admin_section == "👥 Manage Users":
                st.markdown("### All Users")
                
                if st.button("🔄 Refresh Users"):
                    st.rerun()
                
                try:
                    response = requests.get(f"{API_URL}/users")
                    if response.status_code == 200:
                        users = response.json()
                        
                        if users:
                            # Display users in a table
                            user_data = []
                            for user in users:
                                user_data.append({
                                    "ID": user.get('id'),
                                    "Name": user.get('name'),
                                    "Email": user.get('email'),
                                    "Role": user.get('role', 'user')
                                })
                            
                            df = pd.DataFrame(user_data)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            
                            st.divider()
                            
                            # Change user role
                            st.markdown("### Change User Role")
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                user_id_to_change = st.number_input("Select User ID", min_value=1, step=1)
                            
                            with col2:
                                new_role = st.selectbox("New Role", ["user", "manager", "admin"])
                            
                            with col3:
                                if st.button("Update Role", use_container_width=True, type="primary"):
                                    try:
                                        headers = {}
                                        if st.session_state.token:
                                            headers["Authorization"] = f"Bearer {st.session_state.token}"
                                        response = requests.put(
                                            f"{API_URL}/users/{user_id_to_change}/role",
                                            json={"role": new_role},
                                            headers=headers
                                        )
                                        if response.status_code == 200:
                                            st.success(f"✅ User {user_id_to_change} role updated to '{new_role}'!")
                                            st.rerun()
                                        else:
                                            st.error(f"❌ Error: {response.json().get('detail', 'Unknown error')}")
                                    except Exception as e:
                                        st.error(f"❌ Error: {str(e)}")
                            
                            st.divider()
                            
                            # Delete User
                            st.markdown("### Delete User")
                            col1_del, col2_del = st.columns([2, 1])
                            
                            with col1_del:
                                user_id_to_delete = st.number_input("Select User ID to Delete", min_value=1, step=1, key="delete_user_id_input")
                            
                            with col2_del:
                                # Add spacing to align button vertically with input
                                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                                if st.button("🗑️ Delete User", use_container_width=True, type="primary", key="delete_user_btn"):
                                    if user_id_to_delete == st.session_state.user_id:
                                        st.error("❌ You cannot delete your own admin account.")
                                    else:
                                        try:
                                            headers = {}
                                            if st.session_state.token:
                                                headers["Authorization"] = f"Bearer {st.session_state.token}"
                                            response = requests.delete(
                                                f"{API_URL}/users/{user_id_to_delete}",
                                                headers=headers
                                            )
                                            if response.status_code == 200:
                                                st.success(f"✅ User {user_id_to_delete} deleted successfully!")
                                                st.rerun()
                                            else:
                                                st.error(f"❌ Error: {response.json().get('detail', 'Unknown error')}")
                                        except Exception as e:
                                            st.error(f"❌ Error: {str(e)}")
                        else:
                            st.info("No users found")
                    else:
                        st.error("❌ Could not fetch users")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
            
            # VIEW ALL ORDERS SECTION
            elif admin_section == "🔍 View All Orders":
                st.markdown("### All Orders")
                
                if st.button("🔄 Refresh All Orders"):
                    st.rerun()
                
                try:
                    response = requests.get(f"{API_URL}/users")
                    if response.status_code == 200:
                        users = response.json()
                        
                        if users:
                            all_orders = []
                            for user in users:
                                try:
                                    user_orders_response = requests.get(f"{API_URL}/users/{user['id']}")
                                    if user_orders_response.status_code == 200:
                                        user_orders = user_orders_response.json()
                                        for order in user_orders:
                                            if order.get('order_id'):
                                                all_orders.append({
                                                    "User": order.get('name'),
                                                    "User ID": order.get('id'),
                                                    "Order ID": order.get('order_id'),
                                                    "Product": order.get('product_name'),
                                                    "Price": f"${order.get('price', 0):.2f}",
                                                    "Quantity": order.get('quantity'),
                                                })
                                except:
                                    pass
                            
                            if all_orders:
                                df = pd.DataFrame(all_orders)
                                st.dataframe(df, use_container_width=True, hide_index=True)
                                st.markdown(f"**Total Orders:** {len(all_orders)}")
                            else:
                                st.info("No orders found")
                        else:
                            st.info("No users found")
                    else:
                        st.error("❌ Could not fetch data")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
            
            # ADD PRODUCT SECTION
            elif admin_section == "➕ Add Product":
                render_add_product("admin")
            
            # MANAGE PRODUCTS SECTION
            elif admin_section == "📝 Manage Products":
                render_manage_products("admin")
    
    # =============== MANAGER PANEL TAB ===============
    if st.session_state.user_role == "manager":
        with tab_manager:
            st.subheader("📊 Manager Dashboard")
            
            manager_section = st.radio("Select Section", ["➕ Add Product", "📝 Manage Products", "👥 View Users & Managers"], key="manager_section", horizontal=True)
            
            # ADD PRODUCT SECTION
            if manager_section == "➕ Add Product":
                render_add_product("manager")
            
            # MANAGE PRODUCTS SECTION
            elif manager_section == "📝 Manage Products":
                render_manage_products("manager")
                
            # VIEW USERS & MANAGERS SECTION
            elif manager_section == "👥 View Users & Managers":
                st.markdown("### Registered Users & Managers")
                
                if st.button("🔄 Refresh List", key="mgr_refresh_users"):
                    st.rerun()
                
                try:
                    headers = {}
                    if st.session_state.token:
                        headers["Authorization"] = f"Bearer {st.session_state.token}"
                    response = requests.get(
                        f"{API_URL}/manager/users",
                        headers=headers
                    )
                    if response.status_code == 200:
                        users = response.json()
                        
                        if users:
                            user_data = []
                            for user in users:
                                user_data.append({
                                    "ID": user.get('id'),
                                    "Name": user.get('name'),
                                    "Email": user.get('email'),
                                    "Role": user.get('role', 'user')
                                })
                            
                            df = pd.DataFrame(user_data)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No users or managers found")
                    else:
                        st.error(f"❌ Error: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")



# =============== MAIN APP LOGIC ===============
# Define page objects for routing
user_login_page = st.Page(user_login, title="User Login", url_path="user", default=True)
manager_login_page = st.Page(manager_login, title="Manager Login", url_path="manager")
admin_login_page = st.Page(admin_login, title="Admin Login", url_path="admin")
driver_login_page = st.Page(driver_login, title="Driver Login", url_path="driver")
register_page = st.Page(register_view, title="Register", url_path="register")
home_page_obj = st.Page(home_page, title="Home", url_path="home", default=True)

# Run navigation
if st.session_state.user_id is None:
    pg = st.navigation([user_login_page, manager_login_page, admin_login_page, driver_login_page, register_page], position="hidden")
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
            
            // 1. Initialize state in the parent window if it doesn't exist
            if (!parentWin.chatWidgetState) {{
                parentWin.chatWidgetState = {{
                    isOpen: false,
                    history: [],
                    messagesHtml: '<div class="message bot">Hello! I\\'m your shopping assistant. How can I help you find products or orders today?</div>',
                    inputText: ""
                }};
            }}
            
            // 2. Remove old widget container and styling to refresh handlers
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
            
            // 3. Create style element
            var style = parentDoc.createElement("style");
            style.id = "floating-chat-widget-style";
            style.innerHTML = `
                .chat-btn {{
                    position: fixed;
                    bottom: 25px;
                    right: 25px;
                    width: 58px;
                    height: 58px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #0f766e 0%, #2563eb 100%);
                    box-shadow: 0 16px 36px rgba(15, 23, 42, 0.24);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 28px;
                    cursor: pointer;
                    z-index: 999999;
                    transition: transform 0.18s ease, box-shadow 0.18s ease;
                }}
                .chat-btn:hover {{
                    transform: translateY(-2px) scale(1.04);
                    box-shadow: 0 20px 44px rgba(15, 23, 42, 0.30);
                }}
                .chat-window {{
                    position: fixed;
                    bottom: 95px;
                    right: 25px;
                    width: min(380px, calc(100vw - 30px));
                    height: min(520px, calc(100vh - 125px));
                    border-radius: 18px;
                    background: rgba(255, 255, 255, 0.96);
                    backdrop-filter: blur(16px);
                    -webkit-backdrop-filter: blur(16px);
                    border: 1px solid rgba(15, 23, 42, 0.12);
                    box-shadow: 0 24px 60px rgba(15, 23, 42, 0.24);
                    display: flex;
                    flex-direction: column;
                    z-index: 999999;
                    overflow: hidden;
                    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                    transition: all 0.3s cubic-bezier(0.1, 0.8, 0.3, 1);
                }}
                .chat-header {{
                    background: linear-gradient(135deg, #0f766e 0%, #2563eb 100%);
                    color: white;
                    padding: 14px 16px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-weight: bold;
                }}
                .chat-header .title {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 15px;
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
                    padding: 14px;
                    overflow-y: auto;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }}
                .chat-messages::-webkit-scrollbar {{
                    width: 6px;
                }}
                .chat-messages::-webkit-scrollbar-track {{
                    background: transparent;
                }}
                .chat-messages::-webkit-scrollbar-thumb {{
                    background: rgba(15, 23, 42, 0.12);
                    border-radius: 3px;
                }}
                .chat-messages::-webkit-scrollbar-thumb:hover {{
                    background: rgba(15, 23, 42, 0.24);
                }}
                @keyframes fadeIn {{
                    from {{ opacity: 0; transform: translateY(8px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}
                .message {{
                    max-width: 80%;
                    padding: 10px 14px;
                    border-radius: 14px;
                    font-size: 14px;
                    line-height: 1.4;
                    word-wrap: break-word;
                    animation: fadeIn 0.22s ease-out forwards;
                }}
                .message.user {{
                    align-self: flex-end;
                    background: linear-gradient(135deg, #2563eb, #0f766e);
                    color: white;
                    border-bottom-right-radius: 2px;
                }}
                .message.bot {{
                    align-self: flex-start;
                    background-color: #f1f5f9;
                    color: #16202a;
                    border-bottom-left-radius: 2px;
                }}
                .chat-input-area {{
                    padding: 12px;
                    background: rgba(255, 255, 255, 0.8);
                    border-top: 1px solid rgba(15, 23, 42, 0.08);
                    display: flex;
                    gap: 8px;
                }}
                .chat-input {{
                    flex-grow: 1;
                    border: 1px solid rgba(15, 23, 42, 0.14);
                    border-radius: 999px;
                    padding: 8px 16px;
                    font-size: 14px;
                    outline: none;
                    transition: border 0.2s, box-shadow 0.2s;
                }}
                .chat-input:focus {{
                    border-color: #0f766e;
                    box-shadow: 0 0 0 2px rgba(15, 118, 110, 0.15);
                }}
                .send-btn {{
                    background: #0f766e;
                    border: none;
                    color: white;
                    border-radius: 50%;
                    width: 36px;
                    height: 36px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    transition: background 0.2s, transform 0.15s;
                }}
                .send-btn:hover {{
                    background: #2563eb;
                    transform: scale(1.05);
                }}
                .typing-indicator {{
                    display: flex;
                    gap: 4px;
                    padding: 6px 10px;
                    align-self: flex-start;
                    background: rgba(240, 240, 240, 0.9);
                    border-radius: 10px;
                }}
                .typing-dot {{
                    width: 6px;
                    height: 6px;
                    background: #999;
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
            
            // 4. Create widget container
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
            
            // Get elements
            var btn = parentDoc.getElementById("chat-toggle-btn");
            var windowEl = parentDoc.getElementById("chat-widget-window");
            var closeBtn = parentDoc.getElementById("chat-close-btn");
            var messagesContainer = parentDoc.getElementById("chat-messages-container");
            var inputEl = parentDoc.getElementById("chat-message-input");
            var sendBtn = parentDoc.getElementById("chat-send-btn");
            
            // 5. Restore widget state
            windowEl.style.display = parentWin.chatWidgetState.isOpen ? "flex" : "none";
            messagesContainer.innerHTML = parentWin.chatWidgetState.messagesHtml;
            inputEl.value = parentWin.chatWidgetState.inputText;
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            // 6. Define event handlers
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
                
                // Save innerHTML to state
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
    # Ensure widget is removed from DOM when logged out / on login page
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
            // Clear parent state
            if (window.parent.chatWidgetState) {
                window.parent.chatWidgetState = null;
            }
        })();
        </script>
        """,
        height=0,
        width=0
    )


