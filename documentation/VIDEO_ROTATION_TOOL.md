# Video Rotation Tool

## Overview
The Video Rotation tool allows users to rotate video files by 90° clockwise, 90° counter-clockwise, or 180°. It uses FFmpeg for high-quality video processing while preserving audio tracks.

## Features
- ✅ Rotate videos by 90° clockwise
- ✅ Rotate videos by 90° counter-clockwise  
- ✅ Rotate videos by 180° (flip upside down)
- ✅ Preserves original video quality
- ✅ Maintains audio tracks
- ✅ Supports all common video formats

## Supported Formats
- MP4
- AVI
- MOV
- MKV
- WEBM
- FLV
- WMV
- M4V
- MPG/MPEG
- 3GP

## File Size Limit
Maximum file size: **500 MB**

## Implementation Details

### Backend
- **File**: `apps/tools/plugins/video_rotation.py`
- **Class**: `VideoRotation` (inherits from `BaseTool`)
- **Processing**: Uses FFmpeg with `transpose` filter
- **Encoding**: H.264 codec with CRF 23 (balanced quality/size)
- **Audio**: Preserved without re-encoding

### Frontend
- **Template**: `templates/tools/video_rotation.html`
- **UI**: Bootstrap 5 with interactive rotation selection buttons
- **Processing**: Synchronous (returns file directly after rotation)

### API Endpoints
- `GET /api/v1/tools/` - List all tools (includes video-rotation)
- `GET /api/v1/tools/video-rotation/` - Get tool metadata
- `POST /api/v1/tools/video-rotation/convert/` - Rotate video

### Tests
- **File**: `tests/test_video_rotation.py`
- **Coverage**: Tool validation, processing, cleanup, API endpoints
- **Mocking**: FFmpeg execution mocked for unit tests

## FFmpeg Command Examples

### 90° Clockwise
```bash
ffmpeg -i input.mp4 -vf transpose=1 -c:a copy -c:v libx264 -preset fast -crf 23 output.mp4
```

### 90° Counter-Clockwise
```bash
ffmpeg -i input.mp4 -vf transpose=2 -c:a copy -c:v libx264 -preset fast -crf 23 output.mp4
```

### 180°
```bash
ffmpeg -i input.mp4 -vf transpose=2,transpose=2 -c:a copy -c:v libx264 -preset fast -crf 23 output.mp4
```

## Usage

### Web Interface
1. Navigate to the Video Rotation tool
2. Upload a video file (max 500 MB)
3. Select rotation angle:
   - 90° Clockwise (rotate right)
   - 90° Counter-Clockwise (rotate left)
   - 180° (flip upside down)
4. Click "Rotate Video"
5. Download the rotated video

### API Usage
```bash
# Rotate video 90° clockwise
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@video.mp4" \
  -F "rotation=90_cw" \
  https://your-domain.com/api/v1/tools/video-rotation/convert/ \
  -o rotated_video.mp4
```

#### Rotation Parameters
- `90_cw` - 90 degrees clockwise
- `90_ccw` - 90 degrees counter-clockwise
- `180` - 180 degrees

## Dependencies

### System Requirements
- **FFmpeg** must be installed on the system
- Added to Dockerfile: `ffmpeg` package

### Python Requirements
- No additional Python packages required
- Uses Python's built-in `subprocess` module

## Tool Registration
The tool is automatically discovered and registered by the tool registry system in `apps/tools/registry.py`. No manual registration is required.

## Error Handling
- File size validation (max 500 MB)
- File format validation (only supported video formats)
- FFmpeg installation check
- FFmpeg execution timeout (5 minutes)
- Temporary file cleanup on success or failure

## Performance Considerations
- Processing time depends on video size, quality, and system resources
- Typical processing time: 2-5 minutes for a 100 MB video
- Memory usage: ~2x the video file size during processing
- Disk space: Requires space for input + output + temp files

## Future Enhancements
- [ ] Add support for custom rotation angles (not just 90°/180°)
- [ ] Add option to preserve or re-encode video codec
- [ ] Add video quality/bitrate selection
- [ ] Add batch video rotation
- [ ] Add video preview before/after rotation
- [ ] Add progress percentage during processing
- [ ] Add option to rotate only video stream (keep audio orientation)

## Troubleshooting

### FFmpeg Not Found
If you see "FFmpeg is not installed" error:
- **Local development**: Install FFmpeg via `apt-get install ffmpeg` (Linux) or `brew install ffmpeg` (macOS)
- **Docker**: FFmpeg is included in the Dockerfile
- **Azure Container Apps**: FFmpeg is installed in the container image

### Processing Timeout
If rotation times out after 5 minutes:
- Check video file size (max 500 MB)
- Check video codec complexity
- Increase timeout in `video_rotation.py` if needed

### Output File Empty
If the rotated video file is empty or corrupted:
- Check FFmpeg logs in application logs
- Verify input video is valid and not corrupted
- Check disk space availability
