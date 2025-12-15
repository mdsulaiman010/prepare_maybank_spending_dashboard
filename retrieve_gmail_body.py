from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.utils import parsedate_to_datetime
from email import encoders
import mimetypes
import pandas as pd
# from google_auth_oauthlib.flow import Flow, InstalledAppFlow
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
# from google.auth.transport.requests import Request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pickle
import time
import requests
import os
from bs4 import BeautifulSoup
import base64
from get_access_token import get_credentials, get_access_token

CLIENT_SECRET_FILE = 'client_secret.json'
API_NAME = 'gmail'
API_VERSION = 'v1'
SCOPES = ['https://mail.google.com/']

proxy_ip = os.environ['PROXY_IP']   
credentials_dir = os.environ['GOOGLE_CREDENTIALS_DIR']

credentials = pd.read_excel(credentials_dir, sheet_name = 'credentials')
client_id = credentials[credentials['application']=='google_client_id']['username'].values[0]
client_secret = credentials[credentials['application']=='google_client_secret']['username'].values[0]
refresh_token = credentials[credentials['application']=='google_refresh_token']['username'].values[0]

base_url = 'https://gmail.googleapis.com/gmail/v1/users/'

def list_email_message_ids(user_id, current_date, days_lookback = None, label_ids: str|list = None, filter_query = None, include_spam_trash_boxes = False, max_results: int = 500):
    creds = get_credentials()
    client_id, client_secret, refresh_token = creds.client_id, creds.client_secret, creds.refresh_token
    access_token = get_access_token(client_id, client_secret, refresh_token)
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    
    messages_list = []

    url = f'{base_url}{user_id}/messages'
    params = [('maxResults', max_results)]

    if include_spam_trash_boxes:
        params.append(('includeSpamTrash', True))

    # Filter emails by date range
    if days_lookback:
        start_dt = (current_date - timedelta(days=days_lookback))
    else:
        start_dt = (current_date - timedelta(days=1))

    end_dt = (current_date + timedelta(days=1))

    # Convert to UTC timestamps
    start_ts = int(start_dt.astimezone(timezone.utc).timestamp())
    end_ts = int(end_dt.astimezone(timezone.utc).timestamp())
    
    print(f"Filtering range between {start_dt.strftime('%d/%m/%Y %H:%M')} to {end_dt.strftime('%d/%m/%Y %H:%M')}\n")

    q = f"after:{start_ts} before:{end_ts}"
    if filter_query:
        q += f' {filter_query}'
    params.append(('q', q))

    if isinstance(label_ids, list) and len(label_ids) > 0:
        for label in label_ids:
            params.append(('labelIds', label))

    try:
        response = requests.get(url=url, headers=headers, params=params)
        response_data =  response.json()

        if 'messages' in response_data:
            messages_list = response_data['messages']

    except Exception as e:
        print('An unexpected error occured on attempting to retrieve email IDs.')
        raise e
        
    return messages_list

def extract_email_body(payload, parse_method='text'):
    """
    Extracts the email body in the specified format ('text' or 'html').
    If only HTML is found but 'text' is requested, it will strip the HTML.
    """
    def decode_base64(data):
        return base64.urlsafe_b64decode(data.encode('utf-8')).decode('utf-8')

    def find_part(parts, mime_type):
        for part in parts:
            if part.get('mimeType') == mime_type and 'data' in part.get('body', {}):
                return decode_base64(part['body']['data'])
            elif 'parts' in part:
                result = find_part(part['parts'], mime_type)
                if result:
                    return result
        return None

    # Step 1: Try to find the requested format
    mime_target = 'text/plain' if parse_method == 'text' else 'text/html'
    body = None

    if 'parts' in payload:
        body = find_part(payload['parts'], mime_target)
    elif payload.get('mimeType') == mime_target and 'data' in payload.get('body', {}):
        body = decode_base64(payload['body']['data'])

    # Step 2: Fallback - if user wants plain text but only HTML is found
    if not body and parse_method == 'text':
        # Try to find HTML and strip it
        html_body = None
        if 'parts' in payload:
            html_body = find_part(payload['parts'], 'text/html')
        elif payload.get('mimeType') == 'text/html' and 'data' in payload.get('body', {}):
            html_body = decode_base64(payload['body']['data'])

        if html_body:
            soup = BeautifulSoup(html_body, 'html.parser')
            return soup.get_text(separator='\n', strip=True)

    return body or f"[No {parse_method} body found]"


def retrieve_gmail_body(user_id, current_date, days_lookback = None, label_ids = None, return_message_id = False, parse_method = 'text', subject_filter = [], email_filter = [], include_spam_trash_boxes = False):
    """
    Function to retrieve emails in specific mailing location and restrict according to conditions

    user_id: str
        User's email address

    current_date: datetime
        Current date to start filtering for emails
    
    days_lookback: int
        Number of days from current_date to lookback and filter emails

    label_ids: list
        List of mailing locations and statuses to check for emails
    
    subject_filter: list
        User-defined string(s) to filter emails based on subject
    
    email_filter: list
        User-defined string(s) to filter emails based on sender email

    return_message_id: bool
        Whether to return message ID in dataframe output

    include_spam_trash_boxes: bool
        Whether to list out emails from the Spam and Trash mailboxes
    """
    creds = get_credentials()
    client_id, client_secret, refresh_token = creds.client_id, creds.client_secret, creds.refresh_token
    access_token = get_access_token(client_id, client_secret, refresh_token)
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}

    full_filter_query = ''

    # Filter emails by sender email if list not empty
    if len(email_filter) > 0:
        adjusted_email_filter_list = [f'from:{email}' for email in email_filter]
        email_query = ' OR '.join(adjusted_email_filter_list)
    
    # IF no emails to filter on, pass empty string to add to full_filter_query
    else:
        email_query = ''

    # Filter emails by subject if list not empty
    if len(subject_filter) > 0:
        adjusted_subject_filter_list = [f'subject:{subject}' for subject in subject_filter]
        subject_query = ' OR '.join(adjusted_subject_filter_list)
    
    # If no emails to filter on, pass empty string to add to full_filter_query
    else:
        subject_query = ''
    
    # Define full query to pass into helper function
    full_filter_query = ' '.join([email_query, subject_query]).strip()

    # Filter all emails that meet passed criteria
    messages_list = list_email_message_ids(user_id=user_id, current_date=current_date, days_lookback=days_lookback, label_ids=label_ids, include_spam_trash_boxes=include_spam_trash_boxes, filter_query=full_filter_query)

    # Initialize dataframe to store all email details 
    df = pd.DataFrame()

    # Define MIME target (whether to parse content as text or html)
    mime_target = 'text/plain' if parse_method == 'text' else 'text/html'

    for i, message in enumerate(messages_list):

        url = f"{base_url}{user_id}/messages/{message['id']}"
        
        try:
            response = requests.get(url, headers=headers)
            message_metadata = response.json()

        except Exception as e:
            raise e

        message_id = message_metadata['id']

        message_headers = message_metadata['payload']['headers']
        content = extract_email_body(message_metadata['payload'], parse_method)
        # content = ''

        # if 'parts' in message_metadata['payload']:
        #     message_main_content = message_metadata['payload']['parts']
            
        #     for part in message_main_content:
        #         if 'parts' in part:
        #             for item in part['parts']:
        #                 content += base64.urlsafe_b64decode(item['body']['data']).decode('utf-8')
        #                 content += '\n\n'

        #         elif part['mimeType'] == 'text/plain' or part['mimeType'] == 'text/html':
        #             content += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        #             content += '\n\n'

        # elif 'body' in message_metadata['payload']:
        #     message_main_content = message_metadata['payload']['body']

        #     content += base64.urlsafe_b64decode(message_main_content['data']).decode('utf-8')
        #     content += '\n\n'


        sender_email = [header['value'] for header in message_headers if header['name'].lower()=='from'][0]
        message_subject = [header['value'] for header in message_headers if header['name'].lower()=='subject'][0]
        date_received = [header['value'] for header in message_headers if header['name'].lower() == 'date'][0]
        cleaned_date = date_received.split(' (')[0].strip()

        # Normalize timezone names to numeric if needed
        for name, offset in {"GMT": "+0000", "UTC": "+0000"}.items():
            if cleaned_date.endswith(name):
                cleaned_date = cleaned_date.replace(name, offset)

        # Robust parsing
        try:
            dt = parsedate_to_datetime(cleaned_date)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            dt_myt = dt.astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
            myt_date_received = dt_myt.strftime('%Y-%m-%d %H:%M:%S')

        except Exception as e:
            print("Parsing failed for:", cleaned_date, "Error:", e)
            myt_date_received = "Invalid date"
        
        
        
        
        # date_recieved = [header['value'] for header in message_headers if header['name'].lower()=='date'][0]

        # cleaned_date = date_recieved.split(' (')[0]

        # # Determine what string format to use in extracting date components
        # if ',' in cleaned_date:
        #     date_format = "%a, %d %b %Y %H:%M:%S %Z"
        # elif '+' in cleaned_date or '-' in cleaned_date:
        #     date_format = "%d %b %Y %H:%M:%S %z"
        # else:
        #     date_format = "%d %b %Y %H:%M:%S %Z"

        # dt = datetime.strptime(cleaned_date, date_format)  # Parse with timezone
        # dt_myt = dt.astimezone(ZoneInfo("Asia/Kuala_Lumpur"))  # Convert to MYT
        # myt_date_recieved = dt_myt.strftime('%Y-%m-%d %H:%M:%S')

        if return_message_id:
            row_df = pd.DataFrame([[message_id, myt_date_received, sender_email, message_subject, content]], 
                                columns = ['Id', 'Date Recieved', 'Sender Email', 'Subject', 'Body'])
        
        else:
            row_df = pd.DataFrame([[myt_date_received, sender_email, message_subject, content]], 
                                columns = ['Date Recieved', 'Sender Email', 'Subject', 'Body'])
            

        df = pd.concat([df, row_df], axis=0, ignore_index=True)
        print(f"{dt_myt.strftime('%d%m%Y - %H%M%S')} | {message_subject}")

    return df # messages_list

    

    




