"""
Authentication API endpoints

Provides user registration, login, password reset, and user management.
Uses Supabase Auth for JWT-based authentication.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from src.auth import supabase, get_current_user, AuthUser
from src.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# === Configuration Endpoint ===

@router.get("/config")
async def get_config():
    """
    Get public Supabase configuration for frontend.
    Only returns public keys (ANON key, not SERVICE key).
    """
    from config.settings import settings
    return {
        "supabaseUrl": settings.SUPABASE_URL,
        "supabaseAnonKey": settings.SUPABASE_ANON_KEY
    }


# === Request/Response Models ===

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    anonymous_user_id: Optional[str] = None  # For data migration


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordUpdateRequest(BaseModel):
    new_password: str


class AuthResponse(BaseModel):
    user_id: str
    email: str
    access_token: str
    refresh_token: str


# === Endpoints ===

@router.post("/auth/signup", response_model=AuthResponse)
async def sign_up(request: SignUpRequest):
    """
    Register new user with email/password.
    Sends verification email automatically via Supabase.

    Args:
        request: Signup request with email, password, and optional anonymous_user_id

    Returns:
        AuthResponse with user_id, email, and JWT tokens

    Raises:
        HTTPException: If signup fails
    """
    try:
        if not supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )

        # Create user in Supabase Auth
        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })

        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sign up failed"
            )

        user = response.user
        session = response.session

        if not session:
            # Email confirmation required - user created but not verified
            logger.info(f"User created: {user.email}, awaiting email confirmation")
            return {
                "user_id": str(user.id),
                "email": user.email,
                "access_token": "",
                "refresh_token": "",
                "message": "Check your email to confirm your account"
            }

        # Create user in our database
        with get_db() as cursor:
            cursor.execute("""
                INSERT INTO users (id, email, is_anonymous, supabase_user_id, created_at)
                VALUES (%s, %s, FALSE, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET
                    email = EXCLUDED.email,
                    is_anonymous = FALSE,
                    supabase_user_id = EXCLUDED.supabase_user_id
            """, (str(user.id), user.email, str(user.id)))

        # Migrate anonymous user data if provided
        if request.anonymous_user_id:
            await migrate_anonymous_data(
                anonymous_id=request.anonymous_user_id,
                authenticated_id=str(user.id)
            )

        logger.info(f"✓ User signed up: {user.email}")

        return AuthResponse(
            user_id=str(user.id),
            email=user.email,
            access_token=session.access_token,
            refresh_token=session.refresh_token
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sign up error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/auth/signin", response_model=AuthResponse)
async def sign_in(request: SignInRequest):
    """
    Login with email/password.

    Args:
        request: Sign-in request with email and password

    Returns:
        AuthResponse with user_id, email, and JWT tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        if not supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )

        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })

        if not response.user or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        user = response.user
        session = response.session

        # Update last login in our database
        with get_db() as cursor:
            cursor.execute("""
                UPDATE users
                SET last_login = CURRENT_TIMESTAMP
                WHERE supabase_user_id = %s
            """, (str(user.id),))

        logger.info(f"✓ User signed in: {user.email}")

        return AuthResponse(
            user_id=str(user.id),
            email=user.email,
            access_token=session.access_token,
            refresh_token=session.refresh_token
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sign in error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.post("/auth/signout")
async def sign_out(user: AuthUser = Depends(get_current_user)):
    """
    Sign out current user.

    Args:
        user: Current authenticated user

    Returns:
        Success message

    Raises:
        HTTPException: If sign out fails
    """
    try:
        if not supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )

        supabase.auth.sign_out()
        logger.info(f"✓ User signed out: {user.email}")
        return {"message": "Signed out successfully"}
    except Exception as e:
        logger.error(f"Sign out error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/auth/forgot-password")
async def forgot_password(request: PasswordResetRequest):
    """
    Send password reset email.
    Supabase sends email automatically with reset link.

    Args:
        request: Password reset request with email

    Returns:
        Success message (doesn't reveal if email exists)
    """
    try:
        if not supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )

        supabase.auth.reset_password_email(request.email)
        logger.info(f"Password reset requested for: {request.email}")
        # Don't reveal if email exists (security best practice)
        return {"message": "If that email exists, a reset link has been sent"}
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        # Still don't reveal if email exists
        return {"message": "If that email exists, a reset link has been sent"}


@router.post("/auth/reset-password")
async def reset_password(
    request: PasswordUpdateRequest,
    user: AuthUser = Depends(get_current_user)
):
    """
    Update password (called after clicking reset link).
    User must be authenticated via reset token.

    Args:
        request: Password update request with new password
        user: Current user (authenticated via reset token)

    Returns:
        Success message

    Raises:
        HTTPException: If password update fails
    """
    try:
        if not supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )

        supabase.auth.update_user({
            "password": request.new_password
        })
        logger.info(f"✓ Password updated for: {user.email}")
        return {"message": "Password updated successfully"}
    except Exception as e:
        logger.error(f"Password update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/auth/resend-verification")
async def resend_verification(request: PasswordResetRequest):
    """
    Resend email verification.

    Args:
        request: Request with email

    Returns:
        Success message
    """
    try:
        if not supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )

        # Supabase doesn't have direct resend API, use password reset as workaround
        supabase.auth.reset_password_email(request.email)
        logger.info(f"Verification email resent for: {request.email}")
        return {"message": "If that email exists, verification has been sent"}
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        return {"message": "If that email exists, verification has been sent"}


@router.get("/auth/me")
async def get_me(user: AuthUser = Depends(get_current_user)):
    """
    Get current user info.

    Args:
        user: Current user (authenticated or anonymous)

    Returns:
        User information
    """
    return {
        "user_id": user.id,
        "email": user.email,
        "is_anonymous": user.is_anonymous
    }


# === Helper Functions ===

async def migrate_anonymous_data(anonymous_id: str, authenticated_id: str):
    """
    Migrate data from anonymous user to authenticated user.
    Called when user signs up after browsing anonymously.

    Args:
        anonymous_id: UUID of anonymous user
        authenticated_id: UUID of authenticated user

    Note:
        Uses ON CONFLICT to merge data (e.g., sum cart quantities)
    """
    try:
        with get_db() as cursor:
            # Migrate shopping cart (merge quantities if item already exists)
            cursor.execute("""
                INSERT INTO shopping_carts (
                    user_id, product_name, price, quantity, aisle, image_url,
                    search_term, is_sold_by_weight, unit_price
                )
                SELECT %s, product_name, price, quantity, aisle, image_url,
                       search_term, is_sold_by_weight, unit_price
                FROM shopping_carts
                WHERE user_id = %s
                ON CONFLICT (user_id, product_name) DO UPDATE SET
                    quantity = shopping_carts.quantity + EXCLUDED.quantity
            """, (authenticated_id, anonymous_id))

            # Migrate saved lists
            cursor.execute("""
                UPDATE saved_lists
                SET user_id = %s
                WHERE user_id = %s
            """, (authenticated_id, anonymous_id))

            # Migrate recipes
            cursor.execute("""
                UPDATE recipes
                SET user_id = %s
                WHERE user_id = %s
            """, (authenticated_id, anonymous_id))

            # Delete anonymous cart items (already migrated)
            cursor.execute("""
                DELETE FROM shopping_carts WHERE user_id = %s
            """, (anonymous_id,))

            # Delete anonymous user record
            cursor.execute("""
                DELETE FROM users WHERE id = %s
            """, (anonymous_id,))

            logger.info(f"✓ Migrated anonymous user {anonymous_id[:8]}... to {authenticated_id[:8]}...")

    except Exception as e:
        logger.error(f"Migration error: {e}")
        # Don't raise - let signup succeed even if migration fails
