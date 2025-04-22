import smtplib

def send_email(email_address, body, subject):
    gmail_user = "ucliede03@gmail.com"
    gmail_pwd = "eenq uuqz nwto nwrg"
    FROM = "CORE SAT Control in Fordham"
    TO = email_address if type(email_address) is list else [email_address]  # must be a list
    SUBJECT = subject
    TEXT = body
    # Prepare actual message
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ','.join(TO), SUBJECT, TEXT)
    try:
      # server = smtplib.SMTP(SERVER)
      server = smtplib.SMTP("smtp.gmail.com", 587)  # or port 587 or 465 doesn't seem to work!
      server.ehlo()
      server.starttls()
      print('login...')
      server.login(gmail_user, gmail_pwd)  
      print('sendmail...')
      server.sendmail(FROM, TO, message)
      server.close()
      print('Successfully sent the email.')
    except:
      print("Failed to send the email.")

if __name__=='__main__':
    email_list = ['yan.wang@berkeley.edu', 'TJayarathne@trccompanies.com', 'jbursill@deltacontrols.com']
    send_email(email_list, 'TEST FOR CORE APP IN FORDHAM', '[CORE SAT Reset] TEST SUBJECT')