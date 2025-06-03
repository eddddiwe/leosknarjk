from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate # Import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from config import config
from extensions import db # Import db from the new extensions file

# Determine the configuration environment
config_name = os.getenv('FLASK_ENV', 'default')

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(config[config_name]) # Load configuration based on environment

# Initialize extensions (SQLAlchemy is initialized in extensions.py)
db.init_app(app) # Initialize db with the app
migrate = Migrate(app, db) # Initialize Flask-Migrate
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import models and managers AFTER db is initialized with the app
from models import User, EncryptedData
from sync_manager import SyncManager
from backup_manager import BackupManager

# Initialize managers
sync_manager = SyncManager(
    local_db_url=app.config['SQLALCHEMY_DATABASE_URI'],
    cloud_db_url=app.config['CLOUD_DATABASE_URI']
)

backup_manager = BackupManager(
    db_url=app.config['SQLALCHEMY_DATABASE_URI'],
    backup_dir=app.config['BACKUP_DIR']
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            email=email
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_data = EncryptedData.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', data=user_data)

@app.route('/data/new', methods=['GET', 'POST'])
@login_required
def new_data():
    if request.method == 'POST':
        data_type = request.form.get('data_type')
        content = request.form.get('content')

        # Encrypt the content before creating the EncryptedData object
        encrypted_content_data = EncryptedData().encrypt_content(content)

        encrypted_data = EncryptedData(
            user_id=current_user.id,
            data_type=data_type,
            encrypted_content=encrypted_content_data # Use the encrypted content
        )
        db.session.add(encrypted_data)
        db.session.commit()
        
        flash('Data added successfully')
        return redirect(url_for('dashboard'))
    
    return render_template('new_data.html')

@app.route('/data/<int:data_id>')
@login_required
def view_data(data_id):
    data = EncryptedData.query.get_or_404(data_id)
    if data.user_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    return render_template('view_data.html', data=data)

@app.route('/data/<int:data_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_data(data_id):
    data = EncryptedData.query.get_or_404(data_id)
    if data.user_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data.data_type = request.form.get('data_type')
        data.content = request.form.get('content')
        data.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Data updated successfully')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_data.html', data=data)

@app.route('/data/<int:data_id>/delete', methods=['POST'])
@login_required
def delete_data(data_id):
    data = EncryptedData.query.get_or_404(data_id)
    if data.user_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    db.session.delete(data)
    db.session.commit()
    flash('Data deleted successfully')
    return redirect(url_for('dashboard'))

@app.route('/backups')
@login_required
def list_backups():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    backups = backup_manager.list_backups()
    return render_template('backups.html', backups=backups)

@app.route('/backups/create', methods=['POST'])
@login_required
def create_backup():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    backup_path = backup_manager.create_backup()
    flash(f'Backup created successfully at {backup_path}')
    return redirect(url_for('list_backups'))

@app.route('/backups/<path:backup_path>/restore', methods=['POST'])
@login_required
def restore_backup(backup_path):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    backup_manager.restore_backup(backup_path)
    flash('Backup restored successfully')
    return redirect(url_for('list_backups'))

@app.route('/backups/<path:backup_path>/delete', methods=['POST'])
@login_required
def delete_backup(backup_path):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    backup_manager.delete_backup(backup_path)
    flash('Backup deleted successfully')
    return redirect(url_for('list_backups'))

if __name__ == '__main__':
    # Get database path from configuration
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')

    # Initialize the database within the application context only if the file does not exist
    if not os.path.exists(db_path):
        with app.app_context():
            db.create_all() # Create tables directly here
        print(f"Database file created at: {db_path}")
    else:
        print(f"Database file already exists at: {db_path}")

    # Start sync and backup processes
    sync_manager.start_sync()
    backup_manager.start_backup()

    # Run the Flask app - commented out for production WSGI server
    # app.run(debug=True) 