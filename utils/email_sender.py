import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Replace these with your actual email credentials
SENDER_EMAIL = "hr.democompany@gmail.com"
SENDER_PASSWORD = "uqgctppzzvtetfsa"

def send_interview_email(name, to_email, interview_datetime):
    
    subject = "Interview Invitation - Shortlisting"
    body = f"""
    Hello {name},

    We hope this message finds you well.

    We would like to invite you to attend a virtual HR interview for an opportunity at XYZ company. 
    Your background, including your skills, experience, and qualifications, aligns well with our current hiring needs.

    Interview Date & Time: {interview_datetime}
    
    Meeting Link: https://zoom.com/meet/{to_email.split('@')[0]}

    Please be available at the scheduled time. 
    If you encounter any issues accessing the link, feel free to reach out to us in advance.

    We look forward to speaking with you.

    Warm regards,  
    Talent Acquisition Team  
    XYZ comapny  
    hr@xyz.com | +91-XXXXXXXXXX

    """

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        print(f"Interview email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
