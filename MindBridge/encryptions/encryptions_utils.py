import logging
from django.conf import settings
import base64
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

cipher_suite = Fernet(settings.FERNET_KEY)

def encrypt_data(data):
    try:
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif not isinstance(data, bytes):
            data = str(data).encode('utf-8')

        logger.debug(f"Data before encryption (bytes): {data}")

        encrypted_data = cipher_suite.encrypt(data)
        encoded_data = base64.b64encode(encrypted_data).decode('utf-8')

        # Prepend marker to identify encrypted data
        encoded_data = 'ENC' + encoded_data

        logger.debug(f"Encrypted data (base64 string): {encoded_data}")
        return encoded_data
    except Exception as e:
        logger.error(f"Error during encryption: {e}")
        return None


def decrypt_data(encrypted_data):
    try:
        # Check if the data has the correct encrypted marker
        if encrypted_data.startswith('ENC'):
            encrypted_data = encrypted_data[3:]  # Remove 'ENC' prefix
        else:
            raise ValueError("Data does not have the 'ENC' prefix.")

        encrypted_data = base64.b64decode(encrypted_data)
        decrypted_data = cipher_suite.decrypt(encrypted_data)
        decoded_data = decrypted_data.decode('utf-8')
        return decoded_data
    except Exception as e:
        logger.error(f"Error during decryption: {e}")
        return None

    
    
from django.db import models
from cryptography.fernet import Fernet, InvalidToken
import base64, binascii
from django.conf import settings
import re
import logging
from django.core.files.storage import FileSystemStorage

# Set up logger
logger = logging.getLogger(__name__)

FERNET_KEY = b'4DVk-ZQfzSM2UwDQ3kaFxSauN4B1mLYzqsFmcmlaCYw='
#cipher_suite = Fernet(FERNET_KEY)
## Utility function to validate email format 4DVk-ZQfzSM2UwDQ3kaFxSauN4B1mLYzqsFmcmlaCYw=


def is_valid_email(email):
    """Validate email format."""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

# Cipher suite for encryption/decryption
#cipher_suite = Fernet(settings.FERNET_KEY)

# Custom Django model fields for encryption and decryption using Fernet
class EncryptedField(models.TextField):
    """
    A custom Django model field for encrypting and decrypting data using Fernet.
    """
    def __init__(self, *args, **kwargs):
        # Initialize the cipher with the environment key
        if not FERNET_KEY:
            raise ValueError("FERNET_KEY must be set in the environment variables.")
        self.cipher_suite = Fernet(FERNET_KEY)
        super().__init__(*args, **kwargs)

    def to_python(self, value, expression=None, connection=None):
        """
        Ensure the value is always decrypted when retrieved from the database.
        """
        if value is not None:
            try:
                # Log the received encrypted value
                logger.debug(f"Received encrypted value for decryption: {value}")

                # Decode the value from Base64
                encrypted_value = base64.b64decode(value)
                logger.debug(f"Base64 decoded value: {encrypted_value}")

                # Decrypt the value using the cipher
                decrypted_value = self.cipher_suite.decrypt(encrypted_value)
                logger.debug(f"Decrypted value: {decrypted_value}")

                # Return the decrypted value and handle padding correctly
                return decrypted_value.decode('utf-8').split('\0')[0]  # Handle padding
            except Exception as e:
                logger.error(f"Error during decryption: {e}")
                raise ValueError("Decryption failed. Ensure that the value has not been tampered with.") from e
        return value

    def get_db_prep_value(self, value, **kwargs):
        """
        Ensure the value is encrypted before saving to the database.
        """
        if value is not None:
            # Ensure padding for the encryption block size
            padding = self.cipher_suite.block_size - len(value.encode('utf-8')) % self.cipher_suite.block_size
            if padding and padding < self.cipher_suite.block_size:
                value += "\0" + ''.join([random.choice(string.printable) for _ in range(padding-1)])

            # Encrypt the value
            encrypted_value = self.cipher_suite.encrypt(value.encode('utf-8'))

            # Return the encrypted value as Base64
            encrypted_value_base64 = base64.b64encode(encrypted_value).decode('utf-8')
            logger.debug(f"Encrypted value: {value} -> {encrypted_value_base64}")
            return encrypted_value_base64
        return value
      

class EncryptedTextField(EncryptedField):
    """
    A field for encrypting and decrypting large text values.
    """
    def get_prep_value(self, value):
        """
        Encrypt the value after trimming whitespace.
        """
        if value:
            value = value.strip()
        return super().get_prep_value(value)


class EncryptedCharField(EncryptedField):
    """
    A custom encrypted CharField to handle encryption and decryption.
    """
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 255)  # Default max_length
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        """
        Encrypt the value, enforcing max_length and trimming whitespace.
        """
        if value:
            value = value.strip()
            if len(value) > self.max_length:
                logger.warning(f"Value length exceeds max_length ({self.max_length}). Truncating.")
                value = value[:self.max_length]
        return super().get_prep_value(value)

    def from_db_value(self, value, expression, connection):
        """
        Decrypt the value after retrieval from the database.
        """
        return super().from_db_value(value, expression, connection)


# Encrypted Email Field
class EncryptedEmailField(EncryptedField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 254)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        """Encrypt email data before saving to the database."""
        if value:
            value = value.strip()  # Remove leading/trailing spaces
        return super().get_prep_value(value)

    def from_db_value(self, value, expression, connection):
        """Decrypt and validate email."""
        decrypted_value = super().from_db_value(value, expression, connection)
        if decrypted_value and not is_valid_email(decrypted_value):
            logger.error(f"Invalid email format after decryption: {decrypted_value}")
            raise ValueError("Invalid email address found in encrypted data")
        return decrypted_value
      
      
class EncryptedFileSystemStorage(FileSystemStorage):
    def _save(self, name, content):
        # Encrypt the file content before saving
        encrypted_content = cipher_suite.encrypt(content.read())
        # Save the encrypted content
        return super()._save(name, encrypted_content)

    def open(self, name, mode='rb'):
        # Open the encrypted file
        file = super().open(name, mode)
        # Decrypt the content when opening
        decrypted_content = cipher_suite.decrypt(file.read())
        return decrypted_content
