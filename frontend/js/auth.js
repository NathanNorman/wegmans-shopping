/**
 * Authentication module using Supabase
 *
 * Provides JWT-based authentication with support for:
 * - Email/password signup and signin
 * - Password reset
 * - Anonymous user migration
 * - Token management
 */

// Initialize Supabase client immediately (uses ANON key - safe for frontend)
let supabase = null;
let currentUser = null;
let accessToken = null;
let supabaseConfig = null;

/**
 * Initialize Supabase client with credentials from backend
 */
async function initSupabase() {
    try {
        // Fetch Supabase config from backend
        const response = await fetch('/api/config');
        const config = await response.json();
        supabaseConfig = config;

        supabase = window.supabase.createClient(
            config.supabaseUrl,
            config.supabaseAnonKey
        );

        console.log('✓ Supabase client initialized');
        return true;
    } catch (error) {
        console.error('✗ Failed to initialize Supabase:', error);
        return false;
    }
}

/**
 * Pre-load auth state from localStorage (instant UI update)
 *
 * IMPORTANT: Uses Supabase SDK's getSession() instead of manual parsing.
 * This is more robust and handles format changes automatically.
 *
 * Fallback: If SDK not loaded yet, try manual parsing (backwards compatible)
 */
function preloadAuthState() {
    try {
        // Method 1: Use Supabase SDK if available (preferred)
        if (window.supabase && supabase && typeof supabase.auth?.getSession === 'function') {
            // SDK handles localStorage parsing internally
            // This is just a sync check - full async check happens in initAuth()
            console.log('✓ Supabase SDK available, will use getSession()');
            return false; // Let initAuth() handle it properly
        }

        // Method 2: Manual parsing (fallback for instant display)
        // Try to find Supabase auth token in localStorage
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('sb-') && key.endsWith('-auth-token')) {
                try {
                    const cachedData = localStorage.getItem(key);
                    if (!cachedData) continue;

                    const session = JSON.parse(cachedData);

                    // Validate session structure (defensive)
                    if (!session || typeof session !== 'object') {
                        console.warn('Invalid session format in localStorage');
                        continue;
                    }

                    if (session.access_token && session.user && session.user.id) {
                        currentUser = session.user;
                        accessToken = session.access_token;
                        updateUIForAuthState(true);
                        console.log('⚡ Auth state pre-loaded from cache (instant!)');
                        return true;
                    }
                } catch (e) {
                    console.warn('Failed to parse localStorage auth data:', e.message);
                    // Continue to next key
                }
            }
        }
    } catch (e) {
        console.error('Error in preloadAuthState:', e);
    }

    return false;
}

/**
 * Initialize auth on page load
 */
async function initAuth() {
    // INSTANT: Pre-load auth state from localStorage (no flash)
    preloadAuthState();

    // Initialize Supabase client in background
    const initialized = await initSupabase();
    if (!initialized) {
        console.error('Failed to initialize auth - using anonymous mode');
        // If we didn't preload and init failed, show logged out state
        if (!currentUser) {
            updateUIForAuthState(false);
        }
        return;
    }

    // Verify cached session with Supabase (in background)
    const { data: { session } } = await supabase.auth.getSession();

    if (session) {
        // Update with fresh session data (might be different from cache)
        currentUser = session.user;
        accessToken = session.access_token;
        updateUIForAuthState(true);
        console.log('✓ User authenticated:', currentUser.email);
    } else {
        // Session expired or invalid - clear cache and show logged out
        currentUser = null;
        accessToken = null;

        // Track as anonymous
        let anonymousId = localStorage.getItem('anonymous_user_id');
        if (!anonymousId) {
            anonymousId = crypto.randomUUID();
            localStorage.setItem('anonymous_user_id', anonymousId);
            console.log('✓ Anonymous user created:', anonymousId.substring(0, 8) + '...');
        }
        updateUIForAuthState(false);
    }

    // Listen for auth state changes
    supabase.auth.onAuthStateChange((event, session) => {
        console.log('Auth state changed:', event);

        if (session) {
            currentUser = session.user;
            accessToken = session.access_token;
            updateUIForAuthState(true);

            // Migration happens during signup on backend (via anonymous_user_id field)
            // No need to migrate on signin - that would be wrong!
            // User might be logging in from a different device with different anonymous cart
        } else {
            currentUser = null;
            accessToken = null;
            updateUIForAuthState(false);
        }
    });

    // IMPORTANT: Now that auth is initialized, tell main.js to load cart/frequent items
    if (typeof window.appReady === 'function') {
        window.appReady();
    }
}

/**
 * Update UI based on auth state
 */
function updateUIForAuthState(isAuthenticated) {
    const authButtons = document.getElementById('auth-buttons');
    const userMenu = document.getElementById('user-menu');

    if (isAuthenticated && currentUser) {
        if (authButtons) authButtons.style.display = 'none';
        if (userMenu) {
            userMenu.style.display = 'flex';
            const emailEl = document.getElementById('user-email');
            if (emailEl) emailEl.textContent = currentUser.email;
        }
    } else {
        if (authButtons) authButtons.style.display = 'flex';
        if (userMenu) userMenu.style.display = 'none';
    }
}

/**
 * Sign up new user
 */
async function signUp(email, password) {
    try {
        // Get anonymous ID if exists (for cart migration)
        const anonymousUserId = localStorage.getItem('anonymous_user_id');

        // Call OUR backend signup endpoint (not Supabase directly)
        // This handles both Supabase auth AND data migration
        const response = await fetch('/api/auth/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: email,
                password: password,
                anonymous_user_id: anonymousUserId
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Signup failed');
        }

        const data = await response.json();

        // If signup successful, update local auth state
        if (data.access_token) {
            // Store session in Supabase client
            if (supabase) {
                await supabase.auth.setSession({
                    access_token: data.access_token,
                    refresh_token: data.refresh_token
                });
            }

            // Clear anonymous ID (data has been migrated)
            localStorage.removeItem('anonymous_user_id');

            currentUser = { id: data.user_id, email: data.email };
            accessToken = data.access_token;
            updateUIForAuthState(true);
        }

        alert('Sign up successful! Check your email to confirm your account.');
        console.log('✓ User signed up:', email);
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
        if (!supabase) {
            throw new Error('Supabase not initialized');
        }

        const { data, error } = await supabase.auth.signInWithPassword({
            email: email,
            password: password
        });

        if (error) throw error;

        console.log('✓ User signed in:', email);
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
        if (!supabase) {
            throw new Error('Supabase not initialized');
        }

        const { error } = await supabase.auth.signOut();
        if (error) throw error;

        console.log('✓ User signed out');
        // Clear any cached data and reload page
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
        if (!supabase) {
            throw new Error('Supabase not initialized');
        }

        const { error } = await supabase.auth.resetPasswordForEmail(email, {
            redirectTo: `${window.location.origin}/reset-password.html`
        });

        if (error) throw error;

        alert('Password reset email sent! Check your inbox.');
        console.log('✓ Password reset email sent to:', email);
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
        if (!supabase) {
            throw new Error('Supabase not initialized');
        }

        const { error } = await supabase.auth.updateUser({
            password: newPassword
        });

        if (error) throw error;

        alert('Password updated successfully!');
        console.log('✓ Password updated');
        window.location.href = '/';
    } catch (error) {
        console.error('Password update error:', error);
        alert(`Password update failed: ${error.message}`);
    }
}

// REMOVED: migrateAnonymousData()
// Migration now happens automatically during signup via backend
// The signup endpoint accepts anonymous_user_id and migrates data server-side

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
        console.log('🔑 Sending authenticated request to:', url);
    } else {
        // For anonymous users, send the anonymous ID as a header
        const anonymousId = localStorage.getItem('anonymous_user_id');
        if (anonymousId) {
            headers['X-Anonymous-User-ID'] = anonymousId;
            console.log('👤 Sending anonymous request with ID:', anonymousId.substring(0, 8) + '...');
        } else {
            console.log('👤 Sending anonymous request (no ID)');
        }
    }

    const response = await fetch(url, {
        ...options,
        headers
    });

    // Handle 401 Unauthorized - token expired
    if (response.status === 401 && accessToken) {
        console.warn('Token expired, refreshing session...');
        // Try to refresh session
        if (supabase) {
            const { data } = await supabase.auth.refreshSession();
            if (data.session) {
                accessToken = data.session.access_token;
                // Retry request with new token
                headers['Authorization'] = `Bearer ${accessToken}`;
                return fetch(url, { ...options, headers });
            }
        }
    }

    return response;
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

/**
 * Get access token
 */
function getAccessToken() {
    return accessToken;
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuth);
} else {
    initAuth();
}

// Export functions for use in other modules
window.auth = {
    signUp,
    signIn,
    signOut,
    resetPassword,
    updatePassword,
    getCurrentUser,
    isAuthenticated,
    getAccessToken,
    fetchWithAuth
};
