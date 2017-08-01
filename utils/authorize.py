import mysql

def check_login(session):
    if 'logged_in' in session:
        c, conn = mysql.connection()

        c.execute("select user_name, user_id from Users where user_id=%s and user_name=%s;", [session['user_id'], session['user_name']])

        results = c.fetchall()

        if results:
            return True

        c.close()
        conn.close()

    else:
        return False
