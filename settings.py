from dotenv import load_dotenv
from os.path import join, dirname
from os import environ

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

SALT = environ.get("SALT")
DB_HOST = environ.get("DB_HOST")
DB_USER = environ.get("DB_USER")
DB_PASS = environ.get("DB_PASS")
DB = environ.get("DB")