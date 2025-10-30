"""
Authentication module using Supabase Auth

This module provides JWT-based authentication via Supabase Auth.
Supports both authenticated users and anonymous users for backward compatibility.
"""
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from typing import Optional
import logging
import jwt
from datetime import datetime

from config.settings import settings

logger = logging.getLogger(__name__)

# Token cache: {token: (user_data, expiry_timestamp)}
_token_cache = {}

# Initialize Supabase client (backend - uses service key for admin operations)
try:
    supabase: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY
    )
    logger.info("✓ Supabase client initialized")
except Exception as e:
    logger.error(f"✗ Failed to initialize Supabase client: {e}")
    supabase = None

# Security scheme for JWT bearer tokens
security = HTTPBearer(auto_error=False)


class AuthUser:
    """Authenticated user object"""
    def __init__(self, user_id: str, email: Optional[str], is_anonymous: bool = False):
        self.id = user_id  # UUID string
        self.email = email
        self.is_anonymous = is_anonymous

    def __repr__(self):
        return f"AuthUser(id={self.id[:8]}..., email={self.email}, anonymous={self.is_anonymous})"


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> AuthUser:
    """
    Get current authenticated user from JWT token.
    Falls back to anonymous user if no token provided.

    Args:
        credentials: Optional HTTP Bearer token
        request: Optional request object for getting anonymous ID header

    Returns:
        AuthUser object (authenticated or anonymous)

    Raises:
        HTTPException: If token is invalid or expired
    """
    import time

    # If no token, use anonymous user
    if not credentials:
        # Check if client sent anonymous ID in header
        if request:
            anonymous_id = request.headers.get('X-Anonymous-User-ID')
            if anonymous_id:
                return await get_or_create_anonymous_user(anonymous_id)
        return await create_anonymous_user()

    token = credentials.credentials
    start = time.time()

    try:
        # Check token cache first (avoid network call)
        if token in _token_cache:
            cached_user, expiry = _token_cache[token]
            if datetime.now().timestamp() < expiry:
                # Cache hit!
                cache_time = (time.time() - start) * 1000
                logger.info(f"⚡ Token cache hit: {cache_time:.1f}ms")
                return cached_user

        if not supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )

        # Decode JWT to get expiry (don't verify signature yet - Supabase will do that)
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            exp_timestamp = decoded.get('exp', 0)
        except:
            exp_timestamp = 0

        # Verify JWT token with Supabase (network call)
        verify_start = time.time()
        response = supabase.auth.get_user(token)
        verify_time = (time.time() - verify_start) * 1000
        logger.info(f"⏱️  Token verification took: {verify_time:.1f}ms")

        user = response.user

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        # Create auth user
        auth_user = AuthUser(
            user_id=str(user.id),
            email=user.email,
            is_anonymous=False
        )

        # Cache the token (use JWT expiry)
        _token_cache[token] = (auth_user, exp_timestamp)

        total_time = (time.time() - start) * 1000
        logger.info(f"⏱️  Total auth check: {total_time:.1f}ms (cached for future requests)")
        return auth_user

    except HTTPException:
        raise
    except Exception as e:
        # Token invalid or expired
        logger.warning(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> AuthUser:
    """
    Get current user, or return anonymous user if not authenticated.
    Does NOT raise 401 - used for endpoints that work with/without auth.

    Args:
        credentials: Optional HTTP Bearer token
        request: Optional request object for getting anonymous ID header

    Returns:
        AuthUser object (authenticated or anonymous)
    """
    if not credentials:
        # Check if client sent anonymous ID
        if request:
            anonymous_id = request.headers.get('X-Anonymous-User-ID')
            if anonymous_id:
                return await get_or_create_anonymous_user(anonymous_id)
        return await create_anonymous_user()

    try:
        return await get_current_user(credentials, request)
    except HTTPException:
        # Token invalid - fall back to anonymous
        logger.debug("Token invalid, falling back to anonymous user")
        if request:
            anonymous_id = request.headers.get('X-Anonymous-User-ID')
            if anonymous_id:
                return await get_or_create_anonymous_user(anonymous_id)
        return await create_anonymous_user()


async def get_or_create_anonymous_user(anonymous_id: str) -> AuthUser:
    """
    Get or create anonymous user with specific ID.
    Used when client sends X-Anonymous-User-ID header.

    Args:
        anonymous_id: UUID string from client

    Returns:
        AuthUser object with is_anonymous=True
    """
    from src.database import get_db

    try:
        with get_db() as cursor:
            # Check if anonymous user already exists
            cursor.execute("""
                SELECT id FROM users WHERE id = %s AND is_anonymous = TRUE
            """, (anonymous_id,))
            existing = cursor.fetchone()

            if existing:
                logger.debug(f"Using existing anonymous user: {anonymous_id[:8]}...")
                return AuthUser(
                    user_id=anonymous_id,
                    email=None,
                    is_anonymous=True
                )

            # Create new anonymous user with provided ID
            cursor.execute("""
                INSERT INTO users (id, email, is_anonymous, created_at)
                VALUES (%s, NULL, TRUE, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO NOTHING
                RETURNING id
            """, (anonymous_id,))
            result = cursor.fetchone()

            logger.debug(f"Created anonymous user with client ID: {anonymous_id[:8]}...")
            return AuthUser(
                user_id=anonymous_id,
                email=None,
                is_anonymous=True
            )

    except Exception as e:
        logger.warning(f"Failed to get/create anonymous user: {e}")
        # Fall back to creating new one
        return await create_anonymous_user()


async def create_anonymous_user() -> AuthUser:
    """
    Create temporary anonymous user (maintains backward compatibility).
    Anonymous users can browse and add to cart without registering.
    Generates a new random UUID.

    Returns:
        AuthUser object with is_anonymous=True
    """
    import uuid
    from src.database import get_db

    # Generate unique UUID for anonymous user
    anon_id = str(uuid.uuid4())

    # Create in database
    try:
        with get_db() as cursor:
            cursor.execute("""
                INSERT INTO users (id, email, is_anonymous, created_at)
                VALUES (%s, NULL, TRUE, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO NOTHING
                RETURNING id
            """, (anon_id,))
            result = cursor.fetchone()

            if result:
                logger.debug(f"Created new anonymous user: {anon_id[:8]}...")
                return AuthUser(
                    user_id=result['id'],
                    email=None,
                    is_anonymous=True
                )
            else:
                # User already exists (conflict)
                logger.debug(f"Anonymous user already exists: {anon_id[:8]}...")
                return AuthUser(
                    user_id=anon_id,
                    email=None,
                    is_anonymous=True
                )
    except Exception as e:
        # If DB fails, still return anonymous user (graceful degradation)
        logger.warning(f"Failed to create anonymous user in DB: {e}")
        return AuthUser(
            user_id=anon_id,
            email=None,
            is_anonymous=True
        )


def require_auth(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """
    Dependency that requires authentication.
    Raises 401 if user is anonymous.

    Args:
        user: Current user from get_current_user

    Returns:
        AuthUser (only if authenticated)

    Raises:
        HTTPException: If user is anonymous
    """
    if user.is_anonymous:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user
