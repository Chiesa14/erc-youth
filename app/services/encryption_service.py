import base64
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for handling message encryption and decryption"""
    
    def __init__(self):
        self.salt_length = 16
    
    def generate_room_key(self) -> str:
        """Generate a new encryption key for a chat room"""
        try:
            key = Fernet.generate_key()
            return base64.urlsafe_b64encode(key).decode('utf-8')
        except Exception as e:
            logger.error(f"Error generating room key: {e}")
            raise
    
    def generate_salt(self) -> bytes:
        """Generate a random salt for key derivation"""
        return secrets.token_bytes(self.salt_length)
    
    def derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password and salt"""
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            return key
        except Exception as e:
            logger.error(f"Error deriving key from password: {e}")
            raise
    
    def encrypt_message(self, message: str, room_key: str) -> Optional[str]:
        """Encrypt a message using the room's encryption key"""
        try:
            if not message or not room_key:
                return None
            
            # Decode the room key
            key_bytes = base64.urlsafe_b64decode(room_key.encode('utf-8'))
            fernet = Fernet(key_bytes)
            
            # Encrypt the message
            encrypted_message = fernet.encrypt(message.encode('utf-8'))
            
            # Return base64 encoded encrypted message
            return base64.urlsafe_b64encode(encrypted_message).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error encrypting message: {e}")
            return None
    
    def decrypt_message(self, encrypted_message: str, room_key: str) -> Optional[str]:
        """Decrypt a message using the room's encryption key"""
        try:
            if not encrypted_message or not room_key:
                return None
            
            # Decode the room key
            key_bytes = base64.urlsafe_b64decode(room_key.encode('utf-8'))
            fernet = Fernet(key_bytes)
            
            # Decode the encrypted message
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_message.encode('utf-8'))
            
            # Decrypt the message
            decrypted_message = fernet.decrypt(encrypted_bytes)
            
            return decrypted_message.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error decrypting message: {e}")
            return None
    
    def encrypt_file_content(self, file_content: bytes, room_key: str) -> Optional[bytes]:
        """Encrypt file content using the room's encryption key"""
        try:
            if not file_content or not room_key:
                return None
            
            # Decode the room key
            key_bytes = base64.urlsafe_b64decode(room_key.encode('utf-8'))
            fernet = Fernet(key_bytes)
            
            # Encrypt the file content
            encrypted_content = fernet.encrypt(file_content)
            
            return encrypted_content
            
        except Exception as e:
            logger.error(f"Error encrypting file content: {e}")
            return None
    
    def decrypt_file_content(self, encrypted_content: bytes, room_key: str) -> Optional[bytes]:
        """Decrypt file content using the room's encryption key"""
        try:
            if not encrypted_content or not room_key:
                return None
            
            # Decode the room key
            key_bytes = base64.urlsafe_b64decode(room_key.encode('utf-8'))
            fernet = Fernet(key_bytes)
            
            # Decrypt the file content
            decrypted_content = fernet.decrypt(encrypted_content)
            
            return decrypted_content
            
        except Exception as e:
            logger.error(f"Error decrypting file content: {e}")
            return None
    
    def rotate_room_key(self, old_key: str) -> str:
        """Generate a new room key (for key rotation)"""
        try:
            # Generate new key
            new_key = self.generate_room_key()
            
            # Log key rotation (without exposing actual keys)
            logger.info("Room encryption key rotated successfully")
            
            return new_key
            
        except Exception as e:
            logger.error(f"Error rotating room key: {e}")
            raise
    
    def validate_key(self, key: str) -> bool:
        """Validate if a key is properly formatted"""
        try:
            if not key:
                return False
            
            # Try to decode the key
            key_bytes = base64.urlsafe_b64decode(key.encode('utf-8'))
            
            # Try to create a Fernet instance
            Fernet(key_bytes)
            
            return True
            
        except Exception:
            return False
    
    def encrypt_user_data(self, data: str, user_password: str) -> Optional[dict]:
        """Encrypt user-specific data using their password"""
        try:
            if not data or not user_password:
                return None
            
            # Generate salt
            salt = self.generate_salt()
            
            # Derive key from password
            key = self.derive_key_from_password(user_password, salt)
            fernet = Fernet(key)
            
            # Encrypt data
            encrypted_data = fernet.encrypt(data.encode('utf-8'))
            
            return {
                'encrypted_data': base64.urlsafe_b64encode(encrypted_data).decode('utf-8'),
                'salt': base64.urlsafe_b64encode(salt).decode('utf-8')
            }
            
        except Exception as e:
            logger.error(f"Error encrypting user data: {e}")
            return None
    
    def decrypt_user_data(self, encrypted_data: str, salt: str, user_password: str) -> Optional[str]:
        """Decrypt user-specific data using their password"""
        try:
            if not encrypted_data or not salt or not user_password:
                return None
            
            # Decode salt
            salt_bytes = base64.urlsafe_b64decode(salt.encode('utf-8'))
            
            # Derive key from password
            key = self.derive_key_from_password(user_password, salt_bytes)
            fernet = Fernet(key)
            
            # Decode and decrypt data
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = fernet.decrypt(encrypted_bytes)
            
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error decrypting user data: {e}")
            return None
    
    def hash_sensitive_data(self, data: str) -> str:
        """Create a hash of sensitive data for verification purposes"""
        try:
            digest = hashes.Hash(hashes.SHA256())
            digest.update(data.encode('utf-8'))
            hash_bytes = digest.finalize()
            
            return base64.urlsafe_b64encode(hash_bytes).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error hashing sensitive data: {e}")
            raise
    
    def verify_data_integrity(self, data: str, expected_hash: str) -> bool:
        """Verify data integrity using hash comparison"""
        try:
            actual_hash = self.hash_sensitive_data(data)
            return actual_hash == expected_hash
            
        except Exception as e:
            logger.error(f"Error verifying data integrity: {e}")
            return False