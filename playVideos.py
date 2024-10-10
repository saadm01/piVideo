import os
import subprocess
import socket
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Google Drive API credentials
CLIENT_ID = '135434687674-f2rkhlp37dd51lik6h6h6h3at0lktckr.apps.googleusercontent.com'
CLIENT_SECRET = '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'
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Directory to store downloaded videos
VIDEO_DIR = 'videos'

def log_current_time():
    """Print the current date and time."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Script started at: {current_time}")

def is_internet_available():
    try:
        socket.create_connection(("8.8.8.8", 53))
        return True
    except OSError:
        return False

def authenticate_google_drive():
    print("Authenticating Google Drive...")
    creds = None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')

    if not creds or not creds.valid:
        print("No valid credentials found or credentials expired.")
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(os.getcwd(), 'credentials.json'), SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    print("Authentication successful.")
    return creds

def list_videos_from_drive(service, folder_id):
    print("Listing videos from Google Drive...")
    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='video/mp4' and trashed=false",
        fields="files(id, name)"
    ).execute()

    drive_videos = results.get('files', [])
    print(f"Found {len(drive_videos)} videos on Google Drive.")
    return drive_videos

def download_videos(service, videos):
    print("Downloading videos...")
    if not os.path.exists(VIDEO_DIR):
        os.makedirs(VIDEO_DIR)

    existing_local_videos = [os.path.join(VIDEO_DIR, file) for file in os.listdir(VIDEO_DIR) if file.endswith('.mp4')]
    video_names = [video['name'] for video in videos]

    for local_video in existing_local_videos:
        video_name = os.path.basename(local_video)
        if video_name not in video_names:
            print(f"Removing local copy of deleted video: {video_name}")
            os.remove(local_video)

    for video in videos:
        video_name = video['name']
        video_id = video['id']
        video_path = os.path.join(VIDEO_DIR, video_name)

        if not os.path.exists(video_path):
            print(f"Downloading video: {video_name}")
            request = service.files().get_media(fileId=video_id)
            with open(video_path, 'wb') as file:
                downloader = MediaIoBaseDownload(file, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            print(f"Downloaded video: {video_name}")
        else:
            print(f"Video already downloaded: {video_name}")

    print("Download complete.")

def play_videos_in_vlc(videos):
    print("Playing videos in VLC...")
    vlc_exe = r"/usr/bin/vlc"
    for video in videos:
        print(f"Playing video: {video}")
        subprocess.Popen([vlc_exe, '--fullscreen', '--no-video-title-show', '--loop', '--no-audio', video])

def main():
    log_current_time()  # Log the current time and date

    # Check if internet is available
    if is_internet_available():
        creds = authenticate_google_drive()
        service = build(API_NAME, API_VERSION, credentials=creds)
        
        # Replace 'YOUR_FOLDER_ID' with the actual ID of your Google Drive folder
        folder_id = '1RXsEMszDRXWB1jSVUqr9551gxUDMSLJ3'
        videos = list_videos_from_drive(service, folder_id)
        
        if videos:
            download_videos(service, videos)
        else:
            print("No videos found in the specified folder.")
    else:
        print("No internet connection. Skipping Google Drive sync.")

    # Play local videos
    local_videos = [os.path.join(VIDEO_DIR, f) for f in os.listdir(VIDEO_DIR) if f.endswith('.mp4')]
    if local_videos:
        play_videos_in_vlc(local_videos)
    else:
        print("No local videos to play.")

if __name__ == '__main__':
    main()
