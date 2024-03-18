import os
import subprocess
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Google Drive API credentials
CLIENT_ID = '135434687674-f2rkhlp37dd51lik6h6h6p3at0lktckr.apps.googleusercontent.com'
CLIENT_SECRET = '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'
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Directory to store downloaded videos
VIDEO_DIR = 'videos'

def authenticate_google_drive():
    print("Authenticating Google Drive...")
    creds = None

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        print("No valid credentials found or credentials expired.")
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(os.getcwd(), 'credentials.json'), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
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
    downloaded_videos = []
    if not os.path.exists(VIDEO_DIR):
        os.makedirs(VIDEO_DIR)

    # Get list of existing local video files
    existing_local_videos = [os.path.join(VIDEO_DIR, file) for file in os.listdir(VIDEO_DIR) if file.endswith('.mp4')]

    # Extract video names from the list of videos
    video_names = [video['name'] for video in videos]

    # Check for videos that were previously downloaded but are no longer in the Google Drive album
    for local_video in existing_local_videos:
        video_name = os.path.basename(local_video)
        if video_name not in video_names:
            print(f"Video '{video_name}' has been removed from the Google Drive album. Removing local copy.")
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
            downloaded_videos.append(video_path)
        else:
            print(f"Video already downloaded: {video_name}")
            downloaded_videos.append(video_path)

    print("Downloading complete.")
    return downloaded_videos

def create_playlist(videos):
    playlist_path = os.path.join(VIDEO_DIR, 'playlist.m3u')
    with open(playlist_path, 'w') as playlist_file:
        for video in videos:
            playlist_file.write(f"{os.path.abspath(video)}\n")
    return playlist_path

def play_videos_in_vlc(playlist_path):
    print(f"Playing videos in VLC: {playlist_path}")
    vlc_exe = r"/usr/bin/vlc"  # Path to VLC executable on Raspberry Pi
    subprocess.Popen([vlc_exe, '--fullscreen', '--loop', playlist_path])

def main():
    creds = authenticate_google_drive()
    service = build(API_NAME, API_VERSION, credentials=creds)

    # Replace 'YOUR_FOLDER_ID' with the actual ID of your Google Drive folder
    folder_id = '1RXsEMszDRXWB1jSVUqr9551gxUDMSLJ3'

    videos = list_videos_from_drive(service, folder_id)

    if videos:
        downloaded_videos = download_videos(service, videos)
        playlist_path = create_playlist(downloaded_videos)
        play_videos_in_vlc(playlist_path)
    else:
        print("No videos found in the specified folder.")

if __name__ == '__main__':
    main()
