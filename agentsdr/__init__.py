import os
from flask import Flask
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
from config import config

# Initialize extensions
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    login_manager.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from agentsdr.auth import auth_bp
    from agentsdr.orgs import orgs_bp
    from agentsdr.records import records_bp
    from agentsdr.admin import admin_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(orgs_bp, url_prefix='/orgs')
    app.register_blueprint(records_bp, url_prefix='/records')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Register main routes
    from agentsdr.main import main_bp
    app.register_blueprint(main_bp)

    # Register API blueprint (JSON endpoints for React frontend)
    from agentsdr.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    csrf.exempt(api_bp)  # API uses Bearer tokens, not CSRF

    # Enable CORS for API routes
    CORS(app, resources={r"/api/*": {
        "origins": [
            "http://localhost:3000",
            "http://localhost:5173",
            "https://2men.co",
            "https://www.2men.co",
            "https://2menco.vercel.app",
        ],
        "supports_credentials": True,
        "allow_headers": ["Content-Type", "Authorization"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    }})

    # Exempt JSON API routes from CSRF where appropriate
    try:
        from agentsdr.orgs.routes import summarize_emails
        csrf.exempt(summarize_emails)
    except Exception:
        # If import fails during certain tooling or tests, skip exemption
        pass

    # User loader for Flask-Login
    from agentsdr.auth.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    # Context processor to inject version info into all templates
    from agentsdr.utils.version import get_version_info
    @app.context_processor
    def inject_version_info():
        return {
            'app_version': get_version_info()
        }

    return app
