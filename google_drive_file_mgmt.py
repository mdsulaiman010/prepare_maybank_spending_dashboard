# from google.auth.transport.requests import Request
from datetime import datetime, timedelta
import pickle
import time
import pandas as pd
import mimetypes
import json
import os
import base64
import requests
from get_access_token import get_credentials, get_access_token

CLIENT_SECRET_FILE = 'client_secret.json'
API_NAME = 'gdrive'
API_VERSION = 'v1'
SCOPES = [
    'https://mail.google.com/',  # Gmail full read/write/send/delete
    'https://www.googleapis.com/auth/drive',  # Drive full CRUD
    'https://www.googleapis.com/auth/spreadsheets',  # Google Sheets CRUD
    'https://www.googleapis.com/auth/documents',  # Google Docs CRUD
    'https://www.googleapis.com/auth/presentations',  # Google Slides CRUD
    'https://www.googleapis.com/auth/calendar'  # Google Calendar full CRUD
]

# proxy_ip = os.environ['PROXY_IP']   
credentials_dir = os.environ['GOOGLE_CREDENTIALS_DIR']
downloads_dir = os.environ['DOWNLOAD_DIR']

credentials = pd.read_excel(credentials_dir, sheet_name = 'credentials')
client_id = credentials[credentials['application']=='google_client_id']['username'].values[0]
client_secret = credentials[credentials['application']=='google_client_secret']['username'].values[0]
refresh_token = credentials[credentials['application']=='google_refresh_token']['username'].values[0]

creds = get_credentials()
client_id, client_secret, refresh_token = creds.client_id, creds.client_secret, creds.refresh_token
access_token = get_access_token(client_id, client_secret, refresh_token)

def get_drive_id(drivename, access_token):
    # Retrieve drive IDs and names associated with a site
    url = f'https://www.googleapis.com/drive/v3/drives'
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'pageSize': 100,
        'supportsAllDrives': 'true',
        'fields': 'nextPageToken, drives(id, name)'
    }
    
    while True:
        response = requests.get(url, headers)
        result = response.json()

        for drive in result.get('drives', []):
            if drive['name'] == drivename:
                return drive['id']

        if 'nextPageToken' in result:
            params['pageToken'] = result['nextPageToken']
        else:
            break

    print(f'No shared drive by the name "{drivename}" found')
    return None

def get_folder_id(foldername, access_token, drivename=None):
    url = "https://www.googleapis.com/drive/v3/files"

    headers = {'Authorization': f'Bearer {access_token}'}
    
    if foldername == '':
        return None
    else:
        params = {
            'q': f"mimeType = 'application/vnd.google-apps.folder' and name = '{foldername}' and trashed = false",
            'fields': 'files(id, name)',
            'corpora': 'user',
            'supportsAllDrives': True,
            'includeItemsFromAllDrives': True,
            'pageSize': 100
        }

        if drivename:
            drive_id = get_drive_id(drivename, access_token)
            params['corpora'] = 'drive'
            params['driveId'] = drive_id

        response = requests.get(url, headers=headers, params=params)
        files_result = response.json()['files']
        if len(files_result) > 0:
            return files_result[0]['id']
        else:
            print(f'No folders found under the name "{foldername}"')
            return None
    
def get_item_id(folder_id, filename, access_token, drivename=None):
    url = "https://www.googleapis.com/drive/v3/files"

    headers = {'Authorization': f'Bearer {access_token}'}
    
    params = {
        'fields': 'files(id, name)',
        'corpora': 'user',
        'supportsAllDrives': True,
        'includeItemsFromAllDrives': True,
        'pageSize': 100
    }
    
    params['q'] = f"mimeType != 'application/vnd.google-apps.folder'and trashed = false and name = '{filename}'"
    params['q'] += f" and '{folder_id}' in parents" if folder_id else ''

    if drivename:
        drive_id = get_drive_id(drivename, access_token)
        params['corpora'] = 'drive'
        params['driveId'] = drive_id

    response = requests.get(url, headers=headers, params=params)
    files_result = response.json()['files']
    if len(files_result) > 0:
        return files_result[0]['id']
    else:
        print(f'No items found under the name "{filename}"')
        return None
    
def google_drive_list_folders(foldername, drivename=None, return_ids=False):
    folder_id = get_folder_id(foldername, access_token, drivename)

    url = "https://www.googleapis.com/drive/v3/files"

    headers = {'Authorization': f'Bearer {access_token}'}

    params = {
        'fields': 'files(id, name)',
        'corpora': 'user',
        'supportsAllDrives': True,
        'includeItemsFromAllDrives': True,
        'pageSize': 100
    }

    params['q'] = f"mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    params['q'] += f" and '{folder_id}' in parents" if folder_id else ''

    if drivename:
        drive_id = get_drive_id(drivename, access_token)
        params['corpora'] = 'drive'
        params['driveId'] = drive_id

    response = requests.get(url, headers=headers, params=params)
    files_result = response.json()['files']

    if return_ids:
        return {item['name']:item['id'] for item in files_result}
    else:
        if len(files_result) > 0:
            available_folders = [item['name'] for item in files_result]
            return available_folders
        else:
            print(f'No existing folders found within "{foldername}" folder')
            return []
        
def google_drive_list_files(foldername, drivename=None, search_string=None):
    folder_id = get_folder_id(foldername, access_token, drivename)

    url = "https://www.googleapis.com/drive/v3/files"

    headers = {'Authorization': f'Bearer {access_token}'}

    full_search_query = f"mimeType != 'application/vnd.google-apps.folder' and trashed = false"
    full_search_query += f" and '{folder_id}' in parents" if folder_id else ''

    if search_string:
        full_search_query = full_search_query + f" and name contains '{search_string}'"
        
    params = {
        'q': full_search_query,
        'fields': 'files(id, name, mimeType)',
        'corpora': 'user',
        'supportsAllDrives': True,
        'includeItemsFromAllDrives': True,
        'pageSize': 100
    }

    if drivename:
        drive_id = get_drive_id(drivename, access_token)
        params['corpora'] = 'drive'
        params['driveId'] = drive_id

    response = requests.get(url, headers=headers, params=params)
    files_result = response.json()['files']
    
    if len(files_result) > 0:
        available_folders = [item['name'] for item in files_result]
        return available_folders
    else:
        print(f'No existing folders found within "{foldername}" folder')
        return []

def google_drive_add_folder(foldername, drivename=None):
    """
    foldername sample input: root_folder/sub_folder1/...sub_folderN/foldername
    """
    
    parts = foldername.strip('/').split('/')
    root_foldername, *intermediary_foldernames = parts

    available_folders = google_drive_list_folders(root_foldername, drivename, return_ids=True)

    if len(intermediary_foldernames) == 0:
        new_foldername = root_foldername
        parent_folder_id = get_folder_id(new_foldername, access_token)

    else:
        root_foldername, *intermediary_foldernames, new_foldername = parts
        for folder in intermediary_foldernames:
            if folder in available_folders:
                parent_folder_id = available_folders[folder]
                available_folders = google_drive_list_folders(folder, None, return_ids=True)
            else:
                print(f'Folder "{folder}" not found within path.')
                return
    
    if new_foldername in available_folders:
        print('Folder already exists')
        return
    
    else:
        url = "https://www.googleapis.com/drive/v3/files"
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        
        params = {"supportsAllDrives": True}
        body = {
            "name": new_foldername,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if len(intermediary_foldernames) == 0:
            parent_folder_id = get_folder_id(root_foldername, access_token)
        else:
            parent_folder_id = None

        if parent_folder_id:
            body["parents"] = [parent_folder_id]

        response = requests.post(url, headers=headers, json=body, params=params)

        if response.status_code == 200:
            print('Folder successfully created.')
            return

    
def google_drive_delete_item(foldername, filename=None, drivename=None):
    """
    foldername sample input: root_folder/sub_folder1/...sub_folderN/foldername
    """
    
    parts = foldername.strip('/').split('/')
    root_foldername, *intermediary_foldernames = parts

    available_folders = google_drive_list_folders(root_foldername, drivename, return_ids=True)

    if len(intermediary_foldernames) == 0:
        parent_folder_id = get_folder_id(root_foldername)
    else:
        for folder in intermediary_foldernames:
            if folder in available_folders:
                parent_folder_id = available_folders[folder]
                available_folders = google_drive_list_folders(folder, drivename, return_ids=True)
            else:
                print(f'Folder "{folder}" not found within path.')
                return
    
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {"supportsAllDrives": True}

    # Option to delete a file item
    if filename:
        item_id = get_item_id(parent_folder_id, filename, access_token, drivename)
    
    # Option to delete a full folder
    else:
        item_id = parent_folder_id

    url = f"https://www.googleapis.com/drive/v3/files/{item_id}"

    response = requests.delete(url, headers=headers, params=params)
    
    if response.status_code == 204:
        print('Item successfully deleted')
    else:
        raise

def google_drive_get_link(foldername, filename=None, drivename=None):
    parts = foldername.strip('/').split('/')
    root_foldername, *intermediary_foldernames = parts

    available_folders = google_drive_list_folders(root_foldername, drivename, return_ids=True)
    
    if len(intermediary_foldernames) == 0:
        parent_folder_id = get_folder_id(root_foldername, access_token, drivename)
    else:
        for folder in intermediary_foldernames:
            if folder in available_folders:
                parent_folder_id = available_folders[folder]
                available_folders = google_drive_list_folders(folder, drivename, return_ids=True)
            else:
                print(f'Folder "{folder}" not found within path.')
                return
    
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {"supportsAllDrives": True}
    
    if filename:
        item_id = get_item_id(parent_folder_id, filename, access_token, drivename)
    else:
        item_id = parent_folder_id


    url = f"https://www.googleapis.com/drive/v3/files/{item_id}"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        "fields": "webViewLink",
        "supportsAllDrives": True
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("webViewLink")
    else:
        print(f"Error fetching link: {response.text}")
        return None
    
def google_drive_download_file(foldername, filename, drivename=None):
    export_mapping = {
        'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
        'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',       # .docx
        'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'            # .xlsx
    }
    
    parts = foldername.strip('/').split('/')
    root_foldername, *intermediary_foldernames = parts

    available_folders = google_drive_list_folders(root_foldername, drivename, return_ids=True)
    
    if len(intermediary_foldernames) == 0:
        parent_folder_id = get_folder_id(root_foldername, access_token, drivename)
    else:
        for folder in intermediary_foldernames:
            if folder in available_folders:
                parent_folder_id = available_folders[folder]
                available_folders = google_drive_list_folders(folder, drivename, return_ids=True)
            else:
                print(f'Folder "{folder}" not found within path.')
                return
            
    item_id = get_item_id(parent_folder_id, filename, access_token, drivename)
    
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    url = f"https://www.googleapis.com/drive/v3/files/{item_id}"
    params = {
        'supportsAllDrives': True,
    }

    item_response = requests.get(url, headers=headers, params=params)    # , stream=True
    item_format = item_response.json().get('mimeType', None)
    if item_format in export_mapping:
        url = f"https://www.googleapis.com/drive/v3/files/{item_id}/export"
        params = {'mimeType': export_mapping[item_format]}
    else:
        # Other formats → use regular download
        params = {'alt': 'media'}

    response = requests.get(url, headers=headers, params=params, stream=True)
    if response.status_code == 200:
        download_path = os.path.join(downloads_dir, filename)
        with open(download_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"Successfully downloaded file.")
        return
    else:
        print(f"Failed to download file: {response.text}")
        return
    
def google_drive_upload_file(local_filepath, dest_foldername, drivename=None, delete_sourcefile=False):
    file_name = os.path.basename(local_filepath)
    mime_type = mimetypes.guess_type(local_filepath)[0] or 'application/octet-stream'

    headers = {'Authorization': f'Bearer {access_token}'}

    # Add file metadata to params dictionary
    params = {
        'name': file_name,
        'mimeType': mime_type,
        'supportAllDrives': True,
        'uploadType': 'multipart'
    }

    if dest_foldername != '':
        # Find the parent folder
        parts = dest_foldername.strip('/').split('/')
        root_foldername, *intermediary_foldernames = parts
        available_folders = google_drive_list_folders(root_foldername, drivename, return_ids=True)
        
        if not intermediary_foldernames:
            parent_folder_id = get_folder_id(root_foldername, access_token, drivename)
        else:
            for folder in intermediary_foldernames:
                if folder in available_folders:
                    parent_folder_id = available_folders[folder]
                    available_folders = google_drive_list_folders(folder, drivename, return_ids=True)
                else:
                    print(f'Folder "{folder}" not found within path.')
                    return
        
        params['parents'] = [parent_folder_id]

    with open(local_filepath, 'rb') as f:
        files = {
            'metadata': ('metadata', json.dumps(params), 'application/json'),
            'file': (file_name, f, mime_type)
        }

        url = 'https://www.googleapis.com/upload/drive/v3/files'
        response = requests.post(url, headers=headers, files=files)

    if response.status_code in (200, 201):
        print(f"Uploaded successfully: {file_name}")
        if delete_sourcefile:
            try:
                os.remove(local_filepath)
                print(f"Deleted local file: {local_filepath}")
            except OSError as e:
                print(f"Error deleting file: {e}")
            return None
    else:
        print(f"Failed to upload: {response.status_code} - {response.text}")
        return None