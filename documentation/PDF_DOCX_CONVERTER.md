# PDF to DOCX Converter

## Overview

The PDF to DOCX converter is a tool that converts PDF documents to Microsoft Word DOCX format. It preserves text content, images, tables, and basic formatting where possible.

## Features

- Convert PDF documents to editable DOCX format
- Preserve text, images, and tables
- Optional page range selection
- Support for large files (up to 100MB)
- Maintains basic formatting and structure

## Usage

### Web Interface

1. Navigate to the PDF to DOCX Converter tool
2. Upload a PDF file (maximum 100MB)
3. Optionally specify page range:
   - Start Page: First page to convert (0-indexed)
   - End Page: Last page to convert
   - Leave both empty to convert the entire document
4. Click "Convert to DOCX"
5. Download the converted DOCX file

### API Endpoint

**Endpoint:** `/api/v1/tools/pdf-docx-converter/convert/`

**Method:** `POST`

**Parameters:**
- `file` (required): PDF file to convert
- `start_page` (optional): First page to convert (default: 0)
- `end_page` (optional): Last page to convert (default: all pages)

**Example using curl:**
```bash
curl -X POST \
  http://localhost:8000/api/v1/tools/pdf-docx-converter/convert/ \
  -F "file=@document.pdf" \
  -F "start_page=0" \
  -F "end_page=10" \
  -o converted.docx
```

**Example using Python:**
```python
import requests

url = "http://localhost:8000/api/v1/tools/pdf-docx-converter/convert/"
files = {"file": open("document.pdf", "rb")}
data = {"start_page": 0, "end_page": 10}

response = requests.post(url, files=files, data=data)

if response.status_code == 200:
    with open("converted.docx", "wb") as f:
        f.write(response.content)
```

## What's Preserved

✓ Text content and formatting  
✓ Images and graphics  
✓ Tables and layouts  
✓ Basic font styles  
✓ Paragraphs and spacing

## Limitations

- Complex layouts may not convert perfectly
- Some fonts may be substituted with similar ones
- Scanned PDFs require OCR (not currently supported)
- Password-protected PDFs are not supported
- Form fields may not be preserved
- Some advanced PDF features may be lost

## Technical Details

### Library Used

The converter uses the `pdf2docx` library, which is built on top of:
- `PyMuPDF` (fitz): For PDF parsing
- `python-docx`: For DOCX creation

### File Size Limits

- Maximum input file size: 100MB
- Output file size may vary (sometimes larger than input)

### Performance

- Conversion speed depends on:
  - PDF complexity (text, images, formatting)
  - Number of pages
  - Server resources
- Average conversion time: 1-2 seconds per page

## Best Practices

1. **Use text-based PDFs**: Best results with PDFs containing selectable text
2. **Page selection**: Convert specific pages for faster processing
3. **Review output**: Always review formatting after conversion
4. **Edit in Word**: The DOCX output can be edited in Microsoft Word, LibreOffice, or Google Docs
5. **Backup originals**: Keep original PDF files as reference

## Troubleshooting

### Conversion Failed

**Problem:** Conversion fails with an error message

**Solutions:**
- Ensure the PDF is not corrupted
- Check that the PDF is not password-protected
- Verify the file size is under 100MB
- Try converting a smaller page range

### Poor Formatting

**Problem:** Output DOCX has formatting issues

**Solutions:**
- Try converting individual pages to identify problematic sections
- Use simpler PDF sources when possible
- Manually adjust formatting in Word after conversion

### Large File Size

**Problem:** Output DOCX is very large

**Solutions:**
- Convert only necessary pages
- Compress images in the output DOCX using Word's compression tools
- Consider using a lower resolution source PDF

## Development

### Adding the Tool

The tool is automatically registered when the Django application starts. The tool class is located at:

```
apps/tools/plugins/pdf_docx_converter.py
```

### Dependencies

Add to `requirements/base.txt`:
```
pdf2docx>=0.5.8
```

Dependencies installed with pdf2docx:
- PyMuPDF>=1.19.0
- python-docx>=0.8.10
- fonttools>=4.24.0
- numpy>=1.17.2
- opencv-python-headless>=4.5
- fire>=0.3.0

### Running Tests

```bash
pytest tests/test_pdf_docx_converter.py -v
```

## Version History

### v1.0.0 (2025-12-01)
- Initial release
- Support for PDF to DOCX conversion
- Optional page range selection
- Basic formatting preservation
- File size limit: 100MB

## Related Tools

- Image Format Converter: For converting images between different formats
- GPX/KML Converter: For GPS file format conversion

## Support

For issues or feature requests, please contact the development team or file an issue in the project repository.
