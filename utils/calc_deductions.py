import mysql, authorize
import math, decimal

def calculate_deductions(session):
    if authorize.check_login(session):
        c, conn = mysql.connection()

        c.execute("select * from Deductions where user_id=%s;", session['user_id'])
        deductions = c.fetchall()

        c.execute("select pay_rate from User_Pay where user_id=%s;", session['user_id'])
        user_pay = c.fetchone()

        c.execute("select * from Paychecks where user_id=%s;", session['user_id'])
        paychecks = c.fetchall()

        for paycheck in paychecks:
            hours = paycheck['gross_pay'] / user_pay['pay_rate']

            deduction_amount = 0

            for deduction in deductions:
                if deduction['type_id'] == 1:
                    deduction_amount += deduction['amount']*hours
                if deduction['type_id'] == 2:
                    deduction_amount += deduction['amount']
                if deduction['type_id'] == 3:
                    deduction_amount += paycheck['gross_pay']*(deduction['amount']/100)

            deduction_amount = decimal.Decimal(deduction_amount).quantize(decimal.Decimal('.01'))

            net_pay = paycheck['gross_pay'] - paycheck['income_tax'] - paycheck['medicare'] - paycheck['social_security'] - deduction_amount

            c.execute("update Paychecks set net_pay=%s, deductions=%s where paycheck_id=%s;", [net_pay, deduction_amount, paycheck['paycheck_id']])

            conn.commit()


    else:
        print "You are not authorized."

