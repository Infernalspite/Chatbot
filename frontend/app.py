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
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.title("🛍️ Shopping Store")
        st.markdown("### 🛒 User Portal")
        st.markdown("Welcome! Please login to continue.")
        st.markdown("---")
        
        user_username = st.text_input("Username", key="user_user", placeholder="e.g. John Doe")
        user_password = st.text_input("Password", type="password", key="user_pass", placeholder="••••")
        if st.button("Login as User", key="user_btn", type="primary", use_container_width=True):
            handle_login(user_username, user_password, "user")
            
        st.markdown("---")
        st.page_link(register_page, label="📝 Don't have an account? Register here", icon="📝")

def manager_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.title("🛍️ Shopping Store")
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
        st.title("🛍️ Shopping Store")
        st.markdown("### 👨‍💼 Admin Portal")
        st.markdown("Administrator authentication required.")
        st.markdown("---")
        
        adm_username = st.text_input("Username", key="adm_user", placeholder="e.g. John Doe")
        adm_password = st.text_input("Password", type="password", key="adm_pass", placeholder="••••")
        if st.button("Login as Admin", key="adm_btn", type="primary", use_container_width=True):
            handle_login(adm_username, adm_password, "admin")
            
        st.markdown("---")
        st.page_link(user_login_page, label="🛒 Go back to User Login", icon="🛒")

def register_view():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.title("🛍️ Shopping Store")
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
    """Main home page after login"""
    # Top bar with user info and logout
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("🛍️ Shopping Store")
    
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.user_role = None
            st.session_state.token = None
            st.session_state.cart = []
            st.session_state.recommendations = []   # ← RECOMMENDATION ENGINE
            st.success("✅ Logged out successfully!")
            st.rerun()
    
    st.divider()
    
    # User info bar
    st.info(f"👤 Welcome, **{st.session_state.username}** | Role: **{st.session_state.user_role}** | ID: {st.session_state.user_id}")
    
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
            refresh = st.button("Refresh")
        
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
                st.markdown(f"## {category_labels[category]}")
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
                        st.info("ðŸ“¦ No orders yet. Start shopping! ðŸ›ï¸")
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
            
            admin_section = st.radio("Select Section", ["👥 Manage Users", "🔍 View All Orders", "➕ Add Product", "📝 Manage Products"], key="admin_section")
            
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
            
            manager_section = st.radio("Select Section", ["➕ Add Product", "📝 Manage Products", "👥 View Users & Managers"], key="manager_section")
            
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
register_page = st.Page(register_view, title="Register", url_path="register")
home_page_obj = st.Page(home_page, title="Home", url_path="home", default=True)

# Run navigation
if st.session_state.user_id is None:
    pg = st.navigation([user_login_page, manager_login_page, admin_login_page, register_page], position="hidden")
else:
    pg = st.navigation([home_page_obj], position="hidden")

pg.run()


# =============== SERVER-SIDE CHATBOT ===============
if st.session_state.user_id is not None:
    if "support_chat_history" not in st.session_state:
        st.session_state.support_chat_history = [
            {
                "role": "assistant",
                "content": "Hello! I'm your shopping assistant. Ask me about products, your orders, or what's in your cart.",
            }
        ]

    with st.sidebar:
        st.subheader("Shopping Assistant")

        for msg in st.session_state.support_chat_history[-8:]:
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['content']}")
            else:
                st.markdown(f"**Assistant:** {msg['content']}")

        with st.form("support_chat_form", clear_on_submit=True):
            chat_prompt = st.text_input("Ask a question", placeholder="What is in my cart?")
            chat_submitted = st.form_submit_button("Send", use_container_width=True)

        if chat_submitted and chat_prompt.strip():
            user_message = chat_prompt.strip()
            st.session_state.support_chat_history.append({"role": "user", "content": user_message})
            try:
                response = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "message": user_message,
                        "history": st.session_state.support_chat_history[-10:],
                        "user_id": st.session_state.user_id,
                        "cart_items": [
                            {
                                "product_id": item["product_id"],
                                "name": item["name"],
                                "price": float(item["price"]),
                                "quantity": int(item["quantity"]),
                            }
                            for item in st.session_state.cart
                        ],
                    },
                    timeout=60,
                )
                if response.status_code == 200:
                    reply = response.json().get("reply", "Sorry, I could not answer that.")
                else:
                    reply = f"Sorry, I could not reach the support server. {response_detail(response)}"
            except Exception as e:
                reply = f"Sorry, I could not reach the support server. {str(e)}"

            st.session_state.support_chat_history.append({"role": "assistant", "content": reply})
            st.session_state.support_chat_history = st.session_state.support_chat_history[-10:]
            st.rerun()


# =============== REMOVE OLD FLOATING CHAT WIDGET ===============
import streamlit.components.v1 as components

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
    width=0,
)
