# Supabase Auth Implementation Plan
**Project:** Wegmans Shopping App
**Date:** October 29, 2025
**Estimated Time:** 8-12 hours (including testing)
**Complexity:** Medium

**WORKING_DIRECTORY:** `.claude-work/impl-20251029-194249-19476`

---

## 🎯 Executive Summary

**Goal:** Replace anonymous UUID-based sessions with Supabase Auth (email/password + forgot password flow).

**Key Benefits:**
- ✅ Secure, industry-standard authentication
- ✅ Built-in email verification & password reset
- ✅ Zero maintenance (Supabase handles security updates)
- ✅ Scalable to 50,000 users on free tier
- ✅ Ready for social login (Google, GitHub) in future
- ✅ Mobile app compatible
- ✅ Row Level Security (database-level auth)

**Key Challenges:**
- Migrating `user_id` from BIGINT to UUID
- Preserving anonymous user data on registration
- Maintaining backward compatibility during rollout

---

## 📊 Current State vs Target State

### Current Architecture
```
┌─────────────┐
│   Browser   │
│  (cookie:   │
│ user_id=123)│
└──────┬──────┘
       │ HTTP + Cookie
       ▼
┌─────────────────┐
│   FastAPI       │
│  (middleware    │
│   reads cookie) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL     │
│  user_id BIGINT │
│  (no auth)      │
└─────────────────┘
```

### Target Architecture
```
┌─────────────────┐
│   Browser       │
│  (localStorage: │
│   JWT token)    │
└────────┬────────┘
         │ Authorization: Bearer <token>
         ▼
┌─────────────────┐
│   FastAPI       │
│  (verify JWT    │
│   via Supabase) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL     │
│  user_id UUID   │
│  + RLS policies │
└─────────────────┘
         ▲
         │
┌─────────────────┐
│  Supabase Auth  │
│  (JWT issuer)   │
└─────────────────┘
```

---

## 🗄️ Phase 1: Database Schema Migration

### 1.1 User ID Type Migration (BIGINT → UUID)

**Current Schema:**
```sql
users.id BIGINT
shopping_carts.user_id BIGINT
saved_lists.user_id BIGINT
recipes.user_id BIGINT
frequent_items (no user_id - global table)
```

**Challenge:** Supabase Auth returns UUID, but we're using BIGINT.

**Solution Options:**

#### Option A: Migrate to UUID (RECOMMENDED)
**Pros:** Clean, aligns with Supabase Auth, modern standard
**Cons:** Requires data migration, more complex

**Steps:**
1. Add new `user_uuid` UUID column to all tables
2. Generate UUIDs for existing users
3. Update foreign keys
4. Drop old `user_id` columns
5. Rename `user_uuid` → `user_id`

#### Option B: Store UUID as string in BIGINT
**Pros:** No schema changes
**Cons:** Hacky, loses type safety, future problems

**Decision: Go with Option A** (proper UUID migration)

### 1.2 Migration SQL

```sql
-- migrations/006_migrate_to_uuid_auth.sql

-- STEP 1: Add UUID columns
ALTER TABLE users ADD COLUMN user_uuid UUID DEFAULT gen_random_uuid();
ALTER TABLE shopping_carts ADD COLUMN user_uuid UUID;
ALTER TABLE saved_lists ADD COLUMN user_uuid UUID;
ALTER TABLE recipes ADD COLUMN user_uuid UUID;

-- STEP 2: Create UUID mapping for existing users
UPDATE users SET user_uuid = gen_random_uuid() WHERE user_uuid IS NULL;

-- STEP 3: Populate foreign key UUIDs
UPDATE shopping_carts sc
SET user_uuid = u.user_uuid
FROM users u
WHERE sc.user_id = u.id;

UPDATE saved_lists sl
SET user_uuid = u.user_uuid
FROM users u
WHERE sl.user_id = u.id;

UPDATE recipes r
SET user_uuid = u.user_uuid
FROM users u
WHERE r.user_id = u.id;

-- STEP 4: Make UUID columns NOT NULL
ALTER TABLE users ALTER COLUMN user_uuid SET NOT NULL;
ALTER TABLE shopping_carts ALTER COLUMN user_uuid SET NOT NULL;
ALTER TABLE saved_lists ALTER COLUMN user_uuid SET NOT NULL;
ALTER TABLE recipes ALTER COLUMN user_uuid SET NOT NULL;

-- STEP 5: Add unique constraint to user_uuid
ALTER TABLE users ADD CONSTRAINT users_user_uuid_unique UNIQUE (user_uuid);

-- STEP 6: Drop old foreign keys and create new ones
ALTER TABLE shopping_carts DROP CONSTRAINT IF EXISTS shopping_carts_user_id_fkey;
ALTER TABLE saved_lists DROP CONSTRAINT IF EXISTS saved_lists_user_id_fkey;
ALTER TABLE recipes DROP CONSTRAINT IF EXISTS recipes_user_id_fkey;

-- STEP 7: Drop old BIGINT id/user_id columns
ALTER TABLE shopping_carts DROP COLUMN user_id;
ALTER TABLE saved_lists DROP COLUMN user_id;
ALTER TABLE recipes DROP COLUMN user_id;
ALTER TABLE users DROP COLUMN id;

-- STEP 8: Rename user_uuid → id (for users table)
ALTER TABLE users RENAME COLUMN user_uuid TO id;
ALTER TABLE shopping_carts RENAME COLUMN user_uuid TO user_id;
ALTER TABLE saved_lists RENAME COLUMN user_uuid TO user_id;
ALTER TABLE recipes RENAME COLUMN user_uuid TO user_id;

-- STEP 9: Set users.id as PRIMARY KEY
ALTER TABLE users ADD PRIMARY KEY (id);

-- STEP 10: Recreate foreign keys
ALTER TABLE shopping_carts
ADD CONSTRAINT shopping_carts_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE saved_lists
ADD CONSTRAINT saved_lists_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE recipes
ADD CONSTRAINT recipes_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- STEP 11: Add email columns to users table
ALTER TABLE users ADD COLUMN email VARCHAR(255) UNIQUE;
ALTER TABLE users ADD COLUMN is_anonymous BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN supabase_user_id UUID UNIQUE; -- Link to auth.users
ALTER TABLE users ADD COLUMN migrated_at TIMESTAMP;

-- STEP 12: Create index on email
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_supabase_user_id ON users(supabase_user_id);

-- STEP 13: Add unique constraint on shopping_carts (user_id, product_name)
-- This prevents duplicate items per user
ALTER TABLE shopping_carts DROP CONSTRAINT IF EXISTS shopping_carts_user_id_product_name_key;
ALTER TABLE shopping_carts ADD CONSTRAINT shopping_carts_user_id_product_name_key
UNIQUE (user_id, product_name);
```

### 1.3 Rollback Plan

```sql
-- migrations/006_rollback.sql
-- WARNING: This will lose UUID data! Only use if migration fails.

-- Recreate BIGINT id column
ALTER TABLE users ADD COLUMN id_bigint BIGSERIAL PRIMARY KEY;
-- ... (reverse all steps)
```

**Better approach:** Test migration on staging/dev database first!

---

## 🔐 Phase 2: Configure Supabase Auth

### 2.1 Enable Auth in Supabase Dashboard

1. Go to https://supabase.com/dashboard/project/YOUR_PROJECT
2. Navigate to **Authentication** → **Providers**
3. Enable **Email** provider
4. Configure settings:
   - ✅ Enable email confirmations
   - ✅ Secure email change
   - ✅ Double confirm email changes
   - Set **Site URL**: `https://your-app.com` (or localhost for dev)
   - Set **Redirect URLs**: `https://your-app.com/**` (wildcard for all paths)

### 2.2 Email Templates

Customize email templates in **Authentication** → **Email Templates**:

**Confirm Signup:**
```html
<h2>Welcome to Wegmans Shopping!</h2>
<p>Click the link below to confirm your email:</p>
<p><a href="{{ .ConfirmationURL }}">Confirm Email</a></p>
```

**Reset Password:**
```html
<h2>Reset Your Password</h2>
<p>Click the link below to reset your password:</p>
<p><a href="{{ .ConfirmationURL }}">Reset Password</a></p>
<p>If you didn't request this, ignore this email.</p>
```

### 2.3 Get API Credentials

From **Settings** → **API**:
- `SUPABASE_URL`: Your project URL
- `SUPABASE_ANON_KEY`: Public anonymous key (safe for frontend)
- `SUPABASE_SERVICE_KEY`: Secret key (backend only, NEVER expose!)

### 2.4 Environment Variables

Update `.env`:
```bash
# Existing
DATABASE_URL=postgresql://...

# NEW - Add these
SUPABASE_URL=https://pisakkjmyeobvcgxbmhk.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...  # Public key
SUPABASE_SERVICE_KEY=eyJhbGc...  # SECRET - backend only!
```

Update `config/settings.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Existing
    DATABASE_URL: str
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False

    # NEW - Supabase Auth
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 🔧 Phase 3: Backend Authentication Layer

### 3.1 Install Dependencies

```bash
# Add to requirements.txt
supabase>=2.0.0  # Official Python client
pyjwt>=2.8.0     # JWT decoding (for token verification)
```

```bash
pip install supabase pyjwt
```

### 3.2 Create Auth Module

**File:** `src/auth.py` (NEW)

```python
"""
Authentication module using Supabase Auth
"""
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from typing import Optional
import jwt
from config.settings import settings

# Initialize Supabase client (backend - uses service key)
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY
)

# Security scheme for JWT bearer tokens
security = HTTPBearer(auto_error=False)

class AuthUser:
    """Authenticated user object"""
    def __init__(self, user_id: str, email: str, is_anonymous: bool = False):
        self.id = user_id  # UUID from Supabase
        self.email = email
        self.is_anonymous = is_anonymous

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> AuthUser:
    """
    Get current authenticated user from JWT token.
    Falls back to anonymous user if no token provided.
    """
    # If no token, create anonymous user
    if not credentials:
        return await create_anonymous_user()

    token = credentials.credentials

    try:
        # Verify JWT token with Supabase
        response = supabase.auth.get_user(token)
        user = response.user

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        # Return authenticated user
        return AuthUser(
            user_id=str(user.id),
            email=user.email,
            is_anonymous=False
        )

    except Exception as e:
        # Token invalid or expired
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> AuthUser:
    """
    Get current user, or return anonymous user if not authenticated.
    Does NOT raise 401 - used for endpoints that work with/without auth.
    """
    if not credentials:
        return await create_anonymous_user()

    try:
        return await get_current_user(credentials)
    except HTTPException:
        # Token invalid - fall back to anonymous
        return await create_anonymous_user()

async def create_anonymous_user() -> AuthUser:
    """
    Create temporary anonymous user (maintains backward compatibility).
    Anonymous users can browse and add to cart without registering.
    """
    import uuid
    from src.database import get_db

    # Generate unique UUID for anonymous user
    anon_id = str(uuid.uuid4())

    # Create in database
    try:
        with get_db() as cursor:
            cursor.execute("""
                INSERT INTO users (id, email, is_anonymous)
                VALUES (%s, NULL, TRUE)
                ON CONFLICT (id) DO NOTHING
                RETURNING id
            """, (anon_id,))
            result = cursor.fetchone()

            if result:
                return AuthUser(
                    user_id=result['id'],
                    email=None,
                    is_anonymous=True
                )
            else:
                # User already exists (conflict)
                return AuthUser(
                    user_id=anon_id,
                    email=None,
                    is_anonymous=True
                )
    except Exception as e:
        # If DB fails, still return anonymous user (graceful degradation)
        return AuthUser(
            user_id=anon_id,
            email=None,
            is_anonymous=True
        )

def require_auth(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """
    Dependency that requires authentication.
    Raises 401 if user is anonymous.
    """
    if user.is_anonymous:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user
```

### 3.3 Create Auth API Endpoints

**File:** `src/api/auth.py` (NEW)

```python
"""
Authentication API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from src.auth import supabase, get_current_user, AuthUser
from src.database import get_db
from typing import Optional

router = APIRouter()

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
    Sends verification email automatically.
    """
    try:
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

        # Create user in our database
        with get_db() as cursor:
            cursor.execute("""
                INSERT INTO users (id, email, is_anonymous, supabase_user_id)
                VALUES (%s, %s, FALSE, %s)
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

        return AuthResponse(
            user_id=str(user.id),
            email=user.email,
            access_token=session.access_token,
            refresh_token=session.refresh_token
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/auth/signin", response_model=AuthResponse)
async def sign_in(request: SignInRequest):
    """Login with email/password"""
    try:
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

        return AuthResponse(
            user_id=str(user.id),
            email=user.email,
            access_token=session.access_token,
            refresh_token=session.refresh_token
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

@router.post("/auth/signout")
async def sign_out(user: AuthUser = Depends(get_current_user)):
    """Sign out current user"""
    try:
        supabase.auth.sign_out()
        return {"message": "Signed out successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/auth/forgot-password")
async def forgot_password(request: PasswordResetRequest):
    """
    Send password reset email.
    Supabase sends email automatically with reset link.
    """
    try:
        supabase.auth.reset_password_email(request.email)
        return {"message": "Password reset email sent"}
    except Exception as e:
        # Don't reveal if email exists (security best practice)
        return {"message": "If that email exists, a reset link has been sent"}

@router.post("/auth/reset-password")
async def reset_password(
    request: PasswordUpdateRequest,
    user: AuthUser = Depends(get_current_user)
):
    """
    Update password (called after clicking reset link).
    User must be authenticated via reset token.
    """
    try:
        supabase.auth.update_user({
            "password": request.new_password
        })
        return {"message": "Password updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/auth/resend-verification")
async def resend_verification(request: PasswordResetRequest):
    """Resend email verification"""
    try:
        # Supabase doesn't have direct resend API, use password reset as workaround
        supabase.auth.reset_password_email(request.email)
        return {"message": "Verification email sent"}
    except Exception as e:
        return {"message": "If that email exists, verification has been sent"}

@router.get("/auth/me")
async def get_me(user: AuthUser = Depends(get_current_user)):
    """Get current user info"""
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
    """
    with get_db() as cursor:
        # Migrate shopping cart
        cursor.execute("""
            UPDATE shopping_carts
            SET user_id = %s
            WHERE user_id = %s
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

        # Delete anonymous user record
        cursor.execute("""
            DELETE FROM users WHERE id = %s
        """, (anonymous_id,))
```

### 3.4 Update App to Include Auth Router

**File:** `app.py`

```python
# Add to imports
from src.api import auth  # NEW

# Add to router includes (after line 37)
app.include_router(auth.router, prefix="/api", tags=["auth"])  # NEW
```

### 3.5 Update Existing Endpoints to Use Auth

Example for cart endpoint:

**File:** `src/api/cart.py`

```python
# OLD
from fastapi import APIRouter, HTTPException, Request

@router.get("/cart")
async def get_cart(request: Request):
    user_id = request.state.user_id  # OLD WAY
    return get_user_cart(user_id)

# NEW
from fastapi import APIRouter, HTTPException, Depends
from src.auth import get_current_user_optional, AuthUser  # NEW

@router.get("/cart")
async def get_cart(user: AuthUser = Depends(get_current_user_optional)):
    # Works for both authenticated and anonymous users
    return get_user_cart(user.id)
```

**Repeat for all endpoints in:**
- `src/api/cart.py`
- `src/api/lists.py`
- `src/api/recipes.py`

### 3.6 Remove Old Session Middleware

**File:** `app.py`

```python
# DELETE this entire middleware (lines 49-84)
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    # ... DELETE ALL THIS ...
```

---

## 🛡️ Phase 4: Row Level Security (RLS) Policies

### 4.1 What is RLS?

Row Level Security = Database-level authorization. Instead of checking permissions in code, the database automatically filters rows based on the authenticated user.

**Benefits:**
- Can't forget to check permissions (enforced at DB level)
- Works for direct DB queries (not just API)
- Simpler backend code
- More secure (defense in depth)

### 4.2 Enable RLS

```sql
-- migrations/007_enable_rls.sql

-- Enable RLS on all user tables
ALTER TABLE shopping_carts ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_lists ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_list_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipes ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipe_items ENABLE ROW LEVEL SECURITY;

-- Note: frequent_items is global (no user_id), so no RLS needed
-- Note: search_cache is global, no RLS needed
```

### 4.3 Create RLS Policies

```sql
-- Policy: Users can only access their own shopping cart
CREATE POLICY "Users can manage own cart"
ON shopping_carts
FOR ALL
USING (user_id = auth.uid()::uuid)
WITH CHECK (user_id = auth.uid()::uuid);

-- Policy: Users can only access their own saved lists
CREATE POLICY "Users can manage own lists"
ON saved_lists
FOR ALL
USING (user_id = auth.uid()::uuid)
WITH CHECK (user_id = auth.uid()::uuid);

-- Policy: Users can only access items in their own lists
CREATE POLICY "Users can manage own list items"
ON saved_list_items
FOR ALL
USING (
    list_id IN (
        SELECT id FROM saved_lists WHERE user_id = auth.uid()::uuid
    )
);

-- Policy: Users can only access their own recipes
CREATE POLICY "Users can manage own recipes"
ON recipes
FOR ALL
USING (user_id = auth.uid()::uuid)
WITH CHECK (user_id = auth.uid()::uuid);

-- Policy: Users can only access items in their own recipes
CREATE POLICY "Users can manage own recipe items"
ON recipe_items
FOR ALL
USING (
    recipe_id IN (
        SELECT id FROM recipes WHERE user_id = auth.uid()::uuid
    )
);
```

### 4.4 Configure Supabase JWT Authentication

For RLS to work, Supabase needs to know which user is making the request.

**Option 1: Use Supabase Client (Recommended)**

```python
# Instead of raw psycopg2, use Supabase client for authenticated queries
from supabase import create_client

# In database.py, add alternative method:
def get_db_authenticated(access_token: str):
    """Get database connection with user context for RLS"""
    supabase = create_client(settings.SUPABASE_URL, access_token)
    return supabase.table('shopping_carts')  # etc
```

**Option 2: Set JWT in PostgreSQL session (Advanced)**

```python
# Before each query, set the JWT
cursor.execute("SET request.jwt.claims = %s", (jwt_claims_json,))
```

**For simplicity, we'll use Option 1** for RLS-protected operations.

### 4.5 Update Database Functions to Support RLS

**File:** `src/database.py`

Add RLS-aware versions:

```python
def get_user_cart_rls(access_token: str) -> List[Dict]:
    """Get cart using RLS (authenticated query)"""
    supabase = create_client(settings.SUPABASE_URL, access_token)
    response = supabase.table('shopping_carts').select('*').execute()
    return response.data

# Or, keep using psycopg2 but pass user_id explicitly (RLS as defense in depth)
# Backend code filters by user_id, RLS prevents direct DB access bypassing API
```

**Decision:** Since we're using psycopg2 and FastAPI already filters by user_id, **RLS acts as secondary defense**. We'll keep existing psycopg2 code, but RLS prevents:
- Direct database queries bypassing API
- SQL injection returning other users' data
- Admin panel mistakes

---

## 🎨 Phase 5: Frontend Authentication UI

### 5.1 Install Supabase JS Client

**File:** `frontend/index.html`

```html
<!-- Add before closing </body> tag -->
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script src="/js/auth.js"></script>
```

### 5.2 Create Auth JavaScript Module

**File:** `frontend/js/auth.js` (NEW)

```javascript
/**
 * Authentication module using Supabase
 */

// Initialize Supabase client (uses ANON key - safe for frontend)
const supabase = window.supabase.createClient(
    'YOUR_SUPABASE_URL',  // Replace with actual URL
    'YOUR_SUPABASE_ANON_KEY'  // Replace with actual key
);

// Auth state management
let currentUser = null;
let accessToken = null;

/**
 * Initialize auth on page load
 */
async function initAuth() {
    // Check if user is already logged in
    const { data: { session } } = await supabase.auth.getSession();

    if (session) {
        currentUser = session.user;
        accessToken = session.access_token;
        updateUIForAuthState(true);
    } else {
        updateUIForAuthState(false);
    }

    // Listen for auth state changes
    supabase.auth.onAuthStateChange((event, session) => {
        console.log('Auth state changed:', event);

        if (session) {
            currentUser = session.user;
            accessToken = session.access_token;
            updateUIForAuthState(true);

            // If user just signed up/in, migrate anonymous data
            if (event === 'SIGNED_IN' || event === 'INITIAL_SESSION') {
                migrateAnonymousData();
            }
        } else {
            currentUser = null;
            accessToken = null;
            updateUIForAuthState(false);
        }
    });
}

/**
 * Update UI based on auth state
 */
function updateUIForAuthState(isAuthenticated) {
    const authButtons = document.getElementById('auth-buttons');
    const userMenu = document.getElementById('user-menu');

    if (isAuthenticated) {
        authButtons.style.display = 'none';
        userMenu.style.display = 'block';
        document.getElementById('user-email').textContent = currentUser.email;
    } else {
        authButtons.style.display = 'block';
        userMenu.style.display = 'none';
    }
}

/**
 * Sign up new user
 */
async function signUp(email, password) {
    try {
        const { data, error } = await supabase.auth.signUp({
            email: email,
            password: password
        });

        if (error) throw error;

        alert('Sign up successful! Check your email to confirm your account.');
        return data;
    } catch (error) {
        console.error('Sign up error:', error);
        alert(`Sign up failed: ${error.message}`);
        throw error;
    }
}

/**
 * Sign in existing user
 */
async function signIn(email, password) {
    try {
        const { data, error } = await supabase.auth.signInWithPassword({
            email: email,
            password: password
        });

        if (error) throw error;

        return data;
    } catch (error) {
        console.error('Sign in error:', error);
        alert(`Sign in failed: ${error.message}`);
        throw error;
    }
}

/**
 * Sign out current user
 */
async function signOut() {
    try {
        const { error } = await supabase.auth.signOut();
        if (error) throw error;

        // Clear cart and reload page
        window.location.reload();
    } catch (error) {
        console.error('Sign out error:', error);
        alert(`Sign out failed: ${error.message}`);
    }
}

/**
 * Send password reset email
 */
async function resetPassword(email) {
    try {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
            redirectTo: `${window.location.origin}/reset-password`
        });

        if (error) throw error;

        alert('Password reset email sent! Check your inbox.');
    } catch (error) {
        console.error('Password reset error:', error);
        alert(`Password reset failed: ${error.message}`);
    }
}

/**
 * Update password (after clicking reset link)
 */
async function updatePassword(newPassword) {
    try {
        const { error } = await supabase.auth.updateUser({
            password: newPassword
        });

        if (error) throw error;

        alert('Password updated successfully!');
        window.location.href = '/';
    } catch (error) {
        console.error('Password update error:', error);
        alert(`Password update failed: ${error.message}`);
    }
}

/**
 * Migrate anonymous user data to authenticated account
 */
async function migrateAnonymousData() {
    const anonymousUserId = localStorage.getItem('anonymous_user_id');

    if (!anonymousUserId) return;

    try {
        // Call backend migration endpoint
        await fetchWithAuth('/api/auth/migrate', {
            method: 'POST',
            body: JSON.stringify({
                anonymous_user_id: anonymousUserId
            })
        });

        // Clear anonymous ID
        localStorage.removeItem('anonymous_user_id');

        console.log('Anonymous data migrated successfully');
    } catch (error) {
        console.error('Migration failed:', error);
    }
}

/**
 * Helper: Fetch with authentication token
 */
async function fetchWithAuth(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    // Add auth token if available
    if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
    }

    return fetch(url, {
        ...options,
        headers
    });
}

/**
 * Get current user
 */
function getCurrentUser() {
    return currentUser;
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return currentUser !== null;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initAuth);

// Export functions for use in other modules
window.auth = {
    signUp,
    signIn,
    signOut,
    resetPassword,
    updatePassword,
    getCurrentUser,
    isAuthenticated,
    fetchWithAuth
};
```

### 5.3 Update Main App to Use Auth

**File:** `frontend/js/app.js`

Update all `fetch()` calls to use `auth.fetchWithAuth()`:

```javascript
// OLD
const response = await fetch('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ search_term: query })
});

// NEW
const response = await auth.fetchWithAuth('/api/search', {
    method: 'POST',
    body: JSON.stringify({ search_term: query })
});
```

### 5.4 Create Login/Register UI

**File:** `frontend/index.html`

Add auth UI to header:

```html
<header>
    <h1>Wegmans Shopping List</h1>

    <!-- Auth buttons (shown when not logged in) -->
    <div id="auth-buttons">
        <button onclick="showLoginModal()" class="btn-primary">Log In</button>
        <button onclick="showRegisterModal()" class="btn-secondary">Sign Up</button>
    </div>

    <!-- User menu (shown when logged in) -->
    <div id="user-menu" style="display: none;">
        <span id="user-email"></span>
        <button onclick="auth.signOut()" class="btn-secondary">Sign Out</button>
    </div>
</header>

<!-- Login Modal -->
<div id="login-modal" class="modal">
    <div class="modal-content">
        <span class="close" onclick="closeModal('login-modal')">&times;</span>
        <h2>Log In</h2>
        <form onsubmit="handleLogin(event)">
            <input type="email" id="login-email" placeholder="Email" required>
            <input type="password" id="login-password" placeholder="Password" required>
            <button type="submit" class="btn-primary">Log In</button>
        </form>
        <p>
            <a href="#" onclick="showForgotPasswordModal()">Forgot password?</a>
        </p>
        <p>
            Don't have an account?
            <a href="#" onclick="showRegisterModal()">Sign up</a>
        </p>
    </div>
</div>

<!-- Register Modal -->
<div id="register-modal" class="modal">
    <div class="modal-content">
        <span class="close" onclick="closeModal('register-modal')">&times;</span>
        <h2>Sign Up</h2>
        <form onsubmit="handleRegister(event)">
            <input type="email" id="register-email" placeholder="Email" required>
            <input type="password" id="register-password" placeholder="Password (min 6 chars)" required minlength="6">
            <input type="password" id="register-confirm" placeholder="Confirm Password" required>
            <button type="submit" class="btn-primary">Sign Up</button>
        </form>
        <p>
            Already have an account?
            <a href="#" onclick="showLoginModal()">Log in</a>
        </p>
    </div>
</div>

<!-- Forgot Password Modal -->
<div id="forgot-password-modal" class="modal">
    <div class="modal-content">
        <span class="close" onclick="closeModal('forgot-password-modal')">&times;</span>
        <h2>Reset Password</h2>
        <form onsubmit="handleForgotPassword(event)">
            <input type="email" id="forgot-email" placeholder="Email" required>
            <button type="submit" class="btn-primary">Send Reset Link</button>
        </form>
    </div>
</div>
```

### 5.5 Add Modal JavaScript

**File:** `frontend/js/modals.js` (NEW)

```javascript
/**
 * Modal management for auth forms
 */

function showModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function showLoginModal() {
    closeAllModals();
    showModal('login-modal');
}

function showRegisterModal() {
    closeAllModals();
    showModal('register-modal');
}

function showForgotPasswordModal() {
    closeAllModals();
    showModal('forgot-password-modal');
}

function closeAllModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
    });
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
};

async function handleLogin(event) {
    event.preventDefault();

    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
        await auth.signIn(email, password);
        closeModal('login-modal');
    } catch (error) {
        // Error already shown in signIn()
    }
}

async function handleRegister(event) {
    event.preventDefault();

    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const confirm = document.getElementById('register-confirm').value;

    if (password !== confirm) {
        alert('Passwords do not match');
        return;
    }

    try {
        await auth.signUp(email, password);
        closeModal('register-modal');
    } catch (error) {
        // Error already shown in signUp()
    }
}

async function handleForgotPassword(event) {
    event.preventDefault();

    const email = document.getElementById('forgot-email').value;

    try {
        await auth.resetPassword(email);
        closeModal('forgot-password-modal');
    } catch (error) {
        // Error already shown in resetPassword()
    }
}
```

### 5.6 Add Modal CSS

**File:** `frontend/css/auth.css` (NEW)

```css
/* Modal styling */
.modal {
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0,0,0,0.5);
}

.modal-content {
    background-color: white;
    margin: 10% auto;
    padding: 30px;
    border-radius: 8px;
    width: 90%;
    max-width: 400px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.modal-content h2 {
    margin-top: 0;
    margin-bottom: 20px;
}

.modal-content input {
    width: 100%;
    padding: 12px;
    margin: 10px 0;
    border: 1px solid #ddd;
    border-radius: 4px;
    box-sizing: border-box;
}

.modal-content button {
    width: 100%;
    margin-top: 10px;
}

.modal-content p {
    text-align: center;
    margin-top: 15px;
}

.modal-content a {
    color: #ff6200;
    text-decoration: none;
}

.modal-content a:hover {
    text-decoration: underline;
}

.close {
    float: right;
    font-size: 28px;
    font-weight: bold;
    color: #aaa;
    cursor: pointer;
}

.close:hover {
    color: #000;
}

/* Auth buttons in header */
#auth-buttons {
    display: flex;
    gap: 10px;
}

#user-menu {
    display: flex;
    align-items: center;
    gap: 15px;
}

#user-email {
    font-weight: 500;
}
```

### 5.7 Create Password Reset Page

**File:** `frontend/reset-password.html` (NEW)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Password - Wegmans Shopping</title>
    <link rel="stylesheet" href="/css/styles.css">
    <link rel="stylesheet" href="/css/auth.css">
</head>
<body>
    <div class="container">
        <h1>Reset Password</h1>
        <form onsubmit="handlePasswordReset(event)">
            <input type="password" id="new-password" placeholder="New Password (min 6 chars)" required minlength="6">
            <input type="password" id="confirm-password" placeholder="Confirm Password" required>
            <button type="submit" class="btn-primary">Update Password</button>
        </form>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <script src="/js/auth.js"></script>
    <script>
        async function handlePasswordReset(event) {
            event.preventDefault();

            const newPassword = document.getElementById('new-password').value;
            const confirm = document.getElementById('confirm-password').value;

            if (newPassword !== confirm) {
                alert('Passwords do not match');
                return;
            }

            try {
                await auth.updatePassword(newPassword);
            } catch (error) {
                // Error already shown in updatePassword()
            }
        }
    </script>
</body>
</html>
```

---

## 🔄 Phase 6: Anonymous User Migration

### 6.1 Strategy

**Goal:** Don't lose user's cart/lists when they sign up.

**Flow:**
1. User browses anonymously → Cart stored with anonymous UUID
2. User decides to register → Sign up form appears
3. After successful sign up → Migrate all data from anonymous ID to authenticated ID
4. Delete anonymous user record

### 6.2 Track Anonymous Users in Frontend

**File:** `frontend/js/auth.js`

Update initialization:

```javascript
async function initAuth() {
    // Check if user is already logged in
    const { data: { session } } = await supabase.auth.getSession();

    if (session) {
        currentUser = session.user;
        accessToken = session.access_token;
        updateUIForAuthState(true);
    } else {
        // User not authenticated - track as anonymous
        let anonymousId = localStorage.getItem('anonymous_user_id');
        if (!anonymousId) {
            // Generate anonymous UUID (first visit)
            anonymousId = crypto.randomUUID();
            localStorage.setItem('anonymous_user_id', anonymousId);
        }
        updateUIForAuthState(false);
    }

    // ... rest of function
}
```

### 6.3 Send Anonymous ID on Sign Up

**File:** `frontend/js/auth.js`

Update `signUp()`:

```javascript
async function signUp(email, password) {
    try {
        // Get anonymous ID if exists
        const anonymousId = localStorage.getItem('anonymous_user_id');

        const { data, error } = await supabase.auth.signUp({
            email: email,
            password: password,
            options: {
                data: {
                    anonymous_user_id: anonymousId  // Pass to backend
                }
            }
        });

        if (error) throw error;

        // Migrate data immediately after signup
        if (anonymousId) {
            await migrateAnonymousData(anonymousId);
        }

        alert('Sign up successful! Check your email to confirm your account.');
        return data;
    } catch (error) {
        console.error('Sign up error:', error);
        alert(`Sign up failed: ${error.message}`);
        throw error;
    }
}
```

### 6.4 Backend Migration Endpoint

Already created in Phase 3.3 (`migrate_anonymous_data()` function).

### 6.5 Handle Edge Cases

**Case 1: User signs up on Device A, logs in on Device B**
- Device B has different anonymous data
- Solution: Don't migrate on login, only on signup

**Case 2: User has both anonymous and authenticated data**
- Merge carts (sum quantities)
- Solution: Use `ON CONFLICT` with `DO UPDATE`

```sql
-- In migration function
INSERT INTO shopping_carts (user_id, product_name, quantity, ...)
SELECT %s, product_name, quantity, ...
FROM shopping_carts
WHERE user_id = %s
ON CONFLICT (user_id, product_name) DO UPDATE SET
    quantity = shopping_carts.quantity + EXCLUDED.quantity;
```

---

## 🧪 Phase 7: Testing

### 7.1 Manual Testing Checklist

**Authentication Flows:**
- [ ] Sign up with new email
- [ ] Check email for verification link
- [ ] Click verification link
- [ ] Log in with verified account
- [ ] Log out
- [ ] Log in again
- [ ] Request password reset
- [ ] Click reset link in email
- [ ] Update password
- [ ] Log in with new password

**Anonymous User Migration:**
- [ ] Add items to cart (not logged in)
- [ ] Sign up
- [ ] Verify cart items still present
- [ ] Check anonymous user deleted from DB

**Authorization:**
- [ ] Try accessing cart without token (should work - anonymous)
- [ ] Try accessing another user's data (should fail - RLS)
- [ ] Try direct database query (should respect RLS)

**Edge Cases:**
- [ ] Sign up with existing email (should error)
- [ ] Log in with wrong password (should error)
- [ ] Reset password for non-existent email (should not reveal)
- [ ] Expired JWT token (should re-authenticate)
- [ ] Multiple tabs (session sync)

### 7.2 Automated Testing

**File:** `tests/test_auth.py` (NEW)

```python
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_sign_up():
    response = client.post("/api/auth/signup", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_sign_in():
    # Assumes user already exists
    response = client.post("/api/auth/signin", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_invalid_credentials():
    response = client.post("/api/auth/signin", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_protected_endpoint_without_auth():
    response = client.get("/api/auth/me")
    # Should work but return anonymous user
    assert response.status_code == 200
    assert response.json()["is_anonymous"] == True

def test_protected_endpoint_with_auth():
    # Get token
    login = client.post("/api/auth/signin", json={
        "email": "test@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]

    # Access protected endpoint
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    assert response.json()["is_anonymous"] == False
```

### 7.3 Security Testing

**SQL Injection:**
```python
# Try injecting SQL in email field
response = client.post("/api/auth/signin", json={
    "email": "test@example.com'; DROP TABLE users; --",
    "password": "anything"
})
# Should fail safely (parameterized queries)
```

**JWT Tampering:**
```python
# Try modifying JWT token
fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake"
response = client.get(
    "/api/auth/me",
    headers={"Authorization": f"Bearer {fake_token}"}
)
assert response.status_code == 401
```

**RLS Bypass:**
```sql
-- Try accessing another user's cart directly in psql
SET request.jwt.claims = '{"sub": "user-1-uuid"}';
SELECT * FROM shopping_carts WHERE user_id = 'user-2-uuid';
-- Should return empty (RLS blocks)
```

---

## 🚀 Phase 8: Deployment

### 8.1 Environment Variables (Production)

**Render Dashboard:**
```
DATABASE_URL=postgresql://...
SUPABASE_URL=https://pisakkjmyeobvcgxbmhk.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJ...  (public key)
SUPABASE_SERVICE_KEY=eyJhbGciOiJ...  (SECRET!)
```

### 8.2 Frontend Configuration

**File:** `frontend/js/auth.js`

Replace hardcoded values with environment variables:

```javascript
// Option 1: Serve config from backend
fetch('/api/config')
    .then(res => res.json())
    .then(config => {
        const supabase = window.supabase.createClient(
            config.supabaseUrl,
            config.supabaseAnonKey
        );
    });

// Backend endpoint:
@router.get("/config")
async def get_config():
    return {
        "supabaseUrl": settings.SUPABASE_URL,
        "supabaseAnonKey": settings.SUPABASE_ANON_KEY
    }
```

### 8.3 Database Migration on Production

**⚠️ CRITICAL: Backup first!**

```bash
# SSH into Render or run from local (connected to prod DB)
python3 << 'EOF'
import subprocess, psycopg2

# Get production DB URL from Render env vars
conn_str = "PRODUCTION_DATABASE_URL"

# Run migration
with open('migrations/006_migrate_to_uuid_auth.sql', 'r') as f:
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute(f.read())
    conn.commit()

print("Migration complete!")
EOF
```

### 8.4 Gradual Rollout (Optional)

**Feature Flag Approach:**

```python
# config/settings.py
class Settings(BaseSettings):
    AUTH_ENABLED: bool = False  # Toggle auth on/off

# app.py
if settings.AUTH_ENABLED:
    app.include_router(auth.router, prefix="/api", tags=["auth"])
else:
    # Use old cookie-based auth
    @app.middleware("http")
    async def session_middleware(request: Request, call_next):
        # Old middleware...
```

**Rollout Plan:**
1. Deploy with `AUTH_ENABLED=False` (no changes)
2. Run database migration (no impact, new columns unused)
3. Deploy with `AUTH_ENABLED=True` (auth live!)
4. Monitor errors for 24 hours
5. If issues: rollback by setting `AUTH_ENABLED=False`

### 8.5 Post-Deployment Checklist

- [ ] Sign up flow works
- [ ] Email verification emails arrive
- [ ] Password reset emails arrive
- [ ] RLS policies enforced
- [ ] No errors in Render logs
- [ ] Anonymous users can still browse
- [ ] Authenticated users see their data only
- [ ] Migration preserves existing users' data

---

## 🛠️ Phase 9: Maintenance & Monitoring

### 9.1 Monitor Supabase Auth

**Supabase Dashboard → Authentication:**
- Total users
- Monthly Active Users (MAU)
- Sign-ups per day
- Failed login attempts

### 9.2 Monitor Backend

**Render Logs:**
```bash
# Watch for auth errors
grep "401 Unauthorized" logs
grep "Authentication failed" logs
```

### 9.3 Email Deliverability

**Supabase → Project Settings → Email:**
- Check email bounce rate
- Verify SPF/DKIM configured
- Consider custom SMTP (e.g., Resend) for better deliverability

### 9.4 Security Updates

**Supabase handles:**
- JWT token security
- Password hashing
- Email verification
- Rate limiting

**You handle:**
- Keep `supabase` Python package updated
- Monitor CVEs in dependencies
- Regular security audits

---

## 📋 Appendix A: Alternative Approaches Considered

### A.1 DIY Auth (Passlib + JWT)
**Pros:** Full control, no vendor lock-in
**Cons:** 10+ hours implementation, ongoing maintenance, security burden
**Verdict:** Not worth it for this project

### A.2 Clerk
**Pros:** Nice UI, easy setup
**Cons:** Community Python SDK (not first-class), more expensive
**Verdict:** Good for React apps, overkill here

### A.3 WorkOS
**Pros:** Enterprise-grade, great for B2B
**Cons:** Overkill for consumer app, focused on SSO/SAML
**Verdict:** Not a fit

### A.4 PropelAuth
**Pros:** FastAPI support, B2B focused
**Cons:** More expensive, focused on orgs/teams
**Verdict:** Overkill for single-user shopping lists

### A.5 Supabase Auth ✅ (CHOSEN)
**Pros:** Already using Supabase, excellent Python SDK, free tier, modern patterns
**Cons:** Vendor lock-in (but can export data)
**Verdict:** Perfect fit

---

## 📋 Appendix B: Migration Rollback Plan

### If Things Go Wrong

**Scenario 1: Migration fails partway**
```sql
-- Rollback script (migrations/006_rollback.sql)
BEGIN;

-- Restore old BIGINT columns
ALTER TABLE users ADD COLUMN id_old BIGSERIAL;
-- ... (reverse all changes)

-- Verify data integrity
SELECT COUNT(*) FROM users;

COMMIT;
```

**Scenario 2: Auth breaks in production**
```python
# Quick fix: disable auth feature flag
AUTH_ENABLED=False

# Deploy
git revert HEAD
git push
```

**Scenario 3: Data loss detected**
```bash
# Restore from backup
pg_restore -d wegmans_shopping backup.dump

# Re-deploy old version
git checkout <previous-commit>
```

---

## 📋 Appendix C: Cost Analysis

### Free Tier Limits

**Supabase:**
- 50,000 MAU (Monthly Active Users)
- Unlimited API requests
- 500 MB database
- Email auth included

**Email (via Supabase):**
- Verification emails: Unlimited
- Password reset emails: Unlimited
- Note: May have rate limits, but sufficient for small apps

**Estimated Monthly Cost for 1,000 users:**
- Supabase: $0 (within free tier)
- Render (existing): $7/month (already paying)
- Total: $7/month (no increase)

**When to Upgrade:**
- \>50,000 users → Supabase Pro ($25/month)
- Need custom domain → Supabase Pro
- Need advanced security → Supabase Pro

---

## 📋 Appendix D: Future Enhancements

### Post-Launch Features (Phase 10+)

**Social Login:**
```javascript
// Add Google/GitHub login (2 clicks in Supabase dashboard)
await supabase.auth.signInWithOAuth({ provider: 'google' });
```

**Magic Links (Passwordless):**
```javascript
await supabase.auth.signInWithOtp({ email });
```

**Multi-Factor Authentication:**
```javascript
await supabase.auth.mfa.enroll({ factorType: 'totp' });
```

**User Profile Management:**
- Change email
- Change password (already implemented)
- Delete account
- Export data (GDPR compliance)

**Session Management:**
- View active sessions
- Revoke sessions
- Device history

---

## 🎯 Implementation Timeline

### Estimated Hours by Phase

| Phase | Task | Estimated Time |
|-------|------|----------------|
| 1 | Database schema migration | 2 hours |
| 2 | Configure Supabase Auth | 1 hour |
| 3 | Backend auth layer | 3 hours |
| 4 | RLS policies | 1 hour |
| 5 | Frontend auth UI | 3 hours |
| 6 | Anonymous migration | 2 hours |
| 7 | Testing | 3 hours |
| 8 | Deployment | 2 hours |
| **Total** | | **17 hours** |

### Recommended Schedule

**Week 1:**
- Day 1: Phase 1 (Database migration) + Phase 2 (Supabase config)
- Day 2: Phase 3 (Backend auth)
- Day 3: Phase 4 (RLS) + Phase 5 (Frontend UI)

**Week 2:**
- Day 4: Phase 6 (Migration logic) + Phase 7 (Testing)
- Day 5: Phase 8 (Deployment) + monitoring
- Day 6-7: Buffer for fixes/polish

---

## ✅ Success Criteria

### Minimum Viable Auth (MVA)

- ✅ Users can register with email/password
- ✅ Users receive verification email
- ✅ Users can log in
- ✅ Users can reset password
- ✅ Anonymous cart data migrates on signup
- ✅ RLS prevents unauthorized access
- ✅ No data loss during migration

### Quality Bar

- ✅ Zero downtime deployment
- ✅ All existing features work
- ✅ Anonymous browsing still works
- ✅ Mobile responsive
- ✅ Clear error messages
- ✅ Email deliverability >95%
- ✅ Page load time <2 seconds

---

## 📞 Support Resources

### Documentation
- Supabase Auth: https://supabase.com/docs/guides/auth
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- Supabase Python: https://github.com/supabase-community/supabase-py

### Community
- Supabase Discord: https://discord.supabase.com
- FastAPI Discord: https://discord.gg/fastapi

### Emergency Contacts
- Supabase Support: support@supabase.io
- Database issues: Check Render dashboard

---

## 🎉 Conclusion

This implementation plan provides a **production-ready authentication system** using **modern best practices** (JWT, RLS, Auth-as-a-Service).

**Key Takeaways:**
1. Supabase Auth is the right choice for 2025 (actively maintained, modern patterns)
2. UUID migration is necessary but straightforward
3. RLS provides defense-in-depth security
4. Anonymous user migration ensures zero data loss
5. Total implementation: ~17 hours including testing

**Next Steps:**
1. Review this plan with stakeholders
2. Backup production database
3. Start with Phase 1 on development environment
4. Test thoroughly before production deployment

**Ready to implement?** Let's start with Phase 1! 🚀
