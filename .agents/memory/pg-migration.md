---
name: PostgreSQL migration
description: Project originally targeted MySQL/pymysql on localhost:3030; Replit runtime only has PostgreSQL via DATABASE_URL secret.
---

## Rule
Always use psycopg2 + DATABASE_URL. Never configure pymysql or localhost:3030.

**Why:** MySQL is not available in the Replit container. The Replit-managed PostgreSQL instance is accessed via the `DATABASE_URL` secret (points to `helium`).

## Key compatibility changes made
- `database.py` uses `psycopg2.extras.RealDictCursor` (returns dict-like rows, same `.get()` / `[]` API as pymysql DictCursor).
- `INSERT ... RETURNING id` replaces `cursor.lastrowid` in `main.py` (create_order) and `mange.py` (create_product).
- `ON CONFLICT (product_id) DO UPDATE` replaces MySQL `ON DUPLICATE KEY UPDATE` in embeddings upserts.
- `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` works in PostgreSQL 9.6+.
- `tags` column stored as TEXT (JSON-serialised), not JSONB, so existing `json.loads(raw)` guards still apply.

## How to apply
Any future DB work: use psycopg2 + `%s` placeholders, `RETURNING id` for inserts that need the new PK, `ON CONFLICT` for upserts.
