from langchain.agents import tool

# @tool
class calendar_event:
    def __init__(self, event_time, event_name: str):
        self.time = event_time
        self.name = event_name
        
    def __repr__(self):
        return f"Event: {self.name} at {self.time}"

import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.oauth2.credentials

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def authenticate_google_calendar() -> google.oauth2.credentials.Credentials:
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
    creds = authenticate_google_calendar()
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

TOOLS = [get_calendar_events]
# def main():
#     creds = authenticate_google_calendar()
#     upcoming_events = 10
#     events = get_calendar_events(creds, upcoming_events)
#     print(events)


# if __name__ == "__main__":
#   main()

    
