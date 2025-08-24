"""
Team Management System for HVAC Scraper
Supports multiple users with different permission levels
"""

import json
import os
import hashlib
from datetime import datetime
from functools import wraps
from flask import session, request, jsonify, redirect, url_for, render_template_string

class TeamManager:
    def __init__(self, app=None):
        self.app = app
        self.users_file = 'team_users.json'
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        # Configuration
        app.config.setdefault('SECRET_KEY', os.environ.get('SECRET_KEY', 'change-this-secret-key'))
        app.config.setdefault('SESSION_TIMEOUT_HOURS', 8)
        
        # Initialize users file
        self.init_users_file()
        
        # Register routes
        app.add_url_rule('/login', 'login', self.login_page, methods=['GET', 'POST'])
        app.add_url_rule('/logout', 'logout', self.logout, methods=['POST'])
        app.add_url_rule('/admin/users', 'manage_users', self.manage_users, methods=['GET', 'POST'])
        app.add_url_rule('/admin/users/<int:user_id>', 'edit_user', self.edit_user, methods=['PUT', 'DELETE'])
    
    def init_users_file(self):
        """Initialize users file with default admin user"""
        if not os.path.exists(self.users_file):
            default_users = {
                "1": {
                    "username": "admin",
                    "email": "admin@company.com",
                    "password_hash": self._hash_password("hvac2024!"),
                    "role": "admin",
                    "permissions": ["create", "view", "download", "manage", "admin"],
                    "created_at": datetime.now().isoformat(),
                    "last_login": None,
                    "active": True
                }
            }
            self.save_users(default_users)
    
    def load_users(self):
        """Load users from JSON file"""
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_users(self, users):
        """Save users to JSON file"""
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=2)
    
    def _hash_password(self, password):
        """Hash password with salt"""
        salt = "hvac_scraper_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def login_required(self, permissions=None):
        """Decorator to require login and optionally specific permissions"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self.is_authenticated():
                    if request.is_json or request.path.startswith('/api/'):
                        return jsonify({'error': 'Authentication required', 'redirect': '/login'}), 401
                    return redirect(url_for('login'))
                
                # Check permissions if specified
                if permissions:
                    user_permissions = session.get('permissions', [])
                    required_perms = permissions if isinstance(permissions, list) else [permissions]
                    if not any(perm in user_permissions for perm in required_perms):
                        return jsonify({'error': 'Insufficient permissions'}), 403
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def admin_required(self, f):
        """Decorator to require admin permissions"""
        return self.login_required(['admin'])(f)
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        return session.get('authenticated', False) and session.get('user_id')
    
    def get_current_user(self):
        """Get current user information"""
        if not self.is_authenticated():
            return None
        
        users = self.load_users()
        user_id = str(session.get('user_id'))
        return users.get(user_id)
    
    def login_page(self):
        """Handle login page and authentication"""
        if request.method == 'GET':
            if self.is_authenticated():
                return redirect('/')
            return render_template_string(TEAM_LOGIN_TEMPLATE)
        
        # Handle login POST
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validate credentials
        users = self.load_users()
        user = None
        user_id = None
        
        for uid, user_data in users.items():
            if (user_data['username'] == username and 
                user_data['active'] and
                self._hash_password(password) == user_data['password_hash']):
                user = user_data
                user_id = uid
                break
        
        if user:
            # Update last login
            user['last_login'] = datetime.now().isoformat()
            users[user_id] = user
            self.save_users(users)
            
            # Create session
            session['authenticated'] = True
            session['user_id'] = user_id
            session['username'] = user['username']
            session['email'] = user['email']
            session['role'] = user['role']
            session['permissions'] = user['permissions']
            session.permanent = True
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': '/'})
            return redirect('/')
        
        # Invalid credentials
        error_msg = 'Invalid username or password'
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 401
        
        return render_template_string(TEAM_LOGIN_TEMPLATE, error=error_msg)
    
    def logout(self):
        """Handle logout"""
        session.clear()
        return jsonify({'success': True, 'redirect': '/login'})
    
    def manage_users(self):
        """Admin page for managing users"""
        if request.method == 'GET':
            users = self.load_users()
            return render_template_string(USER_MANAGEMENT_TEMPLATE, users=users)
        
        # Handle user creation
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'sales')
        
        if not all([username, email, password]):
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        
        users = self.load_users()
        
        # Check if username or email already exists
        for user_data in users.values():
            if user_data['username'] == username:
                return jsonify({'success': False, 'error': 'Username already exists'}), 400
            if user_data['email'] == email:
                return jsonify({'success': False, 'error': 'Email already exists'}), 400
        
        # Define role permissions
        role_permissions = {
            'admin': ['create', 'view', 'download', 'manage', 'admin'],
            'manager': ['create', 'view', 'download', 'manage'],
            'sales': ['create', 'view', 'download'],
            'viewer': ['view', 'download']
        }
        
        # Create new user
        new_user_id = str(max([int(uid) for uid in users.keys()], default=0) + 1)
        users[new_user_id] = {
            'username': username,
            'email': email,
            'password_hash': self._hash_password(password),
            'role': role,
            'permissions': role_permissions.get(role, ['view']),
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'active': True
        }
        
        self.save_users(users)
        return jsonify({'success': True, 'message': 'User created successfully'})
    
    def edit_user(self, user_id):
        """Edit or delete a user"""
        users = self.load_users()
        user_id_str = str(user_id)
        
        if user_id_str not in users:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        if request.method == 'DELETE':
            # Don't allow deleting the last admin
            admin_count = sum(1 for u in users.values() if 'admin' in u.get('permissions', []) and u.get('active', False))
            if 'admin' in users[user_id_str].get('permissions', []) and admin_count <= 1:
                return jsonify({'success': False, 'error': 'Cannot delete the last admin user'}), 400
            
            del users[user_id_str]
            self.save_users(users)
            return jsonify({'success': True, 'message': 'User deleted successfully'})
        
        # Handle user update
        data = request.get_json()
        user = users[user_id_str]
        
        # Update fields
        if 'username' in data:
            user['username'] = data['username']
        if 'email' in data:
            user['email'] = data['email']
        if 'password' in data and data['password']:
            user['password_hash'] = self._hash_password(data['password'])
        if 'role' in data:
            role_permissions = {
                'admin': ['create', 'view', 'download', 'manage', 'admin'],
                'manager': ['create', 'view', 'download', 'manage'],
                'sales': ['create', 'view', 'download'],
                'viewer': ['view', 'download']
            }
            user['role'] = data['role']
            user['permissions'] = role_permissions.get(data['role'], ['view'])
        if 'active' in data:
            user['active'] = data['active']
        
        users[user_id_str] = user
        self.save_users(users)
        return jsonify({'success': True, 'message': 'User updated successfully'})

# Team login template
TEAM_LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HVAC Scraper - Team Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
    <div class="max-w-md w-full space-y-8 p-8">
        <div class="text-center">
            <div class="flex justify-center mb-4">
                <i data-lucide="users" class="h-12 w-12 text-blue-600"></i>
            </div>
            <h2 class="text-3xl font-bold text-gray-900">HVAC Business Scraper</h2>
            <p class="mt-2 text-sm text-gray-600">Team Access Portal</p>
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
            <p>Contact your administrator for account access</p>
        </div>
    </div>

    <script>
        lucide.createIcons();
        
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const loginBtn = document.getElementById('loginBtn');
            const loginText = document.getElementById('loginText');
            const loginSpinner = document.getElementById('loginSpinner');
            
            loginBtn.disabled = true;
            loginText.textContent = 'Signing in...';
            loginSpinner.classList.remove('hidden');
            
            try {
                const formData = new FormData(this);
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: formData.get('username'),
                        password: formData.get('password')
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    window.location.href = result.redirect || '/';
                } else {
                    showError(result.error || 'Login failed');
                }
            } catch (error) {
                showError('Network error. Please try again.');
            } finally {
                loginBtn.disabled = false;
                loginText.textContent = 'Sign In';
                loginSpinner.classList.add('hidden');
            }
        });
        
        function showError(message) {
            // Implementation similar to previous templates
        }
        
        document.getElementById('username').focus();
    </script>
</body>
</html>
'''

# User management template
USER_MANAGEMENT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Management - HVAC Scraper</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="max-w-6xl mx-auto p-8">
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-gray-900">User Management</h1>
            <p class="text-gray-600">Manage team access to the HVAC scraper</p>
        </div>
        
        <!-- Add User Form -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 class="text-xl font-semibold mb-4">Add New User</h2>
            <form id="addUserForm" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Username</label>
                    <input type="text" name="username" required class="w-full px-3 py-2 border border-gray-300 rounded-md">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Email</label>
                    <input type="email" name="email" required class="w-full px-3 py-2 border border-gray-300 rounded-md">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Password</label>
                    <input type="password" name="password" required class="w-full px-3 py-2 border border-gray-300 rounded-md">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Role</label>
                    <select name="role" class="w-full px-3 py-2 border border-gray-300 rounded-md">
                        <option value="sales">Sales</option>
                        <option value="manager">Manager</option>
                        <option value="admin">Admin</option>
                        <option value="viewer">Viewer</option>
                    </select>
                </div>
                <div class="md:col-span-2">
                    <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">
                        Add User
                    </button>
                </div>
            </form>
        </div>
        
        <!-- Users List -->
        <div class="bg-white rounded-lg shadow-md">
            <div class="p-6 border-b">
                <h2 class="text-xl font-semibold">Team Members</h2>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Login</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200">
                        {% for user_id, user in users.items() %}
                        <tr>
                            <td class="px-6 py-4">
                                <div>
                                    <div class="font-medium text-gray-900">{{ user.username }}</div>
                                    <div class="text-sm text-gray-500">{{ user.email }}</div>
                                </div>
                            </td>
                            <td class="px-6 py-4">
                                <span class="px-2 py-1 text-xs font-medium rounded-full 
                                    {% if user.role == 'admin' %}bg-red-100 text-red-800
                                    {% elif user.role == 'manager' %}bg-blue-100 text-blue-800
                                    {% elif user.role == 'sales' %}bg-green-100 text-green-800
                                    {% else %}bg-gray-100 text-gray-800{% endif %}">
                                    {{ user.role|title }}
                                </span>
                            </td>
                            <td class="px-6 py-4 text-sm text-gray-500">
                                {{ user.last_login or 'Never' }}
                            </td>
                            <td class="px-6 py-4">
                                <span class="px-2 py-1 text-xs font-medium rounded-full 
                                    {% if user.active %}bg-green-100 text-green-800{% else %}bg-red-100 text-red-800{% endif %}">
                                    {{ 'Active' if user.active else 'Inactive' }}
                                </span>
                            </td>
                            <td class="px-6 py-4 text-sm">
                                <button onclick="editUser({{ user_id }})" class="text-blue-600 hover:text-blue-800 mr-3">Edit</button>
                                <button onclick="deleteUser({{ user_id }})" class="text-red-600 hover:text-red-800">Delete</button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        lucide.createIcons();
        
        // Add user form submission
        document.getElementById('addUserForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const userData = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/admin/users', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(userData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    location.reload();
                } else {
                    alert(result.error);
                }
            } catch (error) {
                alert('Error adding user');
            }
        });
        
        // Edit user function
        function editUser(userId) {
            // Implementation for editing users
            alert('Edit user functionality - implement as needed');
        }
        
        // Delete user function
        async function deleteUser(userId) {
            if (!confirm('Are you sure you want to delete this user?')) return;
            
            try {
                const response = await fetch(`/admin/users/${userId}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    location.reload();
                } else {
                    alert(result.error);
                }
            } catch (error) {
                alert('Error deleting user');
            }
        }
    </script>
</body>
</html>
'''

