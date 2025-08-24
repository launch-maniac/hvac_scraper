"""
Google Workspace SSO Integration for HVAC Scraper
Allows your sales team to login with their Google Workspace accounts
"""

import os
import json
from functools import wraps
from flask import session, request, jsonify, redirect, url_for, render_template_string
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import google.auth.exceptions

class GoogleWorkspaceSSO:
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        # Configuration
        app.config.setdefault('GOOGLE_CLIENT_ID', os.environ.get('GOOGLE_CLIENT_ID'))
        app.config.setdefault('GOOGLE_CLIENT_SECRET', os.environ.get('GOOGLE_CLIENT_SECRET'))
        app.config.setdefault('GOOGLE_WORKSPACE_DOMAIN', os.environ.get('GOOGLE_WORKSPACE_DOMAIN'))
        app.config.setdefault('ALLOWED_USERS', os.environ.get('ALLOWED_USERS', '').split(','))
        
        self.client_id = app.config['GOOGLE_CLIENT_ID']
        self.workspace_domain = app.config['GOOGLE_WORKSPACE_DOMAIN']
        self.allowed_users = [user.strip() for user in app.config['ALLOWED_USERS'] if user.strip()]
        
        # Register routes
        app.add_url_rule('/auth/google', 'google_auth', self.google_auth, methods=['GET'])
        app.add_url_rule('/auth/google/callback', 'google_callback', self.google_callback, methods=['POST'])
        app.add_url_rule('/login', 'login', self.login_page, methods=['GET'])
        app.add_url_rule('/logout', 'logout', self.logout, methods=['POST'])
    
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
        """Check if user is authenticated"""
        return session.get('authenticated', False) and session.get('user_email')
    
    def login_page(self):
        """Show Google Workspace login page"""
        if self.is_authenticated():
            return redirect('/')
        
        return render_template_string(GOOGLE_LOGIN_TEMPLATE, 
                                    client_id=self.client_id,
                                    workspace_domain=self.workspace_domain)
    
    def google_auth(self):
        """Handle Google OAuth redirect"""
        # This is handled by the frontend JavaScript
        return redirect(url_for('login'))
    
    def google_callback(self):
        """Handle Google OAuth callback"""
        try:
            # Get the ID token from the request
            data = request.get_json()
            if not data or 'credential' not in data:
                return jsonify({'success': False, 'error': 'No credential provided'}), 400
            
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                data['credential'], 
                google_requests.Request(), 
                self.client_id
            )
            
            # Verify the token is from Google
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                return jsonify({'success': False, 'error': 'Invalid token issuer'}), 400
            
            user_email = idinfo['email']
            user_name = idinfo.get('name', user_email)
            user_domain = user_email.split('@')[1] if '@' in user_email else ''
            
            # Check domain restriction
            if self.workspace_domain and user_domain != self.workspace_domain:
                return jsonify({
                    'success': False, 
                    'error': f'Only {self.workspace_domain} accounts are allowed'
                }), 403
            
            # Check user allowlist
            if self.allowed_users and user_email not in self.allowed_users:
                return jsonify({
                    'success': False, 
                    'error': 'Your account is not authorized to access this system'
                }), 403
            
            # Create session
            session['authenticated'] = True
            session['user_email'] = user_email
            session['user_name'] = user_name
            session['auth_method'] = 'google'
            session.permanent = True
            
            return jsonify({'success': True, 'redirect': '/'})
            
        except google.auth.exceptions.GoogleAuthError as e:
            return jsonify({'success': False, 'error': 'Invalid Google token'}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': 'Authentication failed'}), 500
    
    def logout(self):
        """Handle logout"""
        session.clear()
        return jsonify({'success': True, 'redirect': '/login'})

# Google Workspace login template
GOOGLE_LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HVAC Scraper - Google Workspace Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
    <script src="https://accounts.google.com/gsi/client" async defer></script>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
    <div class="max-w-md w-full space-y-8 p-8">
        <div class="text-center">
            <div class="flex justify-center mb-4">
                <i data-lucide="shield-check" class="h-12 w-12 text-blue-600"></i>
            </div>
            <h2 class="text-3xl font-bold text-gray-900">HVAC Business Scraper</h2>
            <p class="mt-2 text-sm text-gray-600">Sign in with your Google Workspace account</p>
            {% if workspace_domain %}
            <p class="mt-1 text-xs text-blue-600">@{{ workspace_domain }} accounts only</p>
            {% endif %}
        </div>
        
        <div class="bg-white rounded-lg shadow-md p-6">
            <div id="error-message" class="hidden mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                <div class="flex">
                    <i data-lucide="alert-circle" class="h-5 w-5 text-red-400 mr-2"></i>
                    <div id="error-text" class="text-sm text-red-700"></div>
                </div>
            </div>
            
            <div class="space-y-6">
                <div class="text-center">
                    <div id="g_id_onload"
                         data-client_id="{{ client_id }}"
                         data-callback="handleCredentialResponse"
                         data-auto_prompt="false">
                    </div>
                    <div class="g_id_signin"
                         data-type="standard"
                         data-size="large"
                         data-theme="outline"
                         data-text="sign_in_with"
                         data-shape="rectangular"
                         data-logo_alignment="left">
                    </div>
                </div>
                
                <div class="text-center">
                    <div id="loading" class="hidden">
                        <i data-lucide="loader" class="h-6 w-6 animate-spin mx-auto text-blue-600"></i>
                        <p class="mt-2 text-sm text-gray-600">Signing you in...</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="text-center text-xs text-gray-500">
            <p>Secure access with your Google Workspace account</p>
            <p class="mt-1">Contact your administrator if you need access</p>
        </div>
    </div>

    <script>
        // Initialize Lucide icons
        lucide.createIcons();
        
        // Handle Google Sign-In response
        function handleCredentialResponse(response) {
            showLoading(true);
            hideError();
            
            fetch('/auth/google/callback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    credential: response.credential
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = data.redirect || '/';
                } else {
                    showError(data.error || 'Authentication failed');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showError('Network error. Please try again.');
            })
            .finally(() => {
                showLoading(false);
            });
        }
        
        function showError(message) {
            const errorDiv = document.getElementById('error-message');
            const errorText = document.getElementById('error-text');
            errorText.textContent = message;
            errorDiv.classList.remove('hidden');
            lucide.createIcons();
        }
        
        function hideError() {
            const errorDiv = document.getElementById('error-message');
            errorDiv.classList.add('hidden');
        }
        
        function showLoading(show) {
            const loadingDiv = document.getElementById('loading');
            if (show) {
                loadingDiv.classList.remove('hidden');
            } else {
                loadingDiv.classList.add('hidden');
            }
            lucide.createIcons();
        }
        
        // Handle errors from Google Sign-In
        window.addEventListener('error', function(e) {
            if (e.message && e.message.includes('gsi')) {
                showError('Google Sign-In failed to load. Please refresh the page.');
            }
        });
    </script>
</body>
</html>
'''

# Configuration helper
def setup_google_workspace_sso():
    """
    Helper function to set up Google Workspace SSO
    Call this instead of SimpleAuth in your main.py
    """
    print("""
    🔧 Google Workspace SSO Setup Required:
    
    1. Go to Google Cloud Console (console.cloud.google.com)
    2. Create a new project or select existing one
    3. Enable Google+ API
    4. Create OAuth 2.0 credentials:
       - Application type: Web application
       - Authorized redirect URIs: https://yourdomain.com/auth/google/callback
    5. Set environment variables:
       export GOOGLE_CLIENT_ID="your-client-id"
       export GOOGLE_CLIENT_SECRET="your-client-secret"
       export GOOGLE_WORKSPACE_DOMAIN="yourdomain.com"
       export ALLOWED_USERS="user1@yourdomain.com,user2@yourdomain.com"
    
    6. Update requirements.txt:
       google-auth==2.17.3
       google-auth-oauthlib==1.0.0
    """)

if __name__ == "__main__":
    setup_google_workspace_sso()

