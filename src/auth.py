"""
Authentication module for HVAC Scraper
Provides simple login protection for personal use
"""

import os
import hashlib
from functools import wraps
from flask import session, request, jsonify, redirect, url_for, render_template_string
from datetime import datetime, timedelta

class SimpleAuth:
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        # Set default configuration
        app.config.setdefault('SECRET_KEY', os.environ.get('SECRET_KEY', 'your-secret-key-change-this'))
        app.config.setdefault('LOGIN_USERNAME', os.environ.get('LOGIN_USERNAME', 'admin'))
        app.config.setdefault('LOGIN_PASSWORD', os.environ.get('LOGIN_PASSWORD', 'password123'))
        app.config.setdefault('SESSION_TIMEOUT_HOURS', 24)  # 24 hour sessions
        
        # Hash the password for security
        self.username = app.config['LOGIN_USERNAME']
        self.password_hash = self._hash_password(app.config['LOGIN_PASSWORD'])
        self.session_timeout = timedelta(hours=app.config['SESSION_TIMEOUT_HOURS'])
        
        # Register routes
        app.add_url_rule('/login', 'login', self.login_page, methods=['GET', 'POST'])
        app.add_url_rule('/logout', 'logout', self.logout, methods=['POST'])
        app.add_url_rule('/auth/check', 'auth_check', self.check_auth, methods=['GET'])
    
    def _hash_password(self, password):
        """Hash password with salt for security"""
        salt = "hvac_scraper_salt_2024"  # Static salt for simplicity
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def login_required(self, f):
        """Decorator to require login for routes"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.is_authenticated():
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required', 'redirect': '/login'}), 401
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    
    def is_authenticated(self):
        """Check if user is authenticated and session is valid"""
        if 'authenticated' not in session or not session['authenticated']:
            return False
        
        # Check session timeout
        if 'login_time' in session:
            login_time = datetime.fromisoformat(session['login_time'])
            if datetime.now() - login_time > self.session_timeout:
                session.clear()
                return False
        
        return True
    
    def login_page(self):
        """Handle login page and authentication"""
        if request.method == 'GET':
            # Show login form
            return render_template_string(LOGIN_TEMPLATE)
        
        # Handle login POST
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validate credentials
        if username == self.username and self._hash_password(password) == self.password_hash:
            session['authenticated'] = True
            session['username'] = username
            session['login_time'] = datetime.now().isoformat()
            session.permanent = True
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': '/'})
            return redirect('/')
        
        # Invalid credentials
        error_msg = 'Invalid username or password'
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 401
        
        return render_template_string(LOGIN_TEMPLATE, error=error_msg)
    
    def logout(self):
        """Handle logout"""
        session.clear()
        return jsonify({'success': True, 'redirect': '/login'})
    
    def check_auth(self):
        """API endpoint to check authentication status"""
        return jsonify({
            'authenticated': self.is_authenticated(),
            'username': session.get('username') if self.is_authenticated() else None
        })

# Login page template
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HVAC Scraper - Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
    <div class="max-w-md w-full space-y-8 p-8">
        <div class="text-center">
            <div class="flex justify-center mb-4">
                <i data-lucide="shield-check" class="h-12 w-12 text-blue-600"></i>
            </div>
            <h2 class="text-3xl font-bold text-gray-900">HVAC Business Scraper</h2>
            <p class="mt-2 text-sm text-gray-600">Please sign in to access the system</p>
        </div>
        
        <div class="bg-white rounded-lg shadow-md p-6">
            {% if error %}
            <div class="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                <div class="flex">
                    <i data-lucide="alert-circle" class="h-5 w-5 text-red-400 mr-2"></i>
                    <div class="text-sm text-red-700">{{ error }}</div>
                </div>
            </div>
            {% endif %}
            
            <form id="loginForm" method="POST" class="space-y-6">
                <div>
                    <label for="username" class="block text-sm font-medium text-gray-700 mb-2">
                        Username
                    </label>
                    <input type="text" id="username" name="username" required
                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                           placeholder="Enter your username">
                </div>
                
                <div>
                    <label for="password" class="block text-sm font-medium text-gray-700 mb-2">
                        Password
                    </label>
                    <input type="password" id="password" name="password" required
                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                           placeholder="Enter your password">
                </div>
                
                <div>
                    <button type="submit" id="loginBtn"
                            class="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors">
                        <span id="loginText">Sign In</span>
                        <i id="loginSpinner" data-lucide="loader" class="h-4 w-4 animate-spin ml-2 hidden"></i>
                    </button>
                </div>
            </form>
        </div>
        
        <div class="text-center text-xs text-gray-500">
            <p>Secure access to your HVAC business data</p>
        </div>
    </div>

    <script>
        // Initialize Lucide icons
        lucide.createIcons();
        
        // Handle form submission
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const loginBtn = document.getElementById('loginBtn');
            const loginText = document.getElementById('loginText');
            const loginSpinner = document.getElementById('loginSpinner');
            
            // Show loading state
            loginBtn.disabled = true;
            loginText.textContent = 'Signing in...';
            loginSpinner.classList.remove('hidden');
            
            try {
                const formData = new FormData(this);
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        username: formData.get('username'),
                        password: formData.get('password')
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    window.location.href = result.redirect || '/';
                } else {
                    // Show error
                    showError(result.error || 'Login failed');
                }
            } catch (error) {
                showError('Network error. Please try again.');
            } finally {
                // Reset button state
                loginBtn.disabled = false;
                loginText.textContent = 'Sign In';
                loginSpinner.classList.add('hidden');
            }
        });
        
        function showError(message) {
            // Remove existing error
            const existingError = document.querySelector('.error-message');
            if (existingError) {
                existingError.remove();
            }
            
            // Create new error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message mb-4 p-3 bg-red-50 border border-red-200 rounded-md';
            errorDiv.innerHTML = `
                <div class="flex">
                    <i data-lucide="alert-circle" class="h-5 w-5 text-red-400 mr-2"></i>
                    <div class="text-sm text-red-700">${message}</div>
                </div>
            `;
            
            // Insert before form
            const form = document.getElementById('loginForm');
            form.parentNode.insertBefore(errorDiv, form);
            
            // Re-initialize icons
            lucide.createIcons();
        }
        
        // Focus on username field
        document.getElementById('username').focus();
    </script>
</body>
</html>
'''

