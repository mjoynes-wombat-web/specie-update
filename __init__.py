from utils import mysql, passwords, authorize, calc_pay, calc_bills, calc_deductions
from flask import Flask, redirect, render_template, request, session
import os, datetime

from flask import make_response
from functools import wraps, update_wrapper


def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return update_wrapper(no_cache, view)

# os.system("sass --update scss:static/css")

app = Flask(__name__)

c, conn = mysql.connection()


@app.route('/')
@nocache
def home():
    if authorize.check_login(session):
        return redirect('/calendar/' + session['user_name'])
    elif request.args.get('error') == 'duplicate':
        return render_template('home.html', title="Duplicate User - Specie - Home")
    else:
        return render_template('home.html', title="Specie - Home")


@app.route('/register', methods=['GET', 'POST'])
@nocache
def add_new_user():
    if authorize.check_login(session):
        return redirect('/calendar/' + session['user_name'])
    else:
        if request.method == 'POST':
            post = dict()
            post['first_name'] = str(request.form['first_name'])
            post['last_name'] = str(request.form['last_name'])
            post['email'] = str(request.form['email'])
            post['user_name'] = str(request.form['user_name'])
            post['password'] = str(request.form['password'])

            c.execute("select * from Users where user_name=%s;", post['user_name'])

            matching_users = c.fetchall()

            if matching_users:
                session['form'] = post
                return redirect('/?error=duplicate#user_name')
            else:
                post['password_encrypted'] = passwords.encrypt(post['password'])

                c.execute(
                    "insert into Users (first_name, last_name, email, user_name, password) values (%s, %s, %s, %s, %s);",
                    [post['first_name'], post['last_name'], post['email'], post['user_name'],
                     post['password_encrypted']])
                conn.commit()

                return redirect('/login?registered=true')
        elif request.method == 'GET':
            return redirect('/')


@app.route('/login', methods=['GET', 'POST'])
@nocache
def login():
    if authorize.check_login(session):
        return redirect('/calendar/' + session['user_name'])
    else:
        if request.method == 'POST':
            post = dict()
            post['user_name'] = str(request.form['user_name'])
            post['password'] = passwords.encrypt(str(request.form['password']))

            c.execute("select * from Users where user_name=%s and password=%s;", [post['user_name'], post['password']])

            auth = c.fetchall()

            if auth:
                session['logged_in'] = True
                session['user_id'] = auth[0]['user_id']
                session['user_name'] = auth[0]['user_name']
                return redirect('/calendar/' + session['user_name'])
            else:
                return redirect('/login?error=failed')
        elif request.method == 'GET':
            return render_template('login.html')


@app.route("/logout")
@nocache
def logout():
    if authorize.check_login(session):
        del session['logged_in']
        del session['user_id']
        del session['user_name']
    else:
        pass

    return redirect('/login?logout=true')


@app.route("/calendar/<user>")
@nocache
def calendar(user=None):
    if authorize.check_login(session):
        if user == session['user_name']:
            c.execute("select * from User_Pay where user_id=%s;", session['user_id'])
            pay_results = c.fetchall()

            if pay_results:
                today = datetime.datetime.now().date()
                date_range = []

                for num in range(0, 31):
                    new_date = today + datetime.timedelta(days=num)
                    date_range.append({
                        'date': new_date,
                        'day_of_week': new_date.isoweekday()
                    })

                paychecks = []
                bills = []

                c.execute(
                    "select due_date_id, Bills.bill_id, bill_name, amount, bill_due_date, bill_billing_date, bill_pay_date from Bills join Bill_Dates on Bills.bill_id = Bill_Dates.bill_id where user_id=%s and (bill_due_date between %s and %s or bill_billing_date between %s and %s or bill_pay_date between %s and %s) group by due_date_id;",
                    [session['user_id'], date_range[0]['date'], date_range[-1]['date'], date_range[0]['date'], date_range[-1]['date'], date_range[0]['date'], date_range[-1]['date']])

                bills = c.fetchall()

                c.execute("select * from Paychecks where user_id=%s and pay_date between %s and %s;",
                          [session['user_id'], date_range[0]['date'], date_range[-1]['date']])
                paychecks = c.fetchall()

                dates = []

                for bill in bills:
                    dates.append(bill['bill_due_date'])
                    dates.append(bill['bill_billing_date'])
                    dates.append(bill['bill_pay_date'])

                for paycheck in paychecks:
                    if paycheck['pay_date'] >= today:
                        dates.append(paycheck['pay_date'])

                dates = sorted(list(set(dates)))

                return render_template('calendar.html', date_range=date_range, dates=dates, paychecks=paychecks, bills=bills)
            else:
                return redirect("/add-pay")
        else:
            return redirect('/calendar/' + session['user_name'] + '?error=wrong_user')
    else:
        return redirect('/login?error=login_required')


@app.route('/add-pay', methods=['GET', 'POST'])
@nocache
def add_pay():
    if authorize.check_login(session):
        c.execute("select * from Day_of_Week order by day_id;")
        days_of_week = c.fetchall()
        if request.method == 'GET':
            c.execute("select * from User_Pay where user_id=%s;", session['user_id'])
            pay = c.fetchall()
            if pay:
                c.execute("select * from Work_Days where user_id=%s order by day_id;", session['user_id'])
                work_schedule = c.fetchall()

                # impliment editable pay

                return render_template('add_pay.html', days_of_week=days_of_week, edit=True)
            else:
                return render_template('add_pay.html', days_of_week=days_of_week, edit=False)
        elif request.method == 'POST':
            post = dict()
            post['pay_period'] = int(request.form['pay_period'])
            post['pay_delay'] = request.form['pay_delay']
            post['last_paycheck'] = str(request.form['last_paycheck'])
            post['filing_status'] = int(request.form['filing_status'])
            post['federal_allowances'] = int(request.form['federal_allowances'])
            post['pay_type'] = int(request.form['pay_type'])
            post['pay_delay'] = str(request.form['pay_delay'])
            post['hours'] = []

            for day in days_of_week:
                if day['day'] in request.form:
                    post['hours'].append((int(session['user_id']), int(day['day_id']),
                                          float(request.form['hours_' + str(day['day_id'])])))

            if post['pay_type'] == 1:
                post['pay_rate'] = request.form['hourly_rate']
            elif post['pay_type'] == 2:
                post['pay_rate'] = request.form['salary']

            c.execute("select user_id from Users where user_id=%s;", session['user_id'])
            user_id_results = c.fetchall()

            user_id = user_id_results[0]['user_id']

            if user_id == session['user_id']:
                c.execute(
                    "insert into User_Pay (user_id, pay_rate, tax_allowances, pay_period_id, pay_type_id, filing_status_id, pay_delay) values (%s, %s, %s, %s, %s, %s, %s);",
                    [session['user_id'], post['pay_rate'], post['federal_allowances'], post['pay_period'],
                     post['pay_type'], post['filing_status'], post['pay_delay']])
                c.executemany("insert into Work_Days (user_id, day_id, hours) values (%s, %s, %s);", post['hours'])
                conn.commit()

                calc_pay.calculate_paychecks(session, post['last_paycheck'])

                return redirect('/add-bill')
            else:
                return redirect('/login?error=bad_id')
    else:
        return redirect('/login?error=login_required')


@app.route('/add-bill', methods=['GET', 'POST'])
@nocache
def add_bill():
    if authorize.check_login(session):
        if request.method == 'POST':
            post = dict()
            post['bill_name'] = request.form['bill_name']
            post['amount'] = request.form['amount']
            post['due_date'] = datetime.datetime.strptime(request.form['due_date'], '%Y-%m-%d')
            post['due_date'] = datetime.datetime.strptime(request.form['due_date'], '%Y-%m-%d')

            c.execute(
                "insert into Bills (user_id, bill_name, amount) values(%s, %s, %s);",
                [session['user_id'], post['bill_name'], post['amount']])

            c.execute("select bill_id from Bills order by bill_id desc limit 1")
            last_bill_entered = c.fetchone()


            if post['due_date'].month == post['due_date'].month:
                for i in range(1, 13):
                    if post['due_date'].day > 28 and i in (2, 4, 6, 9, 11):
                        if i == 2:
                            post['due_date']= post['due_date'].replace(day=28)
                        elif post['due_date'].day == 31:
                            post['due_date'] = post['due_date'].replace(day=30)

                    if post['due_date'].day > 28 and i in (2, 4, 6, 9, 11):
                        if i == 2:
                            post['due_date']= post['due_date'].replace(day=28)
                        elif post['due_date'].day == 31:
                            post['due_date'] = post['due_date'].replace(day=30)

                    post['due_date'] = datetime.date(post['due_date'].year, i, post['due_date'].day)
                    post['due_date'] = datetime.date(post['due_date'].year, i, post['due_date'].day)
                    c.execute(
                        "insert into Bill_Dates (bill_id, bill_due_date, bill_billing_date, bill_pay_date) values(%s, %s, %s, %s);",
                        [last_bill_entered['bill_id'], post['due_date'], post['due_date'], post['due_date']])
            else:
                for i in range(1, 13):
                    if post['due_date'].day > 28 and i in (2, 4, 6, 9, 11):
                        if i == 2:
                            post['due_date']= post['due_date'].replace(day=28)
                        elif post['due_date'].day == 31:
                            post['due_date'] = post['due_date'].replace(day=30)

                    if post['due_date'].day > 28 and i+1 in (2, 4, 6, 9, 11):
                        if i+1 == 2:
                            post['due_date']= post['due_date'].replace(day=28)
                        elif post['due_date'].day == 31:
                            post['due_date'] = post['due_date'].replace(day=30)

                    post['due_date'] = datetime.date(post['due_date'].year, i, post['due_date'].day)
                    if i == 12:
                        post['due_date'] = datetime.date(post['due_date'].year+1, 1, post['due_date'].day)
                    else:
                        post['due_date'] = datetime.date(post['due_date'].year, i+1, post['due_date'].day)

                    c.execute(
                        "insert into Bill_Dates (bill_id, bill_due_date, bill_billing_date, bill_pay_date) values(%s, %s, %s, %s);",
                        [last_bill_entered['bill_id'], post['due_date'], post['due_date'], post['due_date']])

            conn.commit()

            calc_bills.distribute_bills(session)

            return redirect('/calendar/' + session['user_name'])
        elif request.method == 'GET':
            return render_template('add_bill.html')
    else:
        return redirect('login?error=login_required')

@app.route('/add-deduction', methods=['GET', 'POST'])
@nocache
def add_deduction():
    if authorize.check_login(session):

        if request.method == 'POST':
            post = dict()
            post['deduction_name'] = request.form['deduction_name']
            post['deduction_type'] = int(request.form['deduction_type'])

            if post['deduction_type'] == 1:
                post['deduction_amount'] = request.form['deduction_rate']

            elif post['deduction_type'] == 2:
                post['deduction_amount'] = request.form['deduction_amount']

            elif post['deduction_type'] == 3:
                post['deduction_amount'] = request.form['deduction_percentage']

            c.execute("insert into Deductions (user_id, deduction_name, amount, type_id) values (%s, %s, %s, %s)", [session['user_id'], post['deduction_name'], post['deduction_amount'], post['deduction_type']])

            conn.commit()

            calc_deductions.calculate_deductions(session)

            return redirect('/calendar/' + session['user_name'])
        else:
            return render_template('add_deduction.html')
    else:
        return redirect('login?error=login_required')


if __name__ == '__main__':
    app.secret_key = os.urandom(12)
    app.run(debug=True, host='0.0.0.0', port=4000)

