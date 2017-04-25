import smtplib
from email.mime.text import MIMEText

from galicaster.core import context

conf = context.get_conf()
logger = context.get_logger()


def init():
    try:
        gcmail = GCEmail()
        pass

    except ValueError:
        pass


class GCEmail(object):

    def __init__(self):
        self.from_add = conf.get('gcmail', 'from_address')
        self.smtp_router = conf.get('gcmail', 'smtp_server')

    def send_mail(self, recipient, subject='', t_msg=''):
        # Create a text/plain message
        msg = MIMEText(t_msg)

        msg['Subject'] = subject
        msg['From'] = self.from_add
        msg['To'] = recipient

        # Send the message via our own SMTP server
        try:
            s = smtplib.SMTP(self.smtp_router)
            s.sendmail(self.from_add, [recipient], msg.as_string())
            s.quit()

        except Exception as e:
            logger.debug('SMTP email sending failed: {}'.format(e))
