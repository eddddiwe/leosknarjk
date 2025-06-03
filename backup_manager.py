import os
import json
import shutil
from datetime import datetime
import threading
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, EncryptedData
from config import Config

class BackupManager:
    def __init__(self, db_url, backup_dir="backups"):
        self.db_url = db_url
        self.backup_dir = backup_dir
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
        
        self.backup_thread = None
        self.is_running = False
    
    def start_backup(self):
        """Start the backup process in a background thread"""
        if not self.is_running:
            self.is_running = True
            self.backup_thread = threading.Thread(target=self._backup_loop)
            self.backup_thread.daemon = True
            self.backup_thread.start()
    
    def stop_backup(self):
        """Stop the backup process"""
        self.is_running = False
        if self.backup_thread:
            self.backup_thread.join()
    
    def _backup_loop(self):
        """Main backup loop"""
        while self.is_running:
            try:
                self.create_backup()
                time.sleep(Config.BACKUP_INTERVAL)
            except Exception as e:
                print(f"Backup error: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def create_backup(self):
        """Create a new backup of the database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}")
        
        # Create backup directory
        os.makedirs(backup_path, exist_ok=True)
        time.sleep(0.1) # Add a small delay
        
        # Backup database file if using SQLite
        if self.db_url.startswith('sqlite'):
            db_file = self.db_url.replace('sqlite:///', '')
            shutil.copy2(db_file, os.path.join(backup_path, 'database.db'))
        
        # Export data as JSON
        session = self.Session()
        try:
            # Export users
            users = session.query(User).all()
            users_data = [{
                'id': user.id,
                'username': user.username,
                'password_hash': user.password_hash,
                'email': user.email,
                'created_at': user.created_at.isoformat()
            } for user in users]
            
            with open(os.path.join(backup_path, 'users.json'), 'w') as f:
                json.dump(users_data, f, indent=2)
            
            # Export encrypted data
            encrypted_data = session.query(EncryptedData).all()
            data_items = [{
                'id': item.id,
                'user_id': item.user_id,
                'data_type': item.data_type,
                'encrypted_content': item.encrypted_content,
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat()
            } for item in encrypted_data]
            
            with open(os.path.join(backup_path, 'encrypted_data.json'), 'w') as f:
                json.dump(data_items, f, indent=2)
            
        finally:
            session.close()
        
        # Create backup metadata
        metadata = {
            'timestamp': timestamp,
            'database_url': self.db_url,
            'backup_type': 'full',
            'items': {
                'users': len(users_data),
                'encrypted_data': len(data_items)
            }
        }
        
        with open(os.path.join(backup_path, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return backup_path
    
    def restore_backup(self, backup_path):
        """Restore data from a backup"""
        if not os.path.exists(backup_path):
            raise ValueError(f"Backup path does not exist: {backup_path}")
        
        session = self.Session()
        try:
            # Restore database file if using SQLite
            if self.db_url.startswith('sqlite'):
                db_file = self.db_url.replace('sqlite:///', '')
                backup_db = os.path.join(backup_path, 'database.db')
                if os.path.exists(backup_db):
                    shutil.copy2(backup_db, db_file)
            
            # Clear existing data
            session.query(EncryptedData).delete()
            session.query(User).delete()
            
            # Restore users
            users_file = os.path.join(backup_path, 'users.json')
            if os.path.exists(users_file):
                with open(users_file, 'r') as f:
                    users_data = json.load(f)
                
                for user_data in users_data:
                    user = User(
                        username=user_data['username'],
                        password_hash=user_data['password_hash'],
                        email=user_data['email'],
                        created_at=datetime.fromisoformat(user_data['created_at'])
                    )
                    session.add(user)
            
            # Restore encrypted data
            data_file = os.path.join(backup_path, 'encrypted_data.json')
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    data_items = json.load(f)
                
                for item_data in data_items:
                    item = EncryptedData(
                        user_id=item_data['user_id'],
                        data_type=item_data['data_type'],
                        encrypted_content=item_data['encrypted_content'],
                        created_at=datetime.fromisoformat(item_data['created_at']),
                        updated_at=datetime.fromisoformat(item_data['updated_at'])
                    )
                    session.add(item)
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def list_backups(self):
        """List all available backups"""
        backups = []
        for item in os.listdir(self.backup_dir):
            backup_path = os.path.join(self.backup_dir, item)
            if os.path.isdir(backup_path):
                metadata_file = os.path.join(backup_path, 'metadata.json')
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    backups.append({
                        'path': backup_path,
                        'timestamp': metadata['timestamp'],
                        'items': metadata['items']
                    })
        
        return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
    
    def delete_backup(self, backup_path):
        """Delete a backup"""
        if not os.path.exists(backup_path):
            raise ValueError(f"Backup path does not exist: {backup_path}")
        
        shutil.rmtree(backup_path) 