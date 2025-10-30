/**
 * Modal management for authentication forms
 *
 * Handles showing/hiding modals and form submissions for:
 * - Login
 * - Register
 * - Forgot Password
 */

/**
 * Show a modal by ID
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
    }
}

/**
 * Close a modal by ID
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Close all modals
 */
function closeAllModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
    });
}

/**
 * Show login modal
 */
function showLoginModal() {
    closeAllModals();
    showModal('login-modal');
    // Focus on email input
    setTimeout(() => {
        const emailInput = document.getElementById('login-email');
        if (emailInput) emailInput.focus();
    }, 100);
}

/**
 * Show register modal
 */
function showRegisterModal() {
    closeAllModals();
    showModal('register-modal');
    // Focus on email input
    setTimeout(() => {
        const emailInput = document.getElementById('register-email');
        if (emailInput) emailInput.focus();
    }, 100);
}

/**
 * Show forgot password modal
 */
function showForgotPasswordModal() {
    closeAllModals();
    showModal('forgot-password-modal');
    // Focus on email input
    setTimeout(() => {
        const emailInput = document.getElementById('forgot-email');
        if (emailInput) emailInput.focus();
    }, 100);
}

/**
 * Handle login form submission
 */
async function handleLogin(event) {
    event.preventDefault();

    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    // Disable submit button
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Logging in...';

    try {
        await window.auth.signIn(email, password);
        closeModal('login-modal');
        // Clear form
        event.target.reset();
    } catch (error) {
        // Error already shown by signIn()
        console.error('Login failed:', error);
    } finally {
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

/**
 * Handle register form submission
 */
async function handleRegister(event) {
    event.preventDefault();

    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const confirm = document.getElementById('register-confirm').value;

    // Validate passwords match
    if (password !== confirm) {
        alert('Passwords do not match');
        return;
    }

    // Validate password length
    if (password.length < 6) {
        alert('Password must be at least 6 characters');
        return;
    }

    // Disable submit button
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Signing up...';

    try {
        await window.auth.signUp(email, password);
        closeModal('register-modal');
        // Clear form
        event.target.reset();
    } catch (error) {
        // Error already shown by signUp()
        console.error('Registration failed:', error);
    } finally {
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

/**
 * Handle forgot password form submission
 */
async function handleForgotPassword(event) {
    event.preventDefault();

    const email = document.getElementById('forgot-email').value;

    // Disable submit button
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending...';

    try {
        await window.auth.resetPassword(email);
        closeModal('forgot-password-modal');
        // Clear form
        event.target.reset();
    } catch (error) {
        // Error already shown by resetPassword()
        console.error('Password reset failed:', error);
    } finally {
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

// Close modal when clicking outside
window.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
});

// Close modal on Escape key
window.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeAllModals();
    }
});

// Export functions for use in HTML
window.showLoginModal = showLoginModal;
window.showRegisterModal = showRegisterModal;
window.showForgotPasswordModal = showForgotPasswordModal;
window.closeModal = closeModal;
window.handleLogin = handleLogin;
window.handleRegister = handleRegister;
window.handleForgotPassword = handleForgotPassword;
