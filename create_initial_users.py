from app import app
from extensions import db
# from models import User # We will import this inside the context
from werkzeug.security import generate_password_hash

def create_initial_users():
    """Creates database tables and adds initial users."""
    with app.app_context():
        # Import models inside the context to ensure they are registered with db
        from models import User

        # Create all tables if they don't exist - REMOVED, schema is managed by migrations
        # db.create_all()

        # Check if users already exist to avoid duplicates
        if User.query.filter_by(username='testuser').first() is None:
            # Create a regular user
            test_user = User(
                username='testuser',
                password_hash=generate_password_hash('password'),
                email='testuser@example.com',
                is_admin=False
            )
            db.session.add(test_user)
            print("Created user: testuser")

        if User.query.filter_by(username='admin').first() is None:
            # Create an admin user
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('adminpassword'),
                email='admin@example.com',
                is_admin=True
            )
            db.session.add(admin_user)
            print("Created admin user: admin")

        db.session.commit()
        print("Initial users added to the database.")

if __name__ == '__main__':
    create_initial_users() 