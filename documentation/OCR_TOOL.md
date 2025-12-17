# OCR Text Extraction Tool

## Overview
Extract text from images using Tesseract OCR with support for 14+ languages and image preprocessing for improved accuracy. This is an **asynchronous tool** following the Gold Standard pattern.

## Features
- **Multi-Language Support**: 14 languages including English, French, German, Spanish, Italian, Portuguese, Dutch, Russian, Japanese, Chinese, Korean, Arabic, Hindi
- **Image Preprocessing**: Automatic deskewing, denoising, contrast enhancement, and binarization
- **Async Processing**: Background processing via Azure Functions
- **Multiple Formats**: JPG, PNG, BMP, TIFF, WebP
- **Status Tracking**: Real-time polling with progress updates
- **History Sidebar**: Last 10 extractions with download/delete actions

## Architecture

### Flow Diagram
```
User Upload → Django validates & uploads to blob → Azure Function processes → Client polls status
```

### Components
1. **Django Plugin**: `apps/tools/plugins/ocr_tool.py`
2. **Azure Function**: `function_app.py` → `/image/ocr` endpoint
3. **Frontend**: Two-column layout with history sidebar
4. **Database**: ToolExecution status tracking
5. **Blob Storage**: 
   - Input: `uploads/image/{execution_id}.{ext}`
   - Output: `processed/image/{execution_id}.txt`

## Supported Languages

| Code | Language |
|------|----------|
| `eng` | English (default) |
| `fra` | French |
| `deu` | German |
| `spa` | Spanish |
| `ita` | Italian |
| `por` | Portuguese |
| `nld` | Dutch |
| `rus` | Russian |
| `jpn` | Japanese |
| `chi_sim` | Chinese (Simplified) |
| `chi_tra` | Chinese (Traditional) |
| `kor` | Korean |
| `ara` | Arabic |
| `hin` | Hindi |

## Usage

### Web Interface
Navigate to `/tools/ocr-tool/`

**Steps**:
1. Select an image file (JPG, PNG, BMP, TIFF, WebP)
2. Choose language (default: English)
3. Enable/disable preprocessing (recommended: enabled)
4. Click "Extract Text from Image"
5. Monitor real-time status updates
6. Download extracted text file when complete
7. View extraction history in right sidebar

### API Endpoint

#### Upload for Processing
```http
POST /api/v1/tools/ocr-tool/extract/
Content-Type: multipart/form-data

file: <image_file>
language: eng
preprocess: true
```

#### Response
```json
{
  "executionId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "filename": "document.jpg",
  "statusUrl": "/api/v1/executions/550e8400-e29b-41d4-a716-446655440000/status/"
}
```

#### Check Status
```http
GET /api/v1/executions/{execution_id}/status/
```

#### Response (Processing)
```json
{
  "executionId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "toolName": "ocr-tool",
  "inputFilename": "document.jpg"
}
```

#### Response (Completed)
```json
{
  "executionId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "toolName": "ocr-tool",
  "inputFilename": "document.jpg",
  "outputFilename": "550e8400-e29b-41d4-a716-446655440000.txt",
  "downloadUrl": "/api/v1/executions/550e8400-e29b-41d4-a716-446655440000/download/",
  "outputSize": 1234,
  "durationSeconds": 5.2
}
```

#### Download Result
```http
GET /api/v1/executions/{execution_id}/download/
```
Returns the extracted text file.

## Image Preprocessing

### What It Does
When preprocessing is enabled (recommended), the Azure Function applies the following transformations:

1. **Grayscale Conversion**: Reduces noise and improves text detection
2. **Denoising**: Removes image artifacts using Non-Local Means Denoising
3. **Adaptive Thresholding**: Converts to binary (black & white) for better OCR
4. **Deskewing**: Automatically corrects tilted/rotated text
5. **Contrast Enhancement**: Improves visibility of faint text

### When to Enable
✅ **Enable preprocessing for**:
- Low-quality images
- Photos of documents (phone camera)
- Scanned documents with noise
- Tilted or rotated text
- Low contrast images
- Handwritten text (limited support)

❌ **Disable preprocessing for**:
- High-quality scans
- Already optimized images
- PDF-to-image conversions (clean text)
- Screenshots with clear text

## OCR Modes (PSM)

Tesseract Page Segmentation Modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| `0` | Orientation and script detection only | Analyze document layout |
| `1` | Automatic with OSD | General documents |
| `3` | Fully automatic (default) | Most documents |
| `4` | Single column variable sizes | Newspaper columns |
| `6` | Single uniform block of text | Paragraphs |
| `11` | Sparse text | Receipts, invoices |
| `12` | Sparse text with OSD | Mixed sparse content |

**Default**: Mode `3` (fully automatic) - works for most use cases.

## File Constraints
- **Max Size**: 50MB
- **Allowed Types**: .jpg, .jpeg, .png, .bmp, .tiff, .tif, .webp
- **Resolution**: Higher resolution = better accuracy (300+ DPI recommended)

## Performance

### Processing Time
- **Simple image** (1-2 MP, English): 3-8 seconds
- **Complex image** (8+ MP, multi-column): 10-20 seconds
- **Preprocessed image**: +2-5 seconds for enhancement
- **Non-Latin languages** (Chinese, Arabic): +30-50% time

### Accuracy Factors
- **Resolution**: Higher is better (300 DPI ideal)
- **Text Clarity**: Clear fonts work best
- **Background**: Uniform background improves results
- **Language Selection**: Must match document language
- **Preprocessing**: Significantly improves low-quality images

## Azure Function Handler

### Endpoint
```
POST /api/image/ocr
```

### Implementation Highlights
Located in `function_app/function_app.py`:
- Blob download from `uploads/image/{execution_id}.{ext}`
- OpenCV preprocessing pipeline
- Tesseract OCR with language support
- Text output to `processed/image/{execution_id}.txt`
- Database status updates
- Comprehensive logging with emojis

### Dependencies (Azure Function)
```python
# function_app/requirements.txt
pytesseract>=0.3.10
opencv-python-headless>=4.8.0  # Headless for serverless
Pillow>=10.0.0
```

### System Requirements (Azure Function)
**Tesseract OCR Engine** must be installed:
```bash
# Ubuntu/Debian
apt-get update
apt-get install -y tesseract-ocr

# Language packs
apt-get install -y tesseract-ocr-eng tesseract-ocr-fra tesseract-ocr-deu \
  tesseract-ocr-spa tesseract-ocr-ita tesseract-ocr-por tesseract-ocr-nld \
  tesseract-ocr-rus tesseract-ocr-jpn tesseract-ocr-chi-sim tesseract-ocr-chi-tra \
  tesseract-ocr-kor tesseract-ocr-ara tesseract-ocr-hin
```

## Frontend Template

### Location
`templates/tools/ocr_tool.html`

### Structure
**Two-Column Layout** (MANDATORY):
- **Left (8 cols)**: Upload form, status section, instructions
- **Right (4 cols)**: History sidebar (sticky)

### Key Features
- Language dropdown (14 languages)
- Preprocessing toggle
- Real-time status polling (every 2.5s)
- Download button on completion
- History with last 10 items
- Delete with confirmation modal

### JavaScript
- Form submission with FormData
- AJAX upload to `/api/v1/tools/ocr-tool/extract/`
- Status polling loop
- History loading via ToolHistory.js
- Error handling and user notifications

## Database Schema

### ToolExecution Fields
```python
execution_id: UUID (primary key)
tool_name: "ocr-tool"
status: "pending" | "processing" | "completed" | "failed"
input_blob_path: "uploads/image/{uuid}.jpg"
input_filename: "document.jpg"
input_size: bytes
output_blob_path: "processed/image/{uuid}.txt"
output_filename: "{uuid}.txt"
output_size: bytes
created_at: timestamp
completed_at: timestamp
duration_seconds: float
parameters: JSON {"language": "eng", "preprocess": true}
error_message: string (if failed)
```

## Testing

### Local Development (Azurite)
```bash
# Start Azurite
azurite --silent --location /tmp/azurite --debug /tmp/azurite/debug.log

# Run Django
python manage.py runserver

# Run Azure Functions locally
cd function_app
func start
```

### Test Files
- `tests/test_ocr_tool.py` - Plugin tests with mocked Azure SDK
- Mock blob storage operations
- Validate language/preprocess parameters
- Test status polling endpoints

### Coverage Target
≥80% code coverage for new tool

## Troubleshooting

### Common Issues

**1. "Tesseract not found"**
```
Solution: Install Tesseract OCR on Azure Function host
apt-get install tesseract-ocr
```

**2. "Language not supported"**
```
Solution: Install language pack
apt-get install tesseract-ocr-{lang_code}
```

**3. "Poor OCR accuracy"**
```
Solutions:
- Enable preprocessing
- Increase image resolution
- Select correct language
- Use OCR mode 11 for sparse text
```

**4. "Processing timeout"**
```
Solution: Increase Azure Function timeout (default: 300s)
- Check image size (reduce if >20MB)
- Simplify preprocessing
```

**5. "Upload fails"**
```
Solutions:
- Check blob storage connection string
- Verify Managed Identity permissions
- Check firewall/network rules
```

## Best Practices

### For Users
1. **Use high-resolution images** (300+ DPI)
2. **Select correct language** before extraction
3. **Enable preprocessing** for photos/low-quality scans
4. **Crop to text area** for faster processing
5. **Use mode 11** for receipts/invoices

### For Developers
1. **Follow Gold Standard** async pattern
2. **Log comprehensively** with emojis for easy debugging
3. **Test with Azurite** before deploying
4. **Handle timeouts** gracefully
5. **Cleanup temp files** in try/finally blocks
6. **Update database status** at each stage

## Deployment Checklist

- [ ] Install Tesseract OCR on Azure Function host
- [ ] Install all language packs needed
- [ ] Set `AZURE_FUNCTION_BASE_URL` environment variable
- [ ] Configure blob storage containers (`uploads`, `processed`)
- [ ] Enable Managed Identity for blob access
- [ ] Test with sample images in all supported languages
- [ ] Verify preprocessing works correctly
- [ ] Check history sidebar loads properly
- [ ] Test status polling and download
- [ ] Monitor Azure Function logs for errors

## Future Enhancements
- [ ] PDF page OCR (extract text from PDFs)
- [ ] Batch processing (multiple images)
- [ ] OCR confidence scores
- [ ] Structured output (JSON with coordinates)
- [ ] Table detection and extraction
- [ ] Handwriting recognition (specialized models)
- [ ] Custom training data support

## References
- [Tesseract OCR Documentation](https://github.com/tesseract-ocr/tesseract)
- [OpenCV Python Tutorial](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [Async File Processing Gold Standard](./ASYNC_FILE_PROCESSING_GOLD_STANDARD.md)
