from passwords import encrypt
from mysql import connection

c, conn = connection()

hashed_pass = encrypt('----------')
c.execute("update Specie.Users set password=%s where user_id=%s;", [hashed_pass, 1])
conn.commit()
# c.execute("select user_id, password from Specie.Users where user_id=1;")
# results = c.fetchall()
#
# for user in results:
#     hashed_pass = encrypt(user['password'])
#     c.execute("update Specie.Users set password=%s where user_id=%s;", [hashed_pass, int(user['user_id'])])
#     conn.commit()
