"""
analytics.py — Admin analytics router.
Provides gross revenue, order pipeline stats, and top products.
Works with both MySQL and PostgreSQL (via DB_TYPE flag).
"""

from fastapi import APIRouter, HTTPException
from database import DB_connection, DB_TYPE

router = APIRouter(prefix="/admin", tags=["admin"])


def _placeholder(val, default=0):
    return val if val is not None else default


@router.get("/analytics")
def get_analytics():
    """Return admin analytics: revenue, order counts by status, top products."""
    try:
        conn = DB_connection()
        with conn.cursor() as cur:
            # ── 1. Gross revenue (sum of price * quantity across all orders) ──
            cur.execute("""
                SELECT COALESCE(SUM(p.price * oi.quantity), 0) AS gross_revenue
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
            """)
            row = cur.fetchone()
            gross_revenue = float(_placeholder(row["gross_revenue"] if row else 0))

            # ── 2. Total orders ──────────────────────────────────────────────
            cur.execute("SELECT COUNT(*) AS total FROM orders")
            row = cur.fetchone()
            total_orders = int(_placeholder(row["total"] if row else 0))

            # ── 3. Active orders (delivery status not 'Delivered') ───────────
            cur.execute("""
                SELECT COUNT(DISTINCT o.id) AS active
                FROM orders o
                LEFT JOIN deliveries d ON d.order_id = o.id
                WHERE d.status IS NULL OR d.status != 'Delivered'
            """)
            row = cur.fetchone()
            active_orders = int(_placeholder(row["active"] if row else 0))

            # ── 4. Completed orders (delivery status = 'Delivered') ──────────
            cur.execute("""
                SELECT COUNT(DISTINCT o.id) AS completed
                FROM orders o
                JOIN deliveries d ON d.order_id = o.id
                WHERE d.status = 'Delivered'
            """)
            row = cur.fetchone()
            completed_orders = int(_placeholder(row["completed"] if row else 0))

            # ── 5. Order pipeline (count per delivery status) ────────────────
            cur.execute("""
                SELECT COALESCE(d.status, 'Pending') AS status, COUNT(*) AS count
                FROM orders o
                LEFT JOIN deliveries d ON d.order_id = o.id
                GROUP BY COALESCE(d.status, 'Pending')
            """)
            pipeline = [{"status": r["status"], "count": int(r["count"])} for r in cur.fetchall()]

            # ── 6. Top 10 products by revenue ─────────────────────────────
            cur.execute("""
                SELECT p.name,
                       SUM(oi.quantity) AS units_sold,
                       SUM(p.price * oi.quantity) AS revenue
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                GROUP BY p.id, p.name
                ORDER BY revenue DESC
                LIMIT 10
            """)
            top_products = [
                {
                    "name": r["name"],
                    "units_sold": int(r["units_sold"]),
                    "revenue": float(r["revenue"]),
                }
                for r in cur.fetchall()
            ]

            # ── 7. Daily revenue (last 30 days) ──────────────────────────
            if DB_TYPE == "mysql":
                date_trunc = "DATE(o.created_at)"
            else:
                date_trunc = "DATE_TRUNC('day', o.created_at)"

            cur.execute(f"""
                SELECT {date_trunc} AS day,
                       COALESCE(SUM(p.price * oi.quantity), 0) AS revenue
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                JOIN products p ON p.id = oi.product_id
                WHERE o.created_at >= NOW() - INTERVAL {'30 DAY' if DB_TYPE == 'mysql' else "'30 days'"}
                GROUP BY {date_trunc}
                ORDER BY day
            """)
            daily_revenue = [
                {"day": str(r["day"]), "revenue": float(r["revenue"])}
                for r in cur.fetchall()
            ]

            # ── 8. Low-stock alerts ──────────────────────────────────────
            cur.execute("""
                SELECT id, name, stock,
                       COALESCE(low_stock_threshold, 10) AS threshold,
                       COALESCE(locality, 'N/A') AS locality
                FROM products
                WHERE stock <= COALESCE(low_stock_threshold, 10)
                ORDER BY stock ASC
                LIMIT 20
            """)
            low_stock = [dict(r) for r in cur.fetchall()]

        return {
            "gross_revenue": gross_revenue,
            "total_orders": total_orders,
            "active_orders": active_orders,
            "completed_orders": completed_orders,
            "pipeline": pipeline,
            "top_products": top_products,
            "daily_revenue": daily_revenue,
            "low_stock_alerts": low_stock,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
