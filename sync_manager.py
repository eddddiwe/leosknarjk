from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import threading
import time
from datetime import datetime
import json
import os
from models import Base, User, EncryptedData
from config import Config

class SyncManager:
    def __init__(self, local_db_url, cloud_db_url=None):
        self.local_engine = create_engine(local_db_url)
        self.cloud_engine = create_engine(cloud_db_url) if cloud_db_url else None
        
        self.local_Session = sessionmaker(bind=self.local_engine)
        self.cloud_Session = sessionmaker(bind=self.cloud_engine) if cloud_db_url else None
        
        self.sync_thread = None
        self.is_running = False
        
        # Initialize cloud database if available
        if self.cloud_engine:
            Base.metadata.create_all(self.cloud_engine)
    
    def start_sync(self):
        """Start the sync process in a background thread"""
        if not self.is_running:
            self.is_running = True
            self.sync_thread = threading.Thread(target=self._sync_loop)
            self.sync_thread.daemon = True
            self.sync_thread.start()
    
    def stop_sync(self):
        """Stop the sync process"""
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join()
    
    def _sync_loop(self):
        """Main sync loop"""
        while self.is_running:
            try:
                self.sync_data()
                time.sleep(Config.SYNC_INTERVAL)
            except Exception as e:
                print(f"Sync error: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def sync_data(self):
        """Sync data between local and cloud databases"""
        if not self.cloud_engine:
            return
        
        local_session = self.local_Session()
        cloud_session = self.cloud_Session()
        
        try:
            # Sync users
            self._sync_users(local_session, cloud_session)
            
            # Sync encrypted data
            self._sync_encrypted_data(local_session, cloud_session)
            
            # Commit changes
            local_session.commit()
            cloud_session.commit()
            
        except Exception as e:
            local_session.rollback()
            cloud_session.rollback()
            raise e
        finally:
            local_session.close()
            cloud_session.close()
    
    def _sync_users(self, local_session, cloud_session):
        """Sync user data between databases"""
        # Get all users from both databases
        local_users = {u.id: u for u in local_session.query(User).all()}
        cloud_users = {u.id: u for u in cloud_session.query(User).all()}
        
        # Sync from local to cloud
        for user_id, local_user in local_users.items():
            if user_id not in cloud_users:
                # Create new user in cloud
                cloud_user = User(
                    username=local_user.username,
                    password_hash=local_user.password_hash,
                    email=local_user.email,
                    created_at=local_user.created_at
                )
                cloud_session.add(cloud_user)
            else:
                # Update existing user in cloud
                cloud_user = cloud_users[user_id]
                cloud_user.username = local_user.username
                cloud_user.password_hash = local_user.password_hash
                cloud_user.email = local_user.email
        
        # Sync from cloud to local
        for user_id, cloud_user in cloud_users.items():
            if user_id not in local_users:
                # Create new user locally
                local_user = User(
                    username=cloud_user.username,
                    password_hash=cloud_user.password_hash,
                    email=cloud_user.email,
                    created_at=cloud_user.created_at
                )
                local_session.add(local_user)
            else:
                # Update existing user locally
                local_user = local_users[user_id]
                local_user.username = cloud_user.username
                local_user.password_hash = cloud_user.password_hash
                local_user.email = cloud_user.email
    
    def _sync_encrypted_data(self, local_session, cloud_session):
        """Sync encrypted data between databases"""
        # Get all encrypted data from both databases
        local_data = {(d.id, d.user_id): d for d in local_session.query(EncryptedData).all()}
        cloud_data = {(d.id, d.user_id): d for d in cloud_session.query(EncryptedData).all()}
        
        # Sync from local to cloud
        for (data_id, user_id), local_item in local_data.items():
            if (data_id, user_id) not in cloud_data:
                # Create new data in cloud
                cloud_item = EncryptedData(
                    user_id=user_id,
                    data_type=local_item.data_type,
                    encrypted_content=local_item.encrypted_content,
                    created_at=local_item.created_at,
                    updated_at=local_item.updated_at
                )
                cloud_session.add(cloud_item)
            else:
                # Update existing data in cloud
                cloud_item = cloud_data[(data_id, user_id)]
                cloud_item.data_type = local_item.data_type
                cloud_item.encrypted_content = local_item.encrypted_content
                cloud_item.updated_at = local_item.updated_at
        
        # Sync from cloud to local
        for (data_id, user_id), cloud_item in cloud_data.items():
            if (data_id, user_id) not in local_data:
                # Create new data locally
                local_item = EncryptedData(
                    user_id=user_id,
                    data_type=cloud_item.data_type,
                    encrypted_content=cloud_item.encrypted_content,
                    created_at=cloud_item.created_at,
                    updated_at=cloud_item.updated_at
                )
                local_session.add(local_item)
            else:
                # Update existing data locally
                local_item = local_data[(data_id, user_id)]
                local_item.data_type = cloud_item.data_type
                local_item.encrypted_content = cloud_item.encrypted_content
                local_item.updated_at = cloud_item.updated_at 