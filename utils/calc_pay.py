import mysql, authorize
import requests, datetime, math, decimal


def calculate_paychecks(session, last_pay_date):
    if authorize.check_login(session):
        c, conn = mysql.connection()
        last_pay_date = datetime.datetime.strptime(last_pay_date, "%Y-%m-%d").date()

        c.execute(
            "select user_id, pay_rate, tax_allowances, pay_period_id, pay_type_id, pay_delay, fp.filing_status from User_Pay as up left join Filing_Status as fp on up.filing_status_id = fp.filing_status_id where user_id=%s;",
            session['user_id'])
        user_pay = c.fetchall()[0]

        c.execute(
            "select * from Work_Days where user_id=%s;", session['user_id']
        )

        user_pay['work_days'] = c.fetchall()

        c.execute("select * from Day_of_Week order by day_id;")

        days_of_week = c.fetchall()

        pay_year = last_pay_date.year

        taxee_api = {}
        taxee_api['url'] = "https://taxee.io/api/v2/federal/" + str(pay_year)
        taxee_api['headers'] = {
            'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJBUElfS0VZX01BTkFHRVIiLCJodHRwOi8vdGF4ZWUuaW8vdXNlcl9pZCI6IjU4NzI2MDUzY2UzN2E4MjM4NGFmYmYzMyIsImh0dHA6Ly90YXhlZS5pby9zY29wZXMiOlsiYXBpIl0sImlhdCI6MTQ4Mzg5MDc3MX0.GcPeCa2H1bi9BQx4uo_NypoQ4pGsd2aDRC9YjjvHG5s'
        }

        req = requests.get(taxee_api['url'], headers=taxee_api['headers'])

        tax_info = req.json()

        user_pay['tax_info'] = tax_info[user_pay['filing_status']]

        end_of_year = datetime.date(pay_year, 12, 31)
        current_year = datetime.datetime.now().year

        if user_pay['pay_period_id'] == 1:  # Weekly Paychecks
            if last_pay_date.isocalendar()[0] < current_year:
                paychecks_paid = 0
            else:
                paychecks_paid = last_pay_date.isocalendar()[1]

            paychecks_remaining = end_of_year.isocalendar()[1] - paychecks_paid

            total_paychecks = paychecks_paid + paychecks_remaining

            if user_pay['pay_type_id'] == 1:  # Hourly Pay
                pass
            elif user_pay['pay_type_id'] == 2:  # Salary Pay
                pass
        elif user_pay['pay_period_id'] == 2:  # Bi-Weekly Paychecks
            if last_pay_date.isocalendar()[0] < current_year:
                paychecks_paid = 0
                paychecks_remaining = int(math.floor(float(end_of_year.isocalendar()[1]) / 2))
            else:
                paychecks_paid = int(math.ceil(float(last_pay_date.isocalendar()[1]) / 2))
                paychecks_remaining = int(
                    math.floor(float(end_of_year.isocalendar()[1] - last_pay_date.isocalendar()[1]) / 2))
            total_paychecks = paychecks_paid + paychecks_remaining

            if user_pay['pay_type_id'] == 1:  # Hourly Pay
                pass
            elif user_pay['pay_type_id'] == 2:  # Salary Pay
                pass
        elif user_pay['pay_period_id'] == 3:  # Semi-Monthly Paychecks
            total_paychecks = 24
            if last_pay_date.isocalendar()[0] < current_year:
                paychecks_paid = 0
                paychecks_remaining = total_paychecks
            else:
                paychecks_paid = last_pay_date.month * 2 - 1

                if (last_pay_date.day - 15) > 0:
                    paychecks_paid += 1

                paychecks_remaining = total_paychecks - paychecks_paid

            if user_pay['pay_type_id'] == 1:  # Hourly Pay
                paychecks = []

                prev_pay_date = datetime.date(last_pay_date.year-1, 12, 15 + user_pay['pay_delay']) - datetime.timedelta(days=1)
                for p in range(total_paychecks):

                    current_paycheck = {}
                    if prev_pay_date.month == 12:
                        end_of_month = datetime.date(prev_pay_date.year+1, 01, 01) - datetime.timedelta(days=1)
                    else:
                        end_of_month = datetime.date(prev_pay_date.year, prev_pay_date.month + 1, 1) - datetime.timedelta(
                            days=1)

                    begin_pay_period = prev_pay_date - datetime.timedelta(days=user_pay['pay_delay'] - 1)

                    end_last_pay_period = prev_pay_date - datetime.timedelta(days=user_pay['pay_delay'])
                    if end_last_pay_period.day <= 15:
                        end_pay_period = end_of_month
                    else:
                        end_pay_period = begin_pay_period + datetime.timedelta(days=14)

                    days_in_period = end_pay_period.day - begin_pay_period.day + 1

                    work_hours = 0

                    for day in (begin_pay_period + datetime.timedelta(n) for n in range(days_in_period)):
                        for week_day in days_of_week:
                            if day.isoweekday() == week_day['python_day_id']:
                                for work_day in user_pay['work_days']:
                                    if week_day['day_id'] == work_day['day_id']:
                                        work_hours += work_day['hours']

                    current_paycheck['gross_pay'] = decimal.Decimal(work_hours * user_pay['pay_rate']).quantize(decimal.Decimal('.01'))
                    current_paycheck['pay_date'] = end_pay_period + datetime.timedelta(days=user_pay['pay_delay'])

                    paychecks.append(current_paycheck)

                    prev_pay_date = current_paycheck['pay_date']

            elif user_pay['pay_type_id'] == 2:  # Salary Pay
                paycheck_amount = user_pay['pay_rate']/total_paychecks
        elif user_pay['pay_period_id'] == 4:  # Monthly Paychecks
            total_paychecks = 12

            if last_pay_date.isocalendar()[0] < current_year:
                paychecks_paid = 0
                paychecks_remaining = total_paychecks
            else:
                paychecks_paid = last_pay_date.month
                paychecks_remaining = total_paychecks - paychecks_paid

            if user_pay['pay_type_id'] == 1:  # Hourly Pay
                pass
            elif user_pay['pay_type_id'] == 2:  # Salary Pay
                pass

        user_pay['income'] = 0

        for check in paychecks:
            user_pay['income'] += check['gross_pay']

        user_pay['taxable_income'] = user_pay['income'] - user_pay['tax_info']['deductions'][0]['deduction_amount'] - (user_pay['tax_info']['exemptions'][0]['exemption_amount'] * user_pay['tax_allowances'])


        for i in range(len(user_pay['tax_info']['income_tax_brackets'])):

            if user_pay['tax_info']['income_tax_brackets'][i]['bracket'] < user_pay['taxable_income']:
                pass
            else:
                i -= 1

                if user_pay['taxable_income'] <= 0:
                    user_pay['income_tax'] = 0
                else:
                    user_pay['income_tax'] = ((user_pay['taxable_income'] - user_pay['tax_info']['income_tax_brackets'][i]['amount']) * (decimal.Decimal(user_pay['tax_info']['income_tax_brackets'][i]['marginal_rate']) / 100)) + user_pay['tax_info']['income_tax_brackets'][i]['amount']
                    break

        tax_remaining = user_pay['income_tax']
        for check in paychecks:
            check['income_tax'] = decimal.Decimal((check['gross_pay']/user_pay['income']*user_pay['income_tax']).quantize(decimal.Decimal('.01')))
            check['social_security'] = decimal.Decimal((check['gross_pay'] * decimal.Decimal('0.062')).quantize(decimal.Decimal('.01')))
            check['medicare'] = decimal.Decimal((check['gross_pay'] * decimal.Decimal('0.0145')).quantize(decimal.Decimal('.01')))

            check['net_pay'] = check['gross_pay'] - check['income_tax'] - check['social_security'] - check['medicare']

            check['user_id'] = session['user_id']

            c.execute("insert into Paychecks (income_tax, user_id, net_pay, medicare, pay_date, social_security, gross_pay) values (%s, %s, %s, %s, %s, %s, %s);", [check['income_tax'], check['user_id'], check['net_pay'], check['medicare'], check['pay_date'], check['social_security'], check['gross_pay']])

        conn.commit()
        c.close()
        conn.close()
        return True
    else:
        return False

# # TEST CASE
session = {}
session['user_id'] = 24
session['logged_in'] = True
session['user_name'] = 'ssmith123'

calculate_paychecks(session, '2017-01-20')
