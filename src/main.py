import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.models.scraping_job import ScrapingJob, BusinessData
from src.routes.user import user_bp
from src.routes.scraping import scraping_bp
from src.auth import SimpleAuth

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Security configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'hvac-scraper-secret-key-change-this-in-production')
app.config['LOGIN_USERNAME'] = os.environ.get('LOGIN_USERNAME', 'Jake')
app.config['LOGIN_PASSWORD'] = os.environ.get('LOGIN_PASSWORD', 'JakeWhitbeck')
app.config['SESSION_TIMEOUT_HOURS'] = int(os.environ.get('SESSION_TIMEOUT_HOURS', '24'))

# Enable CORS for all routes
CORS(app)

# Initialize authentication
auth = SimpleAuth(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create all database tables
with app.app_context():
    db.create_all()

# Protected routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@auth.login_required
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

# Register blueprints with authentication
app.register_blueprint(user_bp, url_prefix='/api')

# Protect scraping API routes
@scraping_bp.before_request
@auth.login_required
def protect_scraping_routes():
    pass

app.register_blueprint(scraping_bp, url_prefix='/api/scraping')

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🔐 HVAC Scraper - Secure Personal Access")
    print("="*60)
    print(f"🌐 Access URL: http://localhost:5000")
    print(f"👤 Username: {app.config['LOGIN_USERNAME']}")
    print(f"🔑 Password: {app.config['LOGIN_PASSWORD']}")
    print("="*60)
    print("💡 To change credentials, set environment variables:")
    print("   LOGIN_USERNAME=your_username")
    print("   LOGIN_PASSWORD=your_password")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
