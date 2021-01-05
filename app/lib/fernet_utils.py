from cryptography.fernet import Fernet
from flask import current_app


def load_key():
    return open(current_app.config['MFA_ENCRYPT_FILE'], 'rb').read()


def encrypt_string(string):
    key = load_key()
    encoded_string = string.encode()
    f = Fernet(key)
    return f.encrypt(encoded_string)


def decrypt_string(encrypted_string):
    key = load_key()
    f = Fernet(key)
    decrypted_string = f.decrypt(encrypted_string)
    return decrypted_string.decode()
