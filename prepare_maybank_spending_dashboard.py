import pandas as pd
from datetime import datetime
from relocate_emails_to_folders import move_emails, list_all_folders
from retrieve_gmail_attachments import retrieve_gmail_attachments
from retrieve_gmail_body import retrieve_gmail_body
from google_drive_file_mgmt import google_drive_add_folder, google_drive_upload_file, google_drive_get_link
from send_gmail_message import send_email_gmail
from pypdf import PdfReader
import os
import re
import time
import calendar
import shutil
from dotenv import load_dotenv
load_dotenv('.env')

# Define timing parameters
today = datetime.today()
current_year = today.year
max_retries = 5

# Create Downloads local directory
download_dir = os.path.join(os.getcwd(), 'Downloads')
os.makedirs(download_dir, exist_ok=True)

# Define relevant credentials
sender_email = os.environ['EMAIL']
statement_pw = os.environ['MAYBANK_STMT_PW']

root_folder = 'SULAIMAN FINANCING'

# List of relevant email addresses from Maybank
relevant_maybank_emails = ['m2u@maybank.com.my', "m2u@bills.maybank2u.com.my", "m2u@stmts.maybank2u.com.my", 'maybankard@edm.maybank2u.com.my']

# Move outstanding Maybank emails into designated folder
maybank_df = retrieve_gmail_body(sender_email, today, 32, ['INBOX'], True, email_filter=relevant_maybank_emails)
if maybank_df.empty:
    print('No new emails found to move.')
else:
    move_emails(sender_email, maybank_df['Id'].to_list(), ['MayBank'], ['INBOX'])

# Download monthly statement
statement_files = retrieve_gmail_attachments(sender_email, today, 32, 'MayBank', subject_filter=["Savings Account Statement "])

if len(statement_files) == 0:
    print('No MayBank statements found this month.')
else:
    for file in statement_files:
        latest_statement_fn = file # statement_files[0]
        reader = PdfReader(os.path.join(download_dir, latest_statement_fn))
        statement_date = latest_statement_fn.split('_')[1]

        statement_year, statement_month, statement_day = statement_date[0:4], statement_date[4:6], statement_date[6:]

        month_number = int(statement_month)
        month_name = calendar.month_name[month_number]

        statements_foldername = f'{statement_year} Debit Statements'
        statements_gdrive_folderpath = f'{root_folder}/{statements_foldername}'

        # Add new folder for the year if does not exist
        for i in range(max_retries):
            try:
                google_drive_add_folder(statements_gdrive_folderpath)
                break
            except Exception as e:
                if i < max_retries - 1:
                    print('Retrying file upload to Google Drive...')
                    time.sleep(2)
                else:
                    raise

        # Decrypt document password
        if reader.is_encrypted:
            reader.decrypt(statement_pw)

        # Extract content from statement PDF
        full_content = ''
        for page_num, page in enumerate(reader.pages):
            full_content += page.extract_text()

        while '  ' in full_content:
            full_content = full_content.replace('  ', ' ')

        # Determine beginnign balance, total debit and credit for month
        initial_amount_found = re.search(r'BEGINNING\sBALANCE\s([\d.,]+)', full_content).group(1)
        initial_amount = float(initial_amount_found.replace(',', ''))

        actual_total_debit = re.search(r'TOTAL DEBIT\s+:\s+([\d,\.]+)', full_content).group(1)
        actual_total_debit = float(actual_total_debit.replace(',', ''))

        actual_total_credit = re.search(r'TOTAL CREDIT\s+:\s+([\d,\.]+)', full_content).group(1)
        actual_total_credit = float(actual_total_credit.replace(',', ''))

        # Define regex dictionary for all relevant details extracted row-wise from statement
        regex_pattern_dict = {
            'payment_date': r'\d{2}/\d{2}/\d{2}',
            'transaction_description': r'[A-Za-z\s\/\-,\']+',
            'amount_spent': r'[\d\.,]+',
            'net_cashflow': r'[-+]',
            'remaining_amount': r'[\d\.,]+',
            'transaction_description_add': r'[A-Za-z\s\',\-\/\*]+'
        }
        main_details_pattern = re.compile(r'(\d{2}/\d{2}/\d{2})\s+([A-Za-z\s\/\-,\']+)([\d\.,]+)([-+])\s*([\d\.,]+)(?:[\n\t\r\s]+(?!(?:\d{2}/\d{2}/\d{2}))(.+))?')

        # Extract all transaction with corresponding details
        rows = re.findall(main_details_pattern, full_content)
        colnames = ['Transaction Date', 'Transaction Description', 'Amount', 'Cash Flow', 'Remaining Amount', 'Transaction Description (2)']

        # Validate that extracted rows total amount equates to actual debit and credit amount (regex limitation)
        total_debit = 0; total_credit = 0
        for row in rows:
            transaction_amount = float(row[2].replace(',', ''))

            if '-' == row[3]:
                total_debit += transaction_amount

            elif '+' == row[3]:
                total_credit += transaction_amount

        negative_cashflow_complete = round(total_debit, 2) == actual_total_debit
        positive_cashflow_complete = round(total_credit, 2) == actual_total_credit

        if negative_cashflow_complete and positive_cashflow_complete:
            print('Number of rows extracted consistent with statement.')

            spending_records_df = pd.DataFrame(rows, columns=colnames)

            def remove_excess_whitespace(text):
                text = text.replace('\n', '')
                while '  ' in text:
                    text = text.replace('  ', ' ')
                return text

            spending_records_df['Transaction Description'] = spending_records_df['Transaction Description'] + ' ' + spending_records_df['Transaction Description (2)']

            spending_records_df['Transaction Description'] = spending_records_df['Transaction Description'].apply(remove_excess_whitespace)
            spending_records_df['Transaction Description (2)'] = spending_records_df['Transaction Description (2)'].apply(remove_excess_whitespace).str.strip()


            spending_records_df['Transaction Date'] = pd.to_datetime(spending_records_df['Transaction Date'], format='%d/%m/%y', errors='coerce', dayfirst=True)
            spending_records_df['Transaction Day'] = spending_records_df['Transaction Date'].dt.strftime('%A')
            spending_records_df['Transaction Date'] = spending_records_df['Transaction Date'].dt.strftime('%d-%m-%Y')

            spending_records_df['Amount'] = spending_records_df['Amount'].str.replace(',', '').astype(float)
            spending_records_df['Remaining Amount'] = spending_records_df['Remaining Amount'].str.replace(',', '').astype(float)

            output_fn = f'{statement_month}{statement_year}_Maybank_transactions.xlsx'
            spending_records_df.to_excel(os.path.join(download_dir, output_fn), index=False)

            for i in range(max_retries):
                try:
                    # Upload Excel to Google drive
                    google_drive_upload_file(os.path.join(download_dir, output_fn), statements_gdrive_folderpath, delete_sourcefile=True)

                    # Get direct link to Google sheet 
                    document_link = google_drive_get_link(statements_gdrive_folderpath, output_fn)
                    break
                except Exception as e:
                    if i < max_retries - 1:
                        print('Retrying file upload to Google Drive...')
                        time.sleep(2)
                    else:
                        raise

            # Define email subject and body
            email_subject = f'{month_name}{statement_year} Bank Statement Transaction Compilation'
            email_body = """
            <html>
                <head></head>
                <body>
                    Dear User,
                    <br><br>
                    Your bank statement has been added to Google Drive. You can access the link below:<br>
                    <br><a href='"""

            email_body += document_link

            email_body += f"""'>{month_name}{statement_year} Savings Account Bank Statement</a>
                    <br>
                    <br>
                    Thank you.
                    <br>
                    <br>
                    Regards,
                    BBJ
                </body>
            </html>
            """

            # Send email
            for i in range(max_retries):
                try:
                    send_email_gmail(sender_email, [sender_email], [], [], email_subject, email_body, '', [])
                    break
                except Exception as e:
                    if i < max_retries - 1:
                        print(f'Attempt {i+1} failed. Resending email...')
                        time.sleep(2)
                    else:
                        print('All attempts failed.')
                        raise e

        else:
            email_subject = f'[ERROR] {month_name}{statement_year} Bank Statement Transaction Compilation'
            email_body = """
            <html>
                <head></head>
                <body>
                    Dear User,
                    <br><br>
                    I was unable to extract all transaction rows from the attached bank statement. Kindly fix the regular expression(s) used.
                    <br>
                    <br>
                    Thank you.
                    <br>
                    <br>
                    Regards,
                    BBJs
                </body>
            </html>
            """

            for i in range(max_retries):
                try:
                    send_email_gmail('mdsulaiman010@gmail.com', ['mdsulaiman010@gmail.com'], [], [], email_subject, email_body, '', [])
                    break
                except Exception as e:
                    if i < max_retries - 1:
                        print(f'Attempt {i+1} failed. Resending email...')
                        time.sleep(2)
                    else:
                        print('All attempts failed.')
                        raise e
        
        

# Remove already-processed files
for file in statement_files:
    if os.path.exists(os.path.join(download_dir, file)):
        os.remove(os.path.join(download_dir, file))
            
# Remove the __pycache__ after completing task
for root, dirs, files in os.walk('.'):
    for dir in dirs:
        if dir in ['__pycache__']:
            shutil.rmtree(os.path.join(root, dir))
            print(f"Removed {dir} directory: {os.path.join(root, dir)}")