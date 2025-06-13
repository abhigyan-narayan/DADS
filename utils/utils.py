import requests
import re
import json
import os
from dotenv import load_dotenv
import tempfile
from flask import send_file

load_dotenv()
API_KEY = os.environ.get("API_KEY")
CONFIG_PATH = "config.json"

def youtube_info_batch(video_ids):
    video_details = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        ids_str = ",".join(batch)
        url = f'https://www.googleapis.com/youtube/v3/videos?part=snippet&id={ids_str}&key={API_KEY}'
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200:
            print("YouTube API error:", response.status_code, response.text)
            raise RuntimeError("Site is currently down since YouTube API service is unavailable.")
        if "error" in data:
            print("YouTube API error:", data["error"])
            raise RuntimeError("Site is currently down since YouTube API service is unavailable.")

        for item in data.get('items', []):
            snippet = item['snippet']
            video_details.append({
                "video_id": item['id'],
                "title": snippet['title']
            })
    return video_details


def get_playlist_videos(playlist_id=None):
    video_ids = []
    page_token = ''

    while True:
        url = (
            f'https://www.googleapis.com/youtube/v3/playlistItems'
            f'?part=contentDetails&maxResults=50&playlistId={playlist_id}&key={API_KEY}&pageToken={page_token}'
        )
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200:
            print("YouTube API error:", response.status_code, response.text)
            raise RuntimeError("Site is currently down since YouTube API service is unavailable.")
        if "error" in data:
            print("YouTube API error:", data["error"])
            raise RuntimeError("Site is currently down since YouTube API service is unavailable.")

        for item in data.get('items', []):
            video_ids.append(item['contentDetails']['videoId'])
        
        page_token = data.get('nextPageToken', '')
        if not page_token:
            break
    return video_ids


def update_video_ids():
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    playlists = config.get("playlists", {})
    video_ids = {}

    for page, playlist_ids in playlists.items():
        temp_video_id = []
        for playlist_id in playlist_ids:
            temp_video_id.extend(get_playlist_videos(playlist_id))
        video_ids[page] = temp_video_id

    config["video_ids"] = video_ids

    # Write to a temporary file for download
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w")
    json.dump(config, temp, indent=2)
    temp.close()

    return send_file(temp.name, as_attachment=True, download_name="updated_config.json", mimetype="application/json")


def youtube_info_batch_with_links(video_ids):
    """
    Fetches video details and extracts links from descriptions for a batch of video IDs.
    Returns a list of dicts with video_id, title, links_with_headings, links_without_headings.
    """
    video_details = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        ids_str = ",".join(batch)
        url = f'https://www.googleapis.com/youtube/v3/videos?part=snippet&id={ids_str}&key={API_KEY}'
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200:
            print("YouTube API error:", response.status_code, response.text)
            raise RuntimeError("Site is currently down since YouTube API service is unavailable.")
        if "error" in data:
            print("YouTube API error:", data["error"])
            raise RuntimeError("Site is currently down since YouTube API service is unavailable.")

        for item in data.get('items', []):
            snippet = item['snippet']
            description = snippet.get('description', '')

            matches = re.findall(r'([^\n:-]+)\s*[:\-]\s*(https?://[^\s]+)', description)
            links_with_headings = [{"heading": heading.strip(), "link": link} for heading, link in matches]
            all_links = set(re.findall(r'(https?://[^\s]+)', description))
            links_with_headings_set = set(link["link"] for link in links_with_headings)
            links_without_headings = [{"link": link} for link in all_links - links_with_headings_set]
            video_details.append({
                "video_id": item['id'],
                "title": snippet['title'],
                "links_with_headings": links_with_headings,
                "links_without_headings": links_without_headings
            })
    return video_details