import binascii
import os
from Crypto.Cipher import AES
from django.core.exceptions import ValidationError
from django.db import models
from django import forms
from django.core.validators import validate_email
from django.core.files.storage import FileSystemStorage
from Crypto.Util.Padding import pad, unpad
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import re


def is_valid_email(email):
    """Validate email format."""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

SECRET_KEY = b'2\t\xfc0\xf4\x10\x7f\xd7\xe5(\x14;\xf8\xf4\xfc\x8dw\xa1\x15\xd3\xfb\x13\\\x0cf\xb8%K&\x95\x99\x05'


class BaseEncryptedField(models.Field):
    def __init__(self, *args, **kwargs):
        cipher_name = kwargs.pop('cipher', 'AES')

        # Ensure only AES is supported
        if cipher_name != 'AES':
            raise ValueError(f"Unsupported cipher: {cipher_name}. Only AES is supported.")

        self.block_size = AES.block_size  # Typically 16 bytes for AES
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        """Decrypt the value when retrieving from the database."""
        if value and self.is_hex(value):
            try:
                encrypted_data = binascii.a2b_hex(value)  # Convert hex to bytes

                # If the data is shorter than the block size, handle it gracefully
                if len(encrypted_data) < self.block_size:
                    # Handle short data gracefully (return None or original value)
                    return None  # Or return value if you want to retain unencrypted data

                # Extract the IV and ciphertext
                iv = encrypted_data[:self.block_size]
                ciphertext = encrypted_data[self.block_size:]

                # Initialize cipher for decryption
                cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
                decrypted = cipher.decrypt(ciphertext)

                # Remove padding (null byte padding) and decode
                return decrypted.rstrip(b'\0').decode('utf-8')

            except Exception as e:
                raise ValueError(f"Decryption failed: {e}")

        # Return plain text or None if not encrypted
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        """Encrypt the value before saving to the database."""
        if value is not None and isinstance(value, str) and not self.is_hex(value):
            try:
                # Convert the value to bytes
                value = value.encode('utf-8')

                # Generate a random IV
                iv = os.urandom(self.block_size)

                # Apply padding to ensure the plaintext size is a multiple of the block size
                padding = self.block_size - len(value) % self.block_size
                value += b'\0' * padding

                # Encrypt the value
                cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
                encrypted_value = cipher.encrypt(value)

                # Concatenate IV and encrypted value, then convert to hex
                encrypted_data = iv + encrypted_value
                encrypted_data_hex = binascii.b2a_hex(encrypted_data).decode('utf-8')

                return encrypted_data_hex

            except Exception as e:
                raise ValueError(f"Encryption failed: {e}")

        # Return the value as-is if it's already encrypted or None
        return value

    def is_hex(self, value):
        """Helper method to check if a string is valid hexadecimal."""
        try:
            binascii.a2b_hex(value)
            return True
        except (binascii.Error, TypeError, ValueError):
            return False


class EncryptedString(str):
    pass


class EncryptedTextField(BaseEncryptedField):
    """
    A custom field for storing encrypted text data.
    Suitable for longer text inputs, including non-ASCII (Unicode) characters.
    """
    def __init__(self, *args, **kwargs):
        # No max_length for text fields by default
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        """Encrypt text data before saving to the database."""
        if value:
            value = value.strip()  # Remove leading/trailing spaces
            
            # Ensure the value is a string and encode it to UTF-8 for encryption
            if isinstance(value, str):
                value = value.encode('utf-8')  # Convert string to bytes (UTF-8 encoding)
        return super().get_db_prep_value(value, connection=None)

    def from_db_value(self, value, expression, connection):
        """Decrypt text data when retrieving from the database."""
        decrypted_value = super().to_python(value)
        
        # Decode the bytes back to a string (handle non-ASCII/Unicode characters)
        if isinstance(decrypted_value, bytes):
            decrypted_value = decrypted_value.decode('utf-8')  # Convert bytes back to string
        return decrypted_value

    def is_hex(self, value):
        """Check if the value is a valid hexadecimal string."""
        try:
            # Only check hex if the string contains only ASCII characters
            if isinstance(value, str) and all(c in '0123456789abcdefABCDEF' for c in value):
                binascii.a2b_hex(value)  # Try to convert it to bytes
                return True
        except (binascii.Error, TypeError):
            pass
        return False

    def db_type(self, connection):
        """Return the database column type for encrypted text."""
        return 'text'  # Use 'text' for long encrypted text



class EncryptedCharField(BaseEncryptedField):
    """
    A custom field for storing encrypted character data.
    Similar to Django's CharField with a max_length constraint.
    """
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 254)  # Default max_length for CharField
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        """Encrypt character data before saving to the database."""
        if isinstance(value, str):
            value = value.strip()  # Remove leading/trailing spaces
            value = value.encode('utf-8')  # Ensure it's encoded in UTF-8 before encryption
        return super().get_db_prep_value(value, connection=None)

    def from_db_value(self, value, expression, connection):
        """Decrypt character data when retrieving from the database."""
        value = super().to_python(value)
        if isinstance(value, bytes):
            value = value.decode('utf-8')  # Decode from UTF-8 when fetching from DB
        return value

    def db_type(self, connection):
        """Return the database column type for encrypted character data."""
        return f'varchar({self.max_length})'  # Use 'varchar' with the specified max_length


class EncryptedEmailField(BaseEncryptedField):
    """A custom field for encrypting and validating email addresses."""

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 254)  # Standard max length for emails
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        """Encrypt email data before saving to the database."""
        if value:
            value = value.strip()  # Remove leading/trailing spaces
        
        from django.db import connection
        return super().get_db_prep_value(value, connection)

    def from_db_value(self, value, expression, connection):
        """Decrypt and validate email."""
        decrypted_value = super().to_python(value)
        if decrypted_value and not self.is_valid_email(decrypted_value):
            raise ValidationError("Invalid email address found in encrypted data.")
        return decrypted_value

    def is_valid_email(self, email):
        """Helper method to validate email format."""
        try:
            validate_email(email)
            return True
        except ValidationError:
            return False

    def db_type(self, connection):
        """Return the database column type for encrypted email data."""
        return f'VARCHAR({self.max_length})'  # Ensure it's VARCHAR with specified length


class EncryptedFileSystemStorage(FileSystemStorage):
    """Custom storage for encrypting and decrypting files."""
    
    def _save(self, name, content):
        """Encrypt the file content before saving."""
        # Initialize AES cipher in CBC mode with a random IV
        cipher = AES.new(SECRET_KEY[:32], AES.MODE_CBC, iv=os.urandom(AES.block_size))
        iv = cipher.iv
        
        # Read content, pad it, and encrypt
        encrypted_content = cipher.encrypt(pad(content.read(), AES.block_size))
        
        # Combine IV with encrypted content and hexlify the result for storage
        encrypted_data = binascii.hexlify(iv + encrypted_content).decode('utf-8')
        
        # Wrap encrypted data in a BytesIO object to mimic a file-like object
        encrypted_file = BytesIO(encrypted_data.encode('utf-8'))
        
        # Convert the BytesIO object to an InMemoryUploadedFile
        # Here 'file' is a dummy name, adjust it according to your needs
        encrypted_file = InMemoryUploadedFile(encrypted_file, None, name, 'application/octet-stream', len(encrypted_data), None)
        
        # Save the encrypted data to the file system using the InMemoryUploadedFile
        return super()._save(name, encrypted_file)

    def open(self, name, mode='rb'):
        """Decrypt the file content when opening."""
        # Read the encrypted data from storage
        encrypted_data = super().open(name, mode).read()
        
        # Unhexlify the encrypted data to get the IV and content
        encrypted_data = binascii.unhexlify(encrypted_data)
        iv = encrypted_data[:AES.block_size]
        encrypted_content = encrypted_data[AES.block_size:]
        
        # Initialize the cipher with the IV and decrypt the content
        cipher = AES.new(SECRET_KEY[:32], AES.MODE_CBC, iv=iv)
        decrypted_content = unpad(cipher.decrypt(encrypted_content), AES.block_size)
        
        # Return the decrypted content as a file-like object (BytesIO)
        return BytesIO(decrypted_content)
