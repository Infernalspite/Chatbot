from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Header, Depends
from typing import List, Optional
from schema import Product, RoleUpdate
from rbac import RoleChecker, get_current_user
from database import DB_connection, DB_TYPE
from product_classifier import classify_and_update_product

router = APIRouter()

@router.put("/users/{user_id}/role")
def update_user_role(user_id: int = Path(...), role_update: RoleUpdate = ..., current_user: dict = Depends(get_current_user)):
    """Update user role - Only admin can access. Uses JWT for authentication"""
    admin_user_id = current_user.get("id")
    try:
        # Check if admin user exists and has admin role
        connection = DB_connection()
        with connection.cursor() as cursor:
            check_admin_sql = "SELECT role FROM users WHERE id = %s"
            cursor.execute(check_admin_sql, (admin_user_id,))
            admin_result = cursor.fetchone()
            
            if not admin_result or admin_result.get('role') != 'admin':
                raise HTTPException(status_code=403, detail="Admin access required")
            
            # Validate role
            valid_roles = ["user", "manager", "admin"]
            if role_update.role not in valid_roles:
                raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
            
            # Check if target user exists
            check_sql = "SELECT id FROM users WHERE id = %s"
            cursor.execute(check_sql, (user_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="User not found")
            
            # Update user role
            sql = "UPDATE users SET role = %s WHERE id = %s"
            cursor.execute(sql, (role_update.role, user_id))
            connection.commit()
            return {"message": f"User role updated to '{role_update.role}' successfully", "user_id": user_id, "new_role": role_update.role}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@router.delete("/users/{user_id}")
def delete_user(user_id: int = Path(...), current_user: dict = Depends(get_current_user)):
    """Delete user - Only admin can access. Uses JWT for authentication"""
    admin_user_id = current_user.get("id")
    try:
        # Check if admin user exists and has admin role
        connection = DB_connection()
        with connection.cursor() as cursor:
            check_admin_sql = "SELECT role FROM users WHERE id = %s"
            cursor.execute(check_admin_sql, (admin_user_id,))
            admin_result = cursor.fetchone()
            
            if not admin_result or admin_result.get('role') != 'admin':
                raise HTTPException(status_code=403, detail="Admin access required")
            
            # Check if target user exists
            check_sql = "SELECT id FROM users WHERE id = %s"
            cursor.execute(check_sql, (user_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="User not found")
            
            # Prevent admin from deleting themselves
            if user_id == admin_user_id:
                raise HTTPException(status_code=400, detail="Admins cannot delete their own account")
            
            # Get all order IDs for this user
            cursor.execute("SELECT id FROM orders WHERE user_id = %s", (user_id,))
            orders = cursor.fetchall()
            order_ids = [order['id'] for order in orders]
            
            if order_ids:
                # Delete order items for these orders
                format_strings = ','.join(['%s'] * len(order_ids))
                cursor.execute(f"DELETE FROM order_items WHERE order_id IN ({format_strings})", tuple(order_ids))
                
                # Delete orders
                cursor.execute("DELETE FROM orders WHERE user_id = %s", (user_id,))
            
            # Finally, delete user
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            connection.commit()
            return {"message": "User and associated orders deleted successfully", "user_id": user_id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@router.post("/products")
def create_product(
    product: Product,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Create product - Manager or Admin only. Uses JWT for authentication"""
    manager_user_id = current_user.get("id")
    try:
        # Check if user is manager or admin
        connection = DB_connection()
        with connection.cursor() as cursor:
            check_sql = "SELECT role FROM users WHERE id = %s"
            cursor.execute(check_sql, (manager_user_id,))
            user_result = cursor.fetchone()
            
            if not user_result or user_result.get('role') not in ['manager', 'admin']:
                raise HTTPException(status_code=403, detail="Manager or Admin access required")
            
            if DB_TYPE == "mysql":
                cursor.execute("INSERT INTO products (name, price, stock, image_url) VALUES (%s, %s, %s, %s)",
                               (product.name, product.price, product.stock, product.image_url))
                product_id = cursor.lastrowid
            else:
                cursor.execute("INSERT INTO products (name, price, stock, image_url) VALUES (%s, %s, %s, %s) RETURNING id",
                               (product.name, product.price, product.stock, product.image_url))
                product_id = cursor.fetchone()["id"]
            connection.commit()
            background_tasks.add_task(classify_and_update_product, product_id)
            return {"message": "Product created successfully", "product_id": product_id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@router.put("/products/{product_id}")
def update_product(
    product_id: int = Path(...),
    product: Product = ...,
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user),
):
    """Update product - Manager or Admin only. Uses JWT for authentication"""
    manager_user_id = current_user.get("id")
    try:
        # Check if user is manager or admin
        connection = DB_connection()
        with connection.cursor() as cursor:
            check_sql = "SELECT role FROM users WHERE id = %s"
            cursor.execute(check_sql, (manager_user_id,))
            user_result = cursor.fetchone()
            
            if not user_result or user_result.get('role') not in ['manager', 'admin']:
                raise HTTPException(status_code=403, detail="Manager or Admin access required")
            
            # Check if product exists
            check_product_sql = "SELECT id FROM products WHERE id = %s"
            cursor.execute(check_product_sql, (product_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Product not found")
            
            sql = "UPDATE products SET name = %s, price = %s, stock = %s, image_url = %s WHERE id = %s"
            cursor.execute(sql, (product.name, product.price, product.stock, product.image_url, product_id))
            connection.commit()
            if background_tasks:
                background_tasks.add_task(classify_and_update_product, product_id)
            return {"message": "Product updated successfully", "product_id": product_id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@router.delete("/products/{product_id}")
def delete_product(product_id: int = Path(...), current_user: dict = Depends(get_current_user)):
    """Delete product - Manager or Admin only. Uses JWT for authentication"""
    manager_user_id = current_user.get("id")
    try:
        # Check if user is manager or admin
        connection = DB_connection()
        with connection.cursor() as cursor:
            check_sql = "SELECT role FROM users WHERE id = %s"
            cursor.execute(check_sql, (manager_user_id,))
            user_result = cursor.fetchone()
            
            if not user_result or user_result.get('role') not in ['manager', 'admin']:
                raise HTTPException(status_code=403, detail="Manager or Admin access required")
            
            # Check if product exists
            check_product_sql = "SELECT id FROM products WHERE id = %s"
            cursor.execute(check_product_sql, (product_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Product not found")
            
            sql = "DELETE FROM products WHERE id = %s"
            cursor.execute(sql, (product_id,))
            connection.commit()
            return {"message": "Product deleted successfully", "product_id": product_id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@router.get("/admin/all-users")
def admin_get_all_users(role: str = Depends(RoleChecker(["admin"]))):
    """Only ADMIN can access this - Get all users"""
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            sql = "SELECT id, name, email, role FROM users"
            cursor.execute(sql)
            result = cursor.fetchall()
            return {"data": result, "accessed_by_role": role}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()


@router.get("/manager/users")
def manager_get_users(current_user: dict = Depends(get_current_user)):
    """Get only users and managers - Manager or Admin access. Uses JWT for authentication"""
    manager_user_id = current_user.get("id")
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            # Check if user is manager or admin
            check_sql = "SELECT role FROM users WHERE id = %s"
            cursor.execute(check_sql, (manager_user_id,))
            user_result = cursor.fetchone()
            
            if not user_result or user_result.get('role') not in ['manager', 'admin']:
                raise HTTPException(status_code=403, detail="Manager or Admin access required")
                
            sql = "SELECT id, name, email, role FROM users WHERE role IN ('user', 'manager')"
            cursor.execute(sql)
            result = cursor.fetchall()
            return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()
