import os
from app import create_app, db

env_name = os.environ.get('FLASK_ENV', 'prod')
app = create_app(env_name)

# Ensure database tables exist on startup (idempotent)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
