from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv
from extensions import db  # Import db from extensions

# Load environment variables
load_dotenv()

# Get encryption key from environment or generate new one
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

Base = declarative_base()

class User(db.Model):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)
    
    # Relationships
    encrypted_data = relationship("EncryptedData", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username}>"

    # Flask-Login integration
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        # Customize this if you need to deactivate users
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

class EncryptedData(db.Model):
    __tablename__ = 'encrypted_data'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    data_type = Column(String(50), nullable=False)  # e.g., 'credit_card', 'password', 'note'
    encrypted_content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="encrypted_data")
    
    def encrypt_content(self, content):
        """Encrypt the content before storing"""
        return cipher_suite.encrypt(content.encode()).decode()
    
    def decrypt_content(self):
        """Decrypt the stored content"""
        return cipher_suite.decrypt(self.encrypted_content.encode()).decode()
    
    @property
    def decrypted_content(self):
        """Property to access decrypted content"""
        return self.decrypt_content()
    
    def __repr__(self):
        return f"<EncryptedData {self.data_type}>"

# Create database engine
# def init_db(): # This function is no longer needed
#     """Initialize the database"""
#     # with app.app_context(): # This context is no longer needed here
#     db.create_all() # This call is now in app.py 