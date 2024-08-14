import base64
from email.message import EmailMessage
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
CLIENT_SECRETS = "client_secrets.json"
TOKENS = "token_mail.json"

def send_email( to_addresses, from_address, subject, body ):
  creds = None
  if os.path.exists( TOKENS ):
    creds = Credentials.from_authorized_user_file( TOKENS, SCOPES )
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          CLIENT_SECRETS, SCOPES
      )
      creds = flow.run_local_server(port=0)
    with open(TOKENS, "w") as token:
      token.write(creds.to_json())
  try:
    service = build("gmail", "v1", credentials=creds)
    message = EmailMessage()

    message.set_content( body )

    message["To"] = ', '.join( to_addresses )
    message["From"] = from_address
    message["Subject"] = subject

    # encoded message
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    create_message = {"raw": encoded_message}
    # pylint: disable=E1101
    send_message = (
        service.users()
        .messages()
        .send(userId="me", body=create_message)
        .execute()
    )
    print(f'Message Id: {send_message["id"]}')
  except HttpError as error:
    print(f"An error occurred: {error}")
    send_message = None
  return send_message
