import os
from flask import Flask
from config import config_by_name
from app.extensions import db, login_manager

def create_app(config_name='dev'):
    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # User loader
    from app.models.user import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.clients import clients_bp
    from app.routes.assets import assets_bp
    from app.routes.licenses import licenses_bp
    from app.routes.tickets import tickets_bp
    from app.routes.settings import settings_bp
    from app.routes.maintenance import maintenance_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clients_bp, url_prefix='/clients')
    app.register_blueprint(assets_bp, url_prefix='/assets')
    app.register_blueprint(licenses_bp, url_prefix='/licenses')
    app.register_blueprint(tickets_bp, url_prefix='/tickets')
    app.register_blueprint(maintenance_bp, url_prefix='/maintenance')
    app.register_blueprint(settings_bp, url_prefix='/settings')


    # Register Context Processors
    @app.context_processor
    def inject_global_vars():
        from datetime import datetime
        return {'now': datetime.utcnow()}

    return app
