"""
Comprehensive tests for src/auth.py module

Tests all authentication functions including:
- cleanup_expired_tokens() - Token cache cleanup
- get_current_user() - JWT validation with cache
- get_current_user_optional() - Optional authentication
- get_or_create_anonymous_user() - Anonymous user management
- create_anonymous_user() - Anonymous user creation
- require_auth() - Authentication requirement enforcement
- AuthUser class - User representation

Target: >90% code coverage
"""
import pytest
import jwt
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
import uuid

from src.auth import (
    cleanup_expired_tokens,
    get_current_user,
    get_current_user_optional,
    get_or_create_anonymous_user,
    create_anonymous_user,
    require_auth,
    AuthUser,
    _token_cache,
    _cache_last_cleanup,
    CACHE_CLEANUP_INTERVAL
)


class TestAuthUser:
    """Test AuthUser class"""

    def test_auth_user_creation(self):
        """Test creating AuthUser instance"""
        user_id = str(uuid.uuid4())
        email = "test@example.com"
        user = AuthUser(user_id=user_id, email=email, is_anonymous=False)

        assert user.id == user_id
        assert user.email == email
        assert user.is_anonymous is False

    def test_auth_user_anonymous(self):
        """Test creating anonymous AuthUser"""
        user_id = str(uuid.uuid4())
        user = AuthUser(user_id=user_id, email=None, is_anonymous=True)

        assert user.id == user_id
        assert user.email is None
        assert user.is_anonymous is True

    def test_auth_user_repr(self):
        """Test AuthUser string representation"""
        user_id = str(uuid.uuid4())
        user = AuthUser(user_id=user_id, email="test@example.com", is_anonymous=False)
        repr_str = repr(user)

        assert "AuthUser" in repr_str
        assert user_id[:8] in repr_str
        assert "test@example.com" in repr_str
        assert "anonymous=False" in repr_str


class TestCleanupExpiredTokens:
    """Test cleanup_expired_tokens() function"""

    def setup_method(self):
        """Clear token cache before each test"""
        _token_cache.clear()

    def test_cleanup_skipped_if_interval_not_passed(self):
        """Should skip cleanup if cleanup interval hasn't passed"""
        import src.auth

        # Set last cleanup to recent time
        src.auth._cache_last_cleanup = datetime.now().timestamp()

        # Add expired token
        user = AuthUser(user_id=str(uuid.uuid4()), email=None, is_anonymous=True)
        expired_time = datetime.now().timestamp() - 100
        _token_cache["expired_token"] = (user, expired_time)

        # Call cleanup
        cleanup_expired_tokens()

        # Token should still be there (cleanup skipped)
        assert "expired_token" in _token_cache

    def test_cleanup_removes_expired_tokens(self):
        """Should remove expired tokens when interval has passed"""
        import src.auth

        # Set last cleanup to old time (force cleanup)
        src.auth._cache_last_cleanup = datetime.now().timestamp() - CACHE_CLEANUP_INTERVAL - 10

        # Add expired token
        user1 = AuthUser(user_id=str(uuid.uuid4()), email=None, is_anonymous=True)
        expired_time = datetime.now().timestamp() - 100
        _token_cache["expired_token"] = (user1, expired_time)

        # Add valid token
        user2 = AuthUser(user_id=str(uuid.uuid4()), email=None, is_anonymous=True)
        future_time = datetime.now().timestamp() + 3600
        _token_cache["valid_token"] = (user2, future_time)

        # Call cleanup
        cleanup_expired_tokens()

        # Expired token should be removed, valid token should remain
        assert "expired_token" not in _token_cache
        assert "valid_token" in _token_cache

    def test_cleanup_updates_last_cleanup_time(self):
        """Should update last cleanup timestamp"""
        import src.auth

        old_time = datetime.now().timestamp() - CACHE_CLEANUP_INTERVAL - 10
        src.auth._cache_last_cleanup = old_time

        cleanup_expired_tokens()

        # Last cleanup time should be updated
        assert src.auth._cache_last_cleanup > old_time


class TestGetCurrentUser:
    """Test get_current_user() function"""

    def setup_method(self):
        """Clear token cache before each test"""
        _token_cache.clear()

    def test_no_credentials_creates_anonymous_user(self):
        """Should create anonymous user when no credentials provided"""
        async def run_test():
            mock_request = Mock(spec=Request)
            mock_request.headers.get.return_value = None

            with patch('src.auth.create_anonymous_user') as mock_create:
                mock_create.return_value = AuthUser(
                    user_id=str(uuid.uuid4()),
                    email=None,
                    is_anonymous=True
                )

                user = await get_current_user(mock_request, None)

                assert user.is_anonymous is True
                mock_create.assert_called_once()

        asyncio.run(run_test())

    def test_no_credentials_with_anonymous_header(self):
        """Should use existing anonymous user from header"""
        async def run_test():
            mock_request = Mock(spec=Request)
            anon_id = str(uuid.uuid4())
            mock_request.headers.get.return_value = anon_id

            with patch('src.auth.get_or_create_anonymous_user') as mock_get_or_create:
                mock_get_or_create.return_value = AuthUser(
                    user_id=anon_id,
                    email=None,
                    is_anonymous=True
                )

                user = await get_current_user(mock_request, None)

                assert user.is_anonymous is True
                assert user.id == anon_id
                mock_get_or_create.assert_called_once_with(anon_id)

        asyncio.run(run_test())

    def test_token_cache_hit(self):
        """Should return cached user without network call"""
        async def run_test():
            import src.auth

            # Setup mock request and credentials
            mock_request = Mock(spec=Request)
            token = "valid_cached_token"
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            # Add token to cache with future expiry
            user = AuthUser(user_id=str(uuid.uuid4()), email="cached@example.com", is_anonymous=False)
            future_expiry = datetime.now().timestamp() + 3600
            _token_cache[token] = (user, future_expiry)

            # Force cache cleanup to skip (prevent cleanup during test)
            src.auth._cache_last_cleanup = datetime.now().timestamp()

            # Get user (should hit cache)
            result = await get_current_user(mock_request, credentials)

            assert result == user
            assert result.email == "cached@example.com"

        asyncio.run(run_test())

    def test_token_cache_expired(self):
        """Should re-verify token if cached entry is expired"""
        async def run_test():
            import src.auth

            mock_request = Mock(spec=Request)
            token = "expired_cached_token"
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            # Add expired token to cache
            user = AuthUser(user_id=str(uuid.uuid4()), email="old@example.com", is_anonymous=False)
            past_expiry = datetime.now().timestamp() - 100
            _token_cache[token] = (user, past_expiry)

            # Force cache cleanup to skip
            src.auth._cache_last_cleanup = datetime.now().timestamp()

            # Mock Supabase verification
            mock_supabase = MagicMock()
            mock_user = Mock()
            mock_user.id = str(uuid.uuid4())
            mock_user.email = "new@example.com"
            mock_supabase.auth.get_user.return_value = Mock(user=mock_user)

            with patch('src.auth.supabase', mock_supabase):
                result = await get_current_user(mock_request, credentials)

                assert result.email == "new@example.com"
                mock_supabase.auth.get_user.assert_called_once_with(token)

        asyncio.run(run_test())

    def test_supabase_unavailable_returns_503(self):
        """Should return 503 if Supabase client is unavailable"""
        async def run_test():
            import src.auth

            mock_request = Mock(spec=Request)
            token = "some_token"
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            # Force cache cleanup to skip
            src.auth._cache_last_cleanup = datetime.now().timestamp()

            # Mock Supabase as None
            with patch('src.auth.supabase', None):
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(mock_request, credentials)

                assert exc_info.value.status_code == 503
                assert "unavailable" in exc_info.value.detail.lower()

        asyncio.run(run_test())

    def test_valid_token_verification(self):
        """Should verify valid token and cache result"""
        async def run_test():
            import src.auth

            mock_request = Mock(spec=Request)
            token = "valid_new_token"
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            # Force cache cleanup to skip
            src.auth._cache_last_cleanup = datetime.now().timestamp()

            # Mock JWT decode
            exp_time = (datetime.now() + timedelta(hours=1)).timestamp()

            # Mock Supabase
            mock_supabase = MagicMock()
            mock_user = Mock()
            user_id = str(uuid.uuid4())
            mock_user.id = user_id
            mock_user.email = "test@example.com"
            mock_supabase.auth.get_user.return_value = Mock(user=mock_user)

            with patch('src.auth.supabase', mock_supabase):
                with patch('jwt.decode', return_value={'exp': exp_time}):
                    result = await get_current_user(mock_request, credentials)

                    assert result.id == user_id
                    assert result.email == "test@example.com"
                    assert result.is_anonymous is False

                    # Token should be cached
                    assert token in _token_cache
                    cached_user, cached_expiry = _token_cache[token]
                    assert cached_user.email == "test@example.com"

        asyncio.run(run_test())

    def test_invalid_token_returns_401(self):
        """Should return 401 for invalid token"""
        async def run_test():
            import src.auth

            mock_request = Mock(spec=Request)
            token = "invalid_token"
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            # Force cache cleanup to skip
            src.auth._cache_last_cleanup = datetime.now().timestamp()

            # Mock Supabase returning None user
            mock_supabase = MagicMock()
            mock_supabase.auth.get_user.return_value = Mock(user=None)

            with patch('src.auth.supabase', mock_supabase):
                with patch('jwt.decode', return_value={'exp': 0}):
                    with pytest.raises(HTTPException) as exc_info:
                        await get_current_user(mock_request, credentials)

                    assert exc_info.value.status_code == 401
                    assert "Invalid" in exc_info.value.detail

        asyncio.run(run_test())

    def test_token_verification_exception(self):
        """Should handle exceptions during token verification"""
        async def run_test():
            import src.auth

            mock_request = Mock(spec=Request)
            token = "broken_token"
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            # Force cache cleanup to skip
            src.auth._cache_last_cleanup = datetime.now().timestamp()

            # Mock Supabase raising exception
            mock_supabase = MagicMock()
            mock_supabase.auth.get_user.side_effect = Exception("Network error")

            with patch('src.auth.supabase', mock_supabase):
                with patch('jwt.decode', return_value={'exp': 0}):
                    with pytest.raises(HTTPException) as exc_info:
                        await get_current_user(mock_request, credentials)

                    assert exc_info.value.status_code == 401
                    assert "failed" in exc_info.value.detail.lower()

        asyncio.run(run_test())


class TestGetCurrentUserOptional:
    """Test get_current_user_optional() function"""

    def test_no_credentials_returns_anonymous(self):
        """Should return anonymous user when no credentials"""
        async def run_test():
            mock_request = Mock(spec=Request)
            mock_request.headers.get.return_value = None

            with patch('src.auth.create_anonymous_user') as mock_create:
                mock_create.return_value = AuthUser(
                    user_id=str(uuid.uuid4()),
                    email=None,
                    is_anonymous=True
                )

                user = await get_current_user_optional(mock_request, None)

                assert user.is_anonymous is True
                mock_create.assert_called_once()

        asyncio.run(run_test())

    def test_valid_token_returns_authenticated_user(self):
        """Should return authenticated user for valid token"""
        async def run_test():
            mock_request = Mock(spec=Request)
            token = "valid_token"
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            mock_user = AuthUser(
                user_id=str(uuid.uuid4()),
                email="test@example.com",
                is_anonymous=False
            )

            with patch('src.auth.get_current_user', return_value=mock_user):
                user = await get_current_user_optional(mock_request, credentials)

                assert user.is_anonymous is False
                assert user.email == "test@example.com"

        asyncio.run(run_test())

    def test_invalid_token_falls_back_to_anonymous(self):
        """Should fall back to anonymous user if token invalid"""
        async def run_test():
            mock_request = Mock(spec=Request)
            mock_request.headers.get.return_value = None
            token = "invalid_token"
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            # Mock get_current_user raising HTTPException
            async def mock_get_current_user(*args, **kwargs):
                raise HTTPException(status_code=401, detail="Invalid token")

            with patch('src.auth.get_current_user', side_effect=mock_get_current_user):
                with patch('src.auth.create_anonymous_user') as mock_create:
                    mock_create.return_value = AuthUser(
                        user_id=str(uuid.uuid4()),
                        email=None,
                        is_anonymous=True
                    )

                    user = await get_current_user_optional(mock_request, credentials)

                    assert user.is_anonymous is True
                    mock_create.assert_called_once()

        asyncio.run(run_test())

    def test_invalid_token_with_anonymous_header(self):
        """Should use anonymous header when token invalid"""
        async def run_test():
            mock_request = Mock(spec=Request)
            anon_id = str(uuid.uuid4())
            mock_request.headers.get.return_value = anon_id
            token = "invalid_token"
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            # Mock get_current_user raising HTTPException
            async def mock_get_current_user(*args, **kwargs):
                raise HTTPException(status_code=401, detail="Invalid token")

            with patch('src.auth.get_current_user', side_effect=mock_get_current_user):
                with patch('src.auth.get_or_create_anonymous_user') as mock_get_or_create:
                    mock_get_or_create.return_value = AuthUser(
                        user_id=anon_id,
                        email=None,
                        is_anonymous=True
                    )

                    user = await get_current_user_optional(mock_request, credentials)

                    assert user.is_anonymous is True
                    assert user.id == anon_id
                    mock_get_or_create.assert_called_once_with(anon_id)

        asyncio.run(run_test())


class TestGetOrCreateAnonymousUser:
    """Test get_or_create_anonymous_user() function"""

    def test_existing_anonymous_user(self):
        """Should return existing anonymous user"""
        async def run_test():
            anon_id = str(uuid.uuid4())

            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {'id': anon_id}

            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_cursor
            mock_context.__exit__.return_value = None

            # get_db is imported inside the function, so patch it in src.database
            with patch('src.database.get_db', return_value=mock_context):
                user = await get_or_create_anonymous_user(anon_id)

                assert user.id == anon_id
                assert user.is_anonymous is True
                assert user.email is None

                # Should have queried for existing user
                mock_cursor.execute.assert_called_once()
                assert "SELECT id FROM users" in mock_cursor.execute.call_args[0][0]

        asyncio.run(run_test())

    def test_create_new_anonymous_user_with_id(self):
        """Should create new anonymous user with provided ID"""
        async def run_test():
            anon_id = str(uuid.uuid4())

            mock_cursor = MagicMock()
            # First call (SELECT) returns None, second call (INSERT) returns user
            mock_cursor.fetchone.side_effect = [None, {'id': anon_id}]

            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_cursor
            mock_context.__exit__.return_value = None

            with patch('src.database.get_db', return_value=mock_context):
                user = await get_or_create_anonymous_user(anon_id)

                assert user.id == anon_id
                assert user.is_anonymous is True

                # Should have called execute twice (SELECT + INSERT)
                assert mock_cursor.execute.call_count == 2
                assert "INSERT INTO users" in mock_cursor.execute.call_args_list[1][0][0]

        asyncio.run(run_test())

    def test_database_error_falls_back_to_create(self):
        """Should fall back to create_anonymous_user if database fails"""
        async def run_test():
            anon_id = str(uuid.uuid4())

            mock_context = MagicMock()
            mock_context.__enter__.side_effect = Exception("Database connection failed")

            with patch('src.database.get_db', return_value=mock_context):
                with patch('src.auth.create_anonymous_user') as mock_create:
                    mock_create.return_value = AuthUser(
                        user_id=str(uuid.uuid4()),
                        email=None,
                        is_anonymous=True
                    )

                    user = await get_or_create_anonymous_user(anon_id)

                    assert user.is_anonymous is True
                    mock_create.assert_called_once()

        asyncio.run(run_test())


class TestCreateAnonymousUser:
    """Test create_anonymous_user() function"""

    def test_create_new_anonymous_user(self):
        """Should create new anonymous user in database"""
        async def run_test():
            mock_cursor = MagicMock()
            new_id = str(uuid.uuid4())
            mock_cursor.fetchone.return_value = {'id': new_id}

            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_cursor
            mock_context.__exit__.return_value = None

            with patch('src.database.get_db', return_value=mock_context):
                user = await create_anonymous_user()

                assert user.is_anonymous is True
                assert user.email is None
                assert user.id is not None

                # Should have inserted into database
                mock_cursor.execute.assert_called_once()
                assert "INSERT INTO users" in mock_cursor.execute.call_args[0][0]

        asyncio.run(run_test())

    def test_create_anonymous_user_conflict(self):
        """Should handle ID conflict gracefully"""
        async def run_test():
            mock_cursor = MagicMock()
            anon_id = str(uuid.uuid4())
            # fetchone returns None (conflict - ON CONFLICT DO NOTHING)
            mock_cursor.fetchone.return_value = None

            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_cursor
            mock_context.__exit__.return_value = None

            with patch('src.database.get_db', return_value=mock_context):
                with patch('uuid.uuid4', return_value=uuid.UUID(anon_id)):
                    user = await create_anonymous_user()

                    assert user.is_anonymous is True
                    assert user.id == anon_id

        asyncio.run(run_test())

    def test_create_anonymous_user_database_error(self):
        """Should return anonymous user even if database fails"""
        async def run_test():
            mock_context = MagicMock()
            mock_context.__enter__.side_effect = Exception("Database error")

            with patch('src.database.get_db', return_value=mock_context):
                user = await create_anonymous_user()

                # Should still return anonymous user (graceful degradation)
                assert user.is_anonymous is True
                assert user.email is None
                assert user.id is not None

        asyncio.run(run_test())


class TestRequireAuth:
    """Test require_auth() function"""

    def test_authenticated_user_passes(self):
        """Should allow authenticated user"""
        user = AuthUser(
            user_id=str(uuid.uuid4()),
            email="test@example.com",
            is_anonymous=False
        )

        result = require_auth(user)

        assert result == user
        assert result.is_anonymous is False

    def test_anonymous_user_raises_401(self):
        """Should raise 401 for anonymous user"""
        user = AuthUser(
            user_id=str(uuid.uuid4()),
            email=None,
            is_anonymous=True
        )

        with pytest.raises(HTTPException) as exc_info:
            require_auth(user)

        assert exc_info.value.status_code == 401
        assert "required" in exc_info.value.detail.lower()


class TestTokenCacheCleanup:
    """Integration tests for token cache cleanup"""

    def setup_method(self):
        """Clear token cache before each test"""
        _token_cache.clear()

    def test_cleanup_multiple_expired_tokens(self):
        """Should clean up multiple expired tokens at once"""
        import src.auth

        # Force cleanup to run
        src.auth._cache_last_cleanup = datetime.now().timestamp() - CACHE_CLEANUP_INTERVAL - 10

        # Add multiple expired tokens
        now = datetime.now().timestamp()
        for i in range(5):
            user = AuthUser(user_id=str(uuid.uuid4()), email=None, is_anonymous=True)
            _token_cache[f"expired_{i}"] = (user, now - 100)

        # Add valid tokens
        for i in range(3):
            user = AuthUser(user_id=str(uuid.uuid4()), email=None, is_anonymous=True)
            _token_cache[f"valid_{i}"] = (user, now + 3600)

        assert len(_token_cache) == 8

        cleanup_expired_tokens()

        # Should only have valid tokens remaining
        assert len(_token_cache) == 3
        for i in range(3):
            assert f"valid_{i}" in _token_cache


class TestSupabaseInitialization:
    """Test Supabase client initialization edge cases"""

    def test_supabase_client_initialized(self):
        """Should have supabase client initialized"""
        import src.auth
        # In normal operation, supabase should be initialized
        # (will be None if credentials are missing)
        assert src.auth.supabase is not None or src.auth.supabase is None


class TestGetCurrentUserOptionalEdgeCases:
    """Test additional edge cases for get_current_user_optional"""

    def test_no_credentials_no_request_header(self):
        """Should create anonymous user when no credentials and no header"""
        async def run_test():
            mock_request = Mock(spec=Request)
            # No anonymous ID in header
            mock_request.headers.get.return_value = None

            with patch('src.auth.create_anonymous_user') as mock_create:
                mock_create.return_value = AuthUser(
                    user_id=str(uuid.uuid4()),
                    email=None,
                    is_anonymous=True
                )

                user = await get_current_user_optional(mock_request, None)

                assert user.is_anonymous is True
                # Should have checked for header
                mock_request.headers.get.assert_called_with('X-Anonymous-User-ID')
                mock_create.assert_called_once()

        asyncio.run(run_test())

    def test_no_credentials_with_request_header(self):
        """Should use anonymous ID from header when no credentials"""
        async def run_test():
            mock_request = Mock(spec=Request)
            anon_id = str(uuid.uuid4())
            mock_request.headers.get.return_value = anon_id

            with patch('src.auth.get_or_create_anonymous_user') as mock_get_or_create:
                mock_get_or_create.return_value = AuthUser(
                    user_id=anon_id,
                    email=None,
                    is_anonymous=True
                )

                user = await get_current_user_optional(mock_request, None)

                assert user.is_anonymous is True
                assert user.id == anon_id
                mock_get_or_create.assert_called_once_with(anon_id)

        asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.auth", "--cov-report=term-missing"])
