import smtplib
import re
import random
import string
from email.mime.text import MIMEText
import uuid
import os


def check_verify_email(address):
    if not re.match(r'[^@]+@[^@]+\.[^@]+', address):
        return False

    return True


def generate_random_string():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))


def send_email(msg: MIMEText):
    if os.getenv("DEBUG") == 'true':
        print(msg)
        return

    smtp = smtplib.SMTP('smtp.mailgun.org', 2525)
    smtp.login(os.getenv("MAILGUN_SENDER_MAIL"), os.getenv("MAILGUN_SENDER_KEY"))
    smtp.sendmail(msg['From'], msg['To'], msg.as_string())
    smtp.quit()


def send_account_change_email(to_address, username, action):
    if not check_verify_email(to_address):
        return None

    verify_code = generate_random_string()
    msg = MIMEText("""
Hi, {}
Thanks for using ACPool!

Please confirm your email address by the code below.
Your Action is {}

CODE: {}

If you did not request, change your password or let admin know.
* If You want send reply, mail to acpool@acpool.me

Happy mining!
ACPool
        """.format(username, action, verify_code))
    msg['Subject'] = 'Please confirm the code to process your request.'
    msg['From'] = os.getenv("MAILGUN_SENDER_MAIL")
    msg['To'] = to_address

    send_email(msg)

    return verify_code


def send_verify_email(to_address, username):
    if check_verify_email(to_address):
        verify_code = generate_random_string()
        msg = MIMEText("""
Hi, {}
Thanks for using ACPool!
Please confirm your email address by the code below. We'll communicate with you from time to time via email so it's important that we have an up-to-date email address.

CODE: {}

If you did not sign up for a ACPool account please disregard this email.


* If You want send reply, mail to acpool@acpool.me

Happy mining!
ACPool
        """.format(username, verify_code))
        msg['Subject'] = 'Please verify your ACPool account'
        msg['From'] = os.getenv("MAILGUN_SENDER_MAIL")
        msg['To'] = to_address

        send_email(msg)

        return verify_code

    return None


def send_password_reset_email(to_address, username):
    if not check_verify_email(to_address):
        return None

    uri = str(uuid.uuid4())

    msg = MIMEText("""
Hi, {}
Thanks for using ACPool!
Click the URL below to reset your password.

URL: https://acpool.me/api/user/forget/{}
This URL is valid for one hour only.

Happy mining!
ACPool
    """.format(username, uri))
    msg['Subject'] = 'Password Reset'
    msg['From'] = os.getenv("MAILGUN_SENDER_MAIL")
    msg['To'] = to_address

    send_email(msg)

    return uri


def send_temp_password_email(to_address, username, temp_password):
    if not check_verify_email(to_address):
        return None

    msg = MIMEText("""
Hi, {}
Thanks for using ACPool!
Your password is reset.

reset password : {}
Please change your password after login.

Happy mining!
ACPool
    """.format(username, temp_password))
    msg['Subject'] = 'Password Reset'
    msg['From'] = os.getenv("MAILGUN_SENDER_MAIL")
    msg['To'] = to_address

    send_email(msg)

    return True
