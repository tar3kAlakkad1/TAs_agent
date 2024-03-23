from langchain.agents import tool
from bs4 import BeautifulSoup
import base64


class calendar_event:
    def __init__(self, event_time, event_name: str):
        self.time = event_time
        self.name = event_name
        
    def __repr__(self):
        return f"Event: {self.name} at {self.time}"
    
class email_message:
    def __init__(self, sender: str, date, subject: str, body: str):
        self.sender = sender
        self.date = date
        self.subject = subject
        self.body = body
        
    def __repr__(self):
        return f"\n\nFrom: {self.sender}\nDate: {self.date}\nSubject: {self.subject}\nContent:\n\n{self.body}\n\nEnd of email message.\n\n"

import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.oauth2.credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/calendar.readonly", "https://www.googleapis.com/auth/gmail.modify"]


def print_emails(emails: list) -> None:
    for email in emails:
        try:
            print(email, end="\n\n")
        except UnicodeEncodeError:
            print(f"Coudn't print an email due to unicode error!")


def authenticate() -> google.oauth2.credentials.Credentials:
    creds = None
    
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port = 0)
            
        with open("token.json", "w") as token:
            token.write(creds.to_json())
            
    return creds        

@tool
def get_calendar_events(upcoming_k_events: int) -> list:
    """Returns list of upcoming k calendar events"""
    creds = authenticate()
    all_events = []
    try:
        service = build("calendar", "v3", credentials=creds)
        
        now = datetime.datetime.utcnow().isoformat() + "Z" # 'Z' indicates UTC
        
        print(f"Getting the upcoming {upcoming_k_events} events")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=upcoming_k_events,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return []

        # Prints the start and name of the next 10 events
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            name = event["summary"]

            new_event = calendar_event(start, name)
            all_events.append(new_event)

        return all_events
            
    except HttpError as e:
        print(f"An error occurred: {e}")
        return []

@tool
def get_unread_emails(recent_k_emails=10, past_k_days=7):
    """
    A function that returns the most recent k emails in the past k days. Default is recent 10 
    emails in past 7 days.
    
    If there are no new emails, the function returns a string that says no new emails. 
    
    Otherwise, returns a list of email objects with a special __repr__.
    """
    creds = authenticate()
    
    labels = ['INBOX', 'UNREAD']
    unread_emails = []
    
    try:
        service = build("gmail", "v1", credentials=creds)
        unread_messages  = service.users().messages().list(userId="me", labelIds=labels, maxResults=recent_k_emails, q=f"newer_than:{past_k_days}d").execute()
        
        if unread_messages['resultSizeEstimate'] == 0:
            return "No new emails"
        msgs = unread_messages['messages']
        print(f"Total unread messages in inbox: ", str(len(msgs)))
        
        for msg in msgs:
            
            msg_id = msg['id']
            email = service.users().messages().get(userId="me", id=msg_id).execute()
            payload = email['payload']
            header = payload['headers']
            
            sender = ''
            date = ''
            subject = ''
            body_content = ''
            
            for meta in header:
                if date and sender and subject:
                    break
                if meta['name'] == 'From':
                    sender = meta['value'] 
                elif meta['name'] == 'Subject':
                    subject = meta['value']
                elif meta['name'] == 'Date':
                    date = meta['value']
                else:
                    continue
                
            try:
                email_parts = payload['parts']
                part_one = email_parts[0]
                body = part_one['body']
                body_data = body['data']
                    
                body_data = body_data.replace("-", "+")
                body_data = body_data.replace("_", "/")
                body_data = base64.b64decode(bytes(body_data, 'UTF-8'))
                    
                soup = BeautifulSoup(body_data, 'lxml')
                body_content = soup.body()
            except Exception as e:
                print(f"Could not get email content. This is probably due to an empty email. Error: {e}")
                body_content = ''
                
            email = email_message(sender, date, subject, body_content)
            unread_emails.append(email)
            service.users().messages().modify(userId="me", id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
    
        print(f"Total emails retrieved: {len(unread_emails)}.")
        print_emails(unread_emails)
        
    except HttpError as error:
        print(f"An HTTP error occurred: {error}")
        
    return unread_emails

TOOLS = [get_calendar_events, get_unread_emails]