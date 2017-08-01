import MySQLdb
import MySQLdb.cursors
from settings import DB_HOST, DB_USER, DB_PASS, DB

def connection():
    conn = MySQLdb.connect(host=DB_HOST,
                           user=DB_USER,
                           passwd=DB_PASS,
                           db=DB,
                           cursorclass=MySQLdb.cursors.DictCursor)
    c = conn.cursor()

    return c, conn
