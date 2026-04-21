/**
 * Authentication JavaScript
 * Handles login and registration forms
 */

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
});

async function handleLogin(e) {
    e.preventDefault();

    const btn = document.getElementById('loginBtn');
    const errorDiv = document.getElementById('loginError');

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    if (!username || !password) {
        showAuthError(errorDiv, 'Please fill in all fields');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:20px;height:20px;border-width:2px;"></div> Logging in...';
    errorDiv.style.display = 'none';

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (data.success) {
            // Redirect based on role
            window.location.href = data.redirect || '/';
        } else {
            showAuthError(errorDiv, data.message);
        }
    } catch (error) {
        showAuthError(errorDiv, 'Server error. Please try again.');
        console.error('Login error:', error);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">🔓</span> Login';
    }
}

async function handleRegister(e) {
    e.preventDefault();

    const btn = document.getElementById('registerBtn');
    const errorDiv = document.getElementById('registerError');

    const full_name = document.getElementById('full_name').value.trim();
    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirm_password = document.getElementById('confirm_password').value;

    // Validation
    if (!full_name || !username || !email || !password || !confirm_password) {
        showAuthError(errorDiv, 'Please fill in all fields');
        return;
    }

    if (username.length < 3) {
        showAuthError(errorDiv, 'Username must be at least 3 characters');
        return;
    }

    if (password.length < 4) {
        showAuthError(errorDiv, 'Password must be at least 4 characters');
        return;
    }

    if (password !== confirm_password) {
        showAuthError(errorDiv, 'Passwords do not match');
        return;
    }

    if (!email.includes('@')) {
        showAuthError(errorDiv, 'Please enter a valid email');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:20px;height:20px;border-width:2px;"></div> Creating account...';
    errorDiv.style.display = 'none';

    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name, username, email, password })
        });

        const data = await response.json();

        if (data.success) {
            // Auto-login after registration
            const loginResponse = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const loginData = await loginResponse.json();

            if (loginData.success) {
                window.location.href = loginData.redirect || '/';
            } else {
                // Registration succeeded but auto-login failed, redirect to login
                window.location.href = '/login';
            }
        } else {
            showAuthError(errorDiv, data.message);
        }
    } catch (error) {
        showAuthError(errorDiv, 'Server error. Please try again.');
        console.error('Registration error:', error);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">✨</span> Create Account';
    }
}

function showAuthError(errorDiv, message) {
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';

    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}