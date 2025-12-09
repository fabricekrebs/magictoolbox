#!/usr/bin/env python
"""
Test script for video rotation workflow:
1. Upload video
2. List videos
3. Rotate from blob
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1/tools/video-rotation"

# Get CSRF token and login
session = requests.Session()
response = session.get("http://localhost:8000/authentication/login/")
csrf_token = session.cookies.get("csrftoken")

print("=" * 60)
print("Video Rotation Workflow Test")
print("=" * 60)

# Login (assuming user fabrice@krfa-lab.com exists)
print("\n[Auth] Logging in as fabrice@krfa-lab.com...")
login_data = {
    'username': 'fabrice@krfa-lab.com',
    'password': 'admin',  # Change to actual password
    'csrfmiddlewaretoken': csrf_token
}
login_response = session.post("http://localhost:8000/authentication/login/", data=login_data)
if login_response.status_code not in [200, 302]:
    print(f"[Auth] ✗ Login failed: {login_response.status_code}")
    print("       Please ensure user fabrice@krfa-lab.com exists with password 'admin'")
    print("       Or update credentials in test script")
    exit(1)
print(f"[Auth] ✓ Logged in successfully")

# Update CSRF token after login
csrf_token = session.cookies.get("csrftoken")

# Step 1: Upload a video (create a tiny test file)
print("\n[Step 1] Creating test video file...")
test_video_path = Path("/tmp/test_video.mp4")
# Create a minimal MP4 file (just for testing upload, won't be valid for FFmpeg)
test_video_path.write_bytes(b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom' + b'\x00' * 1000)

print(f"[Step 1] Uploading test video ({test_video_path.stat().st_size} bytes)...")
with open(test_video_path, 'rb') as f:
    files = {'file': ('test_video.mp4', f, 'video/mp4')}
    headers = {'X-CSRFToken': csrf_token}
    response = session.post(f"{BASE_URL}/upload-video/", files=files, headers=headers)

print(f"[Step 1] Upload response: {response.status_code}")
if response.status_code in [200, 201]:
    upload_data = response.json()
    print(f"[Step 1] ✓ Video uploaded successfully!")
    print(f"         Video ID: {upload_data.get('video_id')}")
    print(f"         Filename: {upload_data.get('filename')}")
    print(f"         Blob name: {upload_data.get('blob_name')}")
    video_id = upload_data.get('video_id')
else:
    print(f"[Step 1] ✗ Upload failed: {response.text}")
    exit(1)

# Step 2: List videos
print("\n[Step 2] Listing uploaded videos...")
response = session.get(f"{BASE_URL}/list-videos/")
print(f"[Step 2] List response: {response.status_code}")
if response.status_code == 200:
    list_data = response.json()
    videos = list_data.get('videos', [])
    print(f"[Step 2] ✓ Found {len(videos)} video(s):")
    for video in videos:
        print(f"         - {video.get('filename')} ({video.get('video_id')})")
else:
    print(f"[Step 2] ✗ List failed: {response.text}")
    exit(1)

# Step 3: Rotate video from blob
print("\n[Step 3] Requesting rotation for video...")
payload = {
    'video_id': video_id,
    'rotation': '90_cw'
}
headers = {
    'X-CSRFToken': csrf_token,
    'Content-Type': 'application/json'
}
response = session.post(f"{BASE_URL}/rotate-video/", json=payload, headers=headers)
print(f"[Step 3] Rotate response: {response.status_code}")
if response.status_code in [200, 202]:
    rotate_data = response.json()
    print(f"[Step 3] ✓ Rotation started!")
    print(f"         Execution ID: {rotate_data.get('execution_id')}")
    print(f"         Status: {rotate_data.get('status')}")
    print(f"         Status URL: {rotate_data.get('statusUrl')}")
    
    # Check status (just once for testing)
    execution_id = rotate_data.get('execution_id')
    time.sleep(2)
    status_response = session.get(f"http://localhost:8000/api/v1/executions/{execution_id}/status/")
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"\n[Status] Current status: {status_data.get('status')}")
    
else:
    print(f"[Step 3] ✗ Rotation failed: {response.text}")
    exit(1)

print("\n" + "=" * 60)
print("✓ All workflow steps completed successfully!")
print("=" * 60)
print("\nNote: The test video is intentionally minimal and won't")
print("actually process correctly with FFmpeg. This test validates")
print("the API workflow (upload → list → rotate).")
print("\nFor full end-to-end testing, upload a real video file via")
print("the web UI at: http://localhost:8000/tools/video-rotation/")
