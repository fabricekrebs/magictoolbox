# Text Processing Tools

This document covers the Base64 Encoder/Decoder and EXIF Metadata Extractor tools.

## Base64 Encoder/Decoder

### Overview
Bidirectional Base64 encoding and decoding tool that supports both direct text input and file upload.

### Features
- **Encode**: Convert plain text to Base64
- **Decode**: Convert Base64 back to plain text  
- **Text Input**: Direct textarea input
- **File Upload**: Upload .txt files (max 10MB)
- **Copy to Clipboard**: One-click copying
- **Character Counting**: Real-time character count

### Usage

#### API Endpoint
```
POST /api/v1/tools/base64-encoder/process/
```

#### Request (Encode)
```json
{
  "mode": "encode",
  "text": "Hello World"
}
```

#### Response
```json
{
  "result": "SGVsbG8gV29ybGQ=",
  "mode": "encode",
  "operation": "encoded",
  "input_length": 11,
  "output_length": 16
}
```

#### Request (Decode)
```json
{
  "mode": "decode",
  "text": "SGVsbG8gV29ybGQ="
}
```

### Web Interface
Navigate to `/tools/base64-encoder/` for the web interface.

**Encode Tab**:
1. Enter text or upload a text file
2. Click "Encode to Base64"
3. Copy result with one click

**Decode Tab**:
1. Paste Base64 text or upload file
2. Click "Decode from Base64"
3. Copy decoded text

### File Constraints
- **Max Size**: 10MB
- **Allowed Types**: .txt, .text
- **File Upload**: Optional (can use direct text input)

---

## EXIF Metadata Extractor

### Overview
Extract EXIF metadata from images including camera settings, GPS location, timestamps, and technical details. Supports JSON and CSV export.

### Features
- **Comprehensive Extraction**: Camera, GPS, timestamp, image info
- **Multiple Formats**: JPG, PNG, TIFF, WebP, HEIC
- **GPS Coordinates**: Decimal conversion with Google Maps link
- **Export Options**: JSON and CSV formats
- **Real-time Display**: Formatted tables and expandable sections

### Usage

#### API Endpoint
```
POST /api/v1/tools/exif-extractor/extract/
```

#### Request (Extraction Only)
```http
POST /api/v1/tools/exif-extractor/extract/
Content-Type: multipart/form-data

file: <image_file>
```

#### Request (With Export)
```http
POST /api/v1/tools/exif-extractor/extract/
Content-Type: multipart/form-data

file: <image_file>
export_format: json  # or 'csv'
```

#### Response
```json
{
  "image_info": {
    "Filename": "IMG_1234.jpg",
    "Format": "JPEG",
    "Width": 4032,
    "Height": 3024,
    "Size": "4032 x 3024",
    "FileSize": "2.45 MB"
  },
  "exif_data": {
    "Make": "Canon",
    "Model": "Canon EOS 5D Mark IV",
    "DateTime": "2024:12:14 10:30:45",
    "ISOSpeedRatings": "100",
    "FNumber": "2.8",
    "ExposureTime": "1/250",
    "FocalLength": "50.0 mm"
  },
  "gps_data": {
    "DecimalLatitude": 48.8584,
    "DecimalLongitude": 2.2945,
    "MapsURL": "https://www.google.com/maps?q=48.8584,2.2945"
  },
  "has_exif": true,
  "has_gps": true,
  "total_tags": 42,
  "export_data": "..." # If export_format specified
}
```

### Web Interface
Navigate to `/tools/exif-extractor/` for the web interface.

**Steps**:
1. Upload an image (JPG, PNG, TIFF, WebP, or HEIC)
2. Click "Extract EXIF Data"
3. View formatted metadata in tables
4. Click GPS coordinates link to view location on Google Maps
5. Export as JSON or CSV using export buttons

### Extracted Information

**Image Info**:
- Filename, format, dimensions
- File size
- Color mode

**EXIF Data** (if available):
- Camera make and model
- Date/time taken
- ISO, aperture, shutter speed
- Focal length
- Flash settings
- White balance
- Orientation
- Software used

**GPS Data** (if available):
- Latitude/Longitude (raw and decimal)
- Altitude
- Timestamp
- Direction
- Google Maps link for easy viewing

### File Constraints
- **Max Size**: 20MB
- **Allowed Types**: .jpg, .jpeg, .png, .tiff, .tif, .webp, .heic

### Export Formats

#### JSON Export
Structured JSON with three sections:
- `image_info`: Basic image properties
- `exif_data`: All EXIF tags
- `gps_data`: GPS coordinates and metadata

#### CSV Export
Three-column format:
- `Category`: Image Info, EXIF, or GPS
- `Tag`: Metadata tag name
- `Value`: Tag value

### Privacy Considerations
⚠️ **Important**: EXIF data may contain sensitive information:
- **GPS Coordinates**: Exact location where photo was taken
- **Timestamps**: When photo was captured
- **Camera Serial Numbers**: Device identification
- **Software**: Editing applications used

Always strip EXIF data before sharing images publicly if privacy is a concern.

### Common Use Cases
- **Photography**: Analyze camera settings for learning
- **Forensics**: Verify image authenticity
- **Geotagging**: Extract location data
- **Organization**: Sort photos by date/camera
- **Privacy Audits**: Check what metadata is embedded

### No EXIF Data?
Some images may not contain EXIF data because:
- EXIF was stripped (social media, privacy tools)
- Image format doesn't support EXIF (some PNGs)
- Screenshot or computer-generated image
- Image was edited and EXIF was removed

---

## Installation Notes

### System Requirements
Both tools are included in the base Django application and don't require additional system dependencies beyond Python packages.

### Python Dependencies
```bash
# Pillow (already included in base requirements)
pip install Pillow>=10.2

# Optional: Enhanced EXIF reading
pip install exifread>=3.0.0
```

### API Access
Both tools support:
- Web interface
- REST API
- JSON responses
- CORS-enabled endpoints

### Authentication
- Public tools (no authentication required by default)
- Can be restricted via Django permissions if needed
