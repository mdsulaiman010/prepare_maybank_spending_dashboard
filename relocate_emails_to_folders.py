from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import mimetypes
import pandas as pd
# from google_auth_oauthlib.flow import Flow, InstalledAppFlow
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
# from google.auth.transport.requests import Request
from datetime import datetime, timedelta
import pickle
import time
import os
import base64
import requests
from get_access_token import get_access_token
from dotenv import load_dotenv

# Load in directory-specific environem
load_dotenv()

user_gmail = os.environ['email']

base_url = 'https://gmail.googleapis.com/gmail/v1/users/'

# Function to list all available folders
def list_all_folders(user_id):
    """
    List all folders/labels within user's Gmail

    user_id: str
        User's email address
    """
    access_token = get_access_token(user_gmail)

    url = f'{base_url}{user_id}/labels'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    try:
        response = requests.get(url=url, headers=headers)
        response_data = response.json()

        labels_list = response_data['labels']
        label_id_dict = {label['name']: label['id'] for label in labels_list}

        # print(f"No. available folders: {len(labels_list)}")
        # print([label['name'] for label in labels_list])
        return label_id_dict

    except Exception as e:
        print(f'Unexpected error occurred while attempting to list labels')
        raise e
            

# Function to create new label
def create_new_label(user_id, folder_name):
    """
    Create label within user's Gmail
    
    user_id: str
        User's email address
    """
    # creds = get_credentials()
    # client_id, client_secret, refresh_token = creds.client_id, creds.client_secret, creds.refresh_token
    access_token = get_access_token(user_gmail)

    url = f'{base_url}{user_id}/labels'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    payload = {
        'name': folder_name,
        'type': 'user'
    }

    try:
        response = requests.post(url=url, headers=headers, json=payload)
        response_data = response.json()

        if response.status_code == 200 and 'id' in response_data:
            print(f"Successfully created new folder")
            
        elif response.status_code == 409:  # Conflict error (e.g., label already exists)
            # label_id_dict = list_all_folders(access_token, user_id)
            print(f"Label already exists")
            
        else:
            print(f"Unexpected error: {response_data}")
            

    except Exception as e:
        print('Folder creation failed due to an exception')
        raise e


# Function to move email(s) between folders
def move_emails(user_id, message_ids: list, dest_folder_locs: list, remove_curr_locs=[]):
    """
    Move email between labels

    user_id: str
        User email address
    
    message_id: list
        List of unique email identifiers
    
    dest_folder_locs: list
        Destination label name needs to be contained in list format e.g. ['Sample Label']
    
    remove_curr_locs: list
        Whether to remove email from other locations it may be in upon moving
    """
    # creds = get_credentials()
    # client_id, client_secret, refresh_token = creds.client_id, creds.client_secret, creds.refresh_token
    access_token = get_access_token(user_gmail)

    # url = f"{base_url}{user_id}/messages/{message_id}/modify"
    url = f"{base_url}{user_id}/messages/batchModify"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    # Get corresponding label ID based on folder name input
    label_id_dict = list_all_folders(user_id)
    dest_label_id_list = [label_id_dict[labelname] for labelname in dest_folder_locs]     # Cannot have any core locations in this list (i.e. SPAM, INBOX, SENT, etc.)
    
    body = {
        'ids': message_ids,
        'addLabelIds': dest_label_id_list
    }

    # Attempt to move folder from current location to destination while remove current locations
    if len(remove_curr_locs) > 0:
        curr_label_id_list = [label_id_dict[labelname] for labelname in remove_curr_locs]
        body['removeLabelIds'] = curr_label_id_list
        remove_msg = f' and removed from the following folders: {remove_curr_locs}'

    try:
        response = requests.post(url=url, headers=headers, json=body)
        # response_data = response.json()

        if response.status_code == 204:
            response_msg = f"Successfully copied provided email IDs to {dest_folder_locs}"

            if remove_curr_locs:
                response_msg += remove_msg
            
            print(response_msg)
        

        else:
            print(response)

    except Exception as e:
        print('An unexpected error occured when moving email to another folder.')
        raise e

# Function to delete email from a folder
def remove_label(user_id, label_name):
    """
    Remove label from user's Gmail

    user_id: str
        User's email address

    label_name
    """
    # creds = get_credentials()
    # client_id, client_secret, refresh_token = creds.client_id, creds.client_secret, creds.refresh_token
    access_token = get_access_token(user_gmail)
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    # Get corresponding label ID for passed folder name
    label_id_dict = list_all_folders(user_id)
    label_id = label_id_dict.get(label_name)

    if not label_id:
        print('Label does not exist.')
        return None
    else:
        url = f'{base_url}{user_id}/labels/{label_id}'

    try:
        response = requests.delete(url=url, headers=headers)
        
        if response.status_code == 204:
            print('Folder successfully deleted')
        
        else:
            print(response)

    except Exception as e:
        print('An unexpected error occured when moving email to another folder.')
        raise e

    
    