from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from database import DB_connection
from auth import decode_access_token

router = APIRouter()
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Extract and validate user details from JWT token"""
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")
    return payload

def RoleChecker(allowed_roles: List[str]):
    """
    Generic role checker that verifies JWT claims against required roles
    Usage: Depends(RoleChecker(["admin"]))
    """
    async def check_role(current_user: dict = Depends(get_current_user)) -> str:
        user_role = current_user.get('role', 'user')
        if user_role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Access required: {', '.join(allowed_roles)}")
        return user_role
    
    return check_role

@router.get("/user/my-data")
def user_get_own_data(current_user: dict = Depends(get_current_user)):
    """Any authenticated USER, MANAGER, or ADMIN can access their own data"""
    user_id = current_user.get("id")
    role = current_user.get("role")
    try:
        connection = DB_connection()
        with connection.cursor() as cursor:
            sql = "SELECT id, name, email, role FROM users WHERE id = %s"
            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()
            if result:
                return {"data": result, "accessed_by_role": role}
            else:
                raise HTTPException(status_code=404, detail="User not found")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()