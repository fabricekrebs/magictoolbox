# Video Rotation Workflow Update

**Date**: 2025-12-09  
**Change**: Modified video rotation workflow to upload-first, then edit from blob storage

## Summary

Changed the video rotation tool from a single-step "upload + process" workflow to a two-step workflow:
1. **Upload**: User uploads video to blob storage (no processing)
2. **Select & Rotate**: User selects an uploaded video and applies rotation

## Changes Made

### 1. Backend - New API Endpoints (`apps/tools/views.py`)

Added three new `@action` methods to `ToolViewSet`:

#### `upload_video` (POST `/api/v1/tools/video-rotation/upload-video/`)
- Accepts video file upload without processing
- Saves to `video-uploads` container with metadata (user_id, original_filename, file_size, uploaded_at)
- Generates unique video_id (UUID)
- Returns: `{video_id, filename, blob_name, size, message}`

#### `list_videos` (GET `/api/v1/tools/video-rotation/list-videos/`)
- Lists all uploaded videos for the current user
- Filters by user_id in blob metadata
- Returns: `{videos: [{video_id, filename, size, uploaded_at, blob_name}, ...]}`

#### `rotate_video_from_blob` (POST `/api/v1/tools/video-rotation/rotate-video/`)
- Accepts `{video_id, rotation}` payload
- Finds blob by video_id and verifies user ownership
- Creates `ToolExecution` record
- Triggers Azure Function to process existing blob
- Returns: `{execution_id, video_id, filename, rotation, status, statusUrl, message}`

### 2. Frontend - Updated Template (`templates/tools/video_rotation.html`)

Reorganized UI into two-step workflow:

#### Step 1: Upload Video (Card 1)
- Simple file upload form
- Upload button triggers `upload-video` endpoint
- Shows upload progress/status
- No rotation selection at this stage

#### Step 2: Select & Rotate Video (Card 2)
- Lists all user's uploaded videos with refresh button
- Videos displayed as clickable list items showing filename, size, upload date
- Selecting a video:
  - Highlights the video in the list
  - Shows rotation form with 90° CW, 90° CCW, 180° options
  - Scrolls to rotation controls
- Rotate button triggers `rotate-video` endpoint

#### JavaScript Updates
- `loadVideos()`: Fetches and displays video list
- `selectVideo(videoId, videoName)`: Handles video selection
- `uploadForm.submit`: Handles video upload, then refreshes list
- `rotationForm.submit`: Sends rotation request for selected video
- `formatFileSize()`: Helper function for human-readable file sizes
- Status polling and progress tracking remain unchanged

### 3. Updated Information Sidebar
- Modified "How It Works" section to reflect new 6-step workflow
- Added "Step 1" and "Step 2" labels for clarity

## Technical Details

### Blob Storage Structure
```
video-uploads/
  └── video/{uuid}.{ext}  (e.g., video/a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp4)
      metadata:
        - user_id: "123"
        - original_filename: "my_video.mp4"
        - file_size: "12345678"
        - uploaded_at: "2025-12-09 12:30:00"
```

### API Authentication
- All three new endpoints require authentication
- Use session-based auth (Django sessions) or JWT tokens
- Return 401 if not authenticated
- Return 404 if video not found or user doesn't own it

### Azure Function Integration
- `rotate_video_from_blob` triggers existing Azure Function endpoint
- Function receives: `{execution_id, blob_name, rotation}`
- Function processes video from blob, uploads to `video-processed` container
- Status polling uses existing `/api/v1/executions/{id}/status/` endpoint

## Benefits of New Workflow

1. **Better UX**: Users can upload videos once and apply multiple transformations
2. **Efficiency**: No need to re-upload for different rotations
3. **Management**: Users can see all their uploaded videos in one place
4. **Scalability**: Foundation for adding more video operations (crop, trim, etc.)
5. **Storage Optimization**: Uploaded videos can be reused, processed videos are separate

## Testing

### Manual Testing Steps
1. Navigate to: http://localhost:8000/tools/video-rotation/
2. **Step 1**: Upload a video file (supports MP4, AVI, MOV, MKV, WEBM, etc.)
3. Wait for "Upload successful!" message
4. **Step 2**: Click refresh if needed, see video in list
5. Click on video to select it
6. Choose rotation angle (90° CW, 90° CCW, or 180°)
7. Click "Rotate Video"
8. Monitor progress bar
9. Download rotated video when complete

### API Testing
```bash
# 1. Upload video
curl -X POST http://localhost:8000/api/v1/tools/video-rotation/upload-video/ \
  -H "X-CSRFToken: <csrf_token>" \
  -F "file=@/path/to/video.mp4" \
  --cookie "csrftoken=<csrf_token>;sessionid=<session_id>"

# 2. List videos
curl http://localhost:8000/api/v1/tools/video-rotation/list-videos/ \
  --cookie "sessionid=<session_id>"

# 3. Rotate video
curl -X POST http://localhost:8000/api/v1/tools/video-rotation/rotate-video/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <csrf_token>" \
  -d '{"video_id":"<uuid>","rotation":"90_cw"}' \
  --cookie "csrftoken=<csrf_token>;sessionid=<session_id>"

# 4. Check status
curl http://localhost:8000/api/v1/executions/<execution_id>/status/ \
  --cookie "sessionid=<session_id>"
```

## Files Modified

1. `/home/krfa/git-repo/magictoolbox/apps/tools/views.py` (Added 3 new actions)
2. `/home/krfa/git-repo/magictoolbox/templates/tools/video_rotation.html` (Reorganized UI)

## Backward Compatibility

- Old `/api/v1/tools/video-rotation/convert/` endpoint still exists
- Existing video rotation functionality preserved
- Azure Function `rotate_video` endpoint unchanged
- Database schema unchanged (uses existing `ToolExecution` model)

## Next Steps (Future Enhancements)

1. Add video preview thumbnails in the list
2. Add delete video functionality
3. Add video metadata (duration, resolution, codec)
4. Support batch operations (rotate multiple videos)
5. Add more video operations (trim, crop, resize, etc.)
6. Implement video expiration (auto-delete after X days)
7. Add video sharing/download links

## Deployment Notes

- Ensure Azure Blob Storage containers exist: `video-uploads`, `video-processed`
- No database migrations required
- Django restart required to pick up code changes
- Azure Functions deployment unchanged
