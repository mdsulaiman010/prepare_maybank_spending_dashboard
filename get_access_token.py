from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime
import pickle
import requests
import os

SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/calendar'
]

credentials_JSON = os.environ['GOOGLE_APPLICATION_CREDENTIALS']

# def get_credentials():
#     """Gets valid user credentials from storage or initiates authorization flow."""
#     creds = None
#     token_path = 'token.pickle'
    
#     # Load existing credentials
#     if os.path.exists(token_path):
#         with open(token_path, 'rb') as token:
#             creds = pickle.load(token)
    
#     # If credentials don't exist or are invalid, refresh or get new ones
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             # Refresh the access token using the refresh token
#             print("Refreshing access token...")
#             creds.refresh(Request())
#         else:
#             # Run the OAuth flow to get new credentials
#             print("Getting new credentials...")
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 credentials_JSON, SCOPES)
#             creds = flow.run_local_server(port=0)
        
#         # Save credentials for future use
#         with open(token_path, 'wb') as token:
#             pickle.dump(creds, token)
    
#     return creds    # can extract client ID, client secret and refresh token from this

def get_credentials():
    """Gets credentials using service account."""
    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'service_account.json')
    
    creds = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=SCOPES
    )
    
    return creds

def get_access_token(client_id, client_secret, refresh_token):
    token_url = 'https://oauth2.googleapis.com/token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    tokens = response.json()
    return tokens['access_token']


# # # NOTE: run this code to update token with new scopes. Download JSON file from google developer console
# flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
# creds = flow.run_local_server(port=0)

# print(creds.refresh_token)

# # Function to retrieve access token for Gmail API
# def get_access_token(client_secret_file, api_name, api_version, *scopes):
#     SCOPES = [scope for scope in scopes[0]]

#     # Initialize credentials and pickle file path to store access token
#     credentials = None
#     pickle_file = f'token_{api_name}_{api_version}.pickle'

#     # If credentials pickle file exists, overwrite initialized credentials with pickle file contents
#     if os.path.exists(pickle_file):
#         with open(pickle_file, 'rb') as token:
#             credentials = pickle.load(token)
    
#     # Refresh token for API requests
#     if not credentials or not credentials.valid:
#         if credentials and credentials.expired and credentials.refresh_token:
#             credentials.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
#             credentials = flow.run_local_server()

#         # Create new credentials pickle file with latest token
#         with open(pickle_file, 'wb') as token:
#             pickle.dump(credentials, token)

#     return credentials.token

def convert_to_RFC_datetime(year=1900, month=1, day=1, hour=0, minute=0):
    dt = datetime(year, month, day, hour, minute, 0).isoformat() + 'Z'
    return dt
