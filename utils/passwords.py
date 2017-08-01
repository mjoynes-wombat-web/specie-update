import hashlib
from settings import SALT

def encrypt(password):
    salt = SALT
    return hashlib.md5(salt+password).hexdigest()