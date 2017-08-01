import mysql, authorize
import datetime, math, decimal

def distribute_bills(session):
    if authorize.check_login(session):
        c, conn = mysql.connection()

        c.execute("update Paychecks set used_on_bills=0.00 where user_id=%s;", session['user_id'])
        conn.commit()

        c.execute("select due_date_id, Bills.bill_id, bill_name, amount, bill_due_date, bill_billing_date, bill_pay_date from Bills join Bill_Dates on Bills.bill_id = Bill_Dates.bill_id where user_id=%s order by amount desc;", session['user_id'])
        bills = c.fetchall()

        for bill in bills:
            c.execute("select * from Paychecks where user_id = %s and pay_date between %s and %s;", [session['user_id'], bill['bill_billing_date'], bill['bill_due_date']])
            paychecks = c.fetchall()

            for paycheck in paychecks:
                if (paycheck['net_pay'] - paycheck['used_on_bills']) >= bill['amount']:

                    #Loop through and find out which one has less pay taken out of it first before deciding on version 2.
                    c.execute("update Paychecks set used_on_bills=%s where user_id=%s and paycheck_id=%s;", [bill['amount'], session['user_id'], paycheck['paycheck_id']])
                    c.execute("update Bill_Dates set bill_pay_date=%s, paycheck_id=%s where due_date_id=%s and bill_id=%s;", [paycheck['pay_date'], paycheck['paycheck_id'], bill['due_date_id'], bill['bill_id']])
                    conn.commit()
                else:
                    continue


# # TEST CASE
# session = {}
# session['user_id'] = 8
# session['logged_in'] = True
# session['user_name'] = 'james.bond007'
#
# distribute_bills(session)