from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import bcrypt
from models import User, EncryptedData, init_db

class DatabaseManager:
    def __init__(self, database_url="sqlite:///secure_db.sqlite"):
        self.engine = init_db(database_url)
        self.Session = sessionmaker(bind=self.engine)
    
    def create_user(self, username, password, email):
        """Create a new user with hashed password"""
        try:
            session = self.Session()
            # Hash the password
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            
            user = User(
                username=username,
                password_hash=password_hash.decode(),
                email=email
            )
            
            session.add(user)
            session.commit()
            return user
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def verify_user(self, username, password):
        """Verify user credentials"""
        try:
            session = self.Session()
            user = session.query(User).filter_by(username=username).first()
            
            if user and bcrypt.checkpw(password.encode(), user.password_hash.encode()):
                return user
            return None
        finally:
            session.close()
    
    def store_encrypted_data(self, user_id, data_type, content):
        """Store encrypted data for a user"""
        try:
            session = self.Session()
            encrypted_data = EncryptedData(
                user_id=user_id,
                data_type=data_type
            )
            encrypted_data.encrypted_content = encrypted_data.encrypt_content(content)
            
            session.add(encrypted_data)
            session.commit()
            return encrypted_data
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_encrypted_data(self, user_id, data_type=None):
        """Retrieve and decrypt data for a user"""
        try:
            session = self.Session()
            query = session.query(EncryptedData).filter_by(user_id=user_id)
            
            if data_type:
                query = query.filter_by(data_type=data_type)
            
            encrypted_data = query.all()
            return [(data.id, data.data_type, data.decrypt_content()) 
                   for data in encrypted_data]
        finally:
            session.close()
    
    def update_encrypted_data(self, data_id, new_content):
        """Update encrypted data"""
        try:
            session = self.Session()
            data = session.query(EncryptedData).get(data_id)
            
            if data:
                data.encrypted_content = data.encrypt_content(new_content)
                session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_encrypted_data(self, data_id):
        """Delete encrypted data"""
        try:
            session = self.Session()
            data = session.query(EncryptedData).get(data_id)
            
            if data:
                session.delete(data)
                session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close() 