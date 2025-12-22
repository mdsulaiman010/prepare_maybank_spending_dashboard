from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import mimetypes
import time
import os
import pickle
import base64
import requests
import pandas as pd
from get_access_token import get_access_token
from dotenv import load_dotenv

# Load in directory-specific environem
load_dotenv()

user_gmail = os.environ['email']

access_token = get_access_token(user_gmail)

def append_attachment_file(attachment_directory: str, attachment: str, mime_message: MIMEMultipart):
    attachment_path = os.path.join(attachment_directory, attachment)
            
    content_type, _ = mimetypes.guess_type(attachment_path)
    content_type = content_type or 'application/octet-stream'
    main_type, sub_type = content_type.split('/', 1)
    file_name = os.path.basename(attachment_path)

    with open(attachment_path, 'rb') as f:
        file = MIMEBase(main_type, sub_type)
        file.set_payload(f.read())
        file.add_header('Content-Disposition', 'attachment', filename=file_name)
        encoders.encode_base64(file)

    mime_message.attach(file)

def inline_image_as_base64(img_path):
    with open(img_path, "rb") as img_file:
        b64_img = base64.b64encode(img_file.read()).decode()
    mime_type, _ = mimetypes.guess_type(img_path)
    return f'data:{mime_type};base64,{b64_img}'
    

def send_email_gmail(sender_address, email_to: list, email_cc: list, email_bcc: list, email_subject: str, email_body: str, attachments_directory: str, attachments_list: list):
    """
    Function to send email w/ attachments to respective people specified

    sender_address: str
        Email address that will be sending the email. Acts as user_id

    email_to: list
        List of emails addresses to send respective email to.

    email_cc: list
        List of emails addresses to send respective email to as a CC recipient.

    email_bcc: list
        List of emails addresses to send respective email to as a BCC recipient.

    email_subject: str
        Content to be written as email subject.

    email_body: str
        Content to be written as email body. Provide HTML for customizability, otherwise plain text is sufficient.
    
    attachments_list: list
        List of all files to be sent to the recipients.
    
    attachments_directory: str
        Directory to locate respective files in attachments_list
    """

    # Initialize message template object
    mime_message = MIMEMultipart()

    mime_message['subject'] = email_subject
    mime_message['to'] = ', '.join(email_to)
    mime_message['Cc'] = ', '.join(email_cc)
    mime_message['Bcc'] = ', '.join(email_bcc)

    # If attachments provided, attach to message template
    if attachments_list:
        for attachment in attachments_list:
            append_attachment_file(attachments_directory, attachment, mime_message)

    mime_message.attach(MIMEText(email_body, 'html'))

    raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

    url = f'https://gmail.googleapis.com/gmail/v1/users/{sender_address}/messages/send'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    body = {
        'raw': raw_message
    }

    max_retries = 5
    attempt = 0
    for _ in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()
            print(f"Mail successfully sent to {', '.join([mime_message['to'], mime_message['Cc']])}".removesuffix(', '))
            break
        
        except Exception as e:
            if attempt == max_retries:
                print('Maximum number of retries reached...')
                raise e
            else:
                time.sleep(10)
                attempt += 1
                continue

        
    