"""
Full Azure Function for PDF to DOCX conversion with database tracking.
"""

import logging
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import psycopg2
from pdf2docx import Converter

# Initialize Function App
app = func.FunctionApp()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)


def get_blob_service_client() -> BlobServiceClient:
    """
    Get BlobServiceClient using connection string or Managed Identity.
    
    Uses connection string for local development (Azurite), DefaultAzureCredential for Azure.
    This matches the pattern used in Django and PDF converter.
    """
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    
    # Check for local development (Azurite)
    if connection_string and "127.0.0.1" in connection_string:
        logger.info("🔧 Using local Azurite for blob storage")
        return BlobServiceClient.from_connection_string(connection_string)
    
    # Production: Use Managed Identity / DefaultAzureCredential
    storage_account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
    if not storage_account_name:
        logger.error("❌ Storage account name not configured")
        raise ValueError("AZURE_STORAGE_ACCOUNT_NAME not configured")
    
    logger.info(f"🔐 Using Azure Managed Identity for storage account: {storage_account_name}")
    account_url = f"https://{storage_account_name}.blob.core.windows.net"
    credential = DefaultAzureCredential()
    return BlobServiceClient(account_url=account_url, credential=credential)


def get_db_connection():
    """Get PostgreSQL database connection."""
    db_config = {
        'host': os.environ.get('DB_HOST'),
        'database': os.environ.get('DB_NAME'),
        'user': os.environ.get('DB_USER'),
        'password': os.environ.get('DB_PASSWORD'),
        'port': os.environ.get('DB_PORT', '5432'),
        'sslmode': os.environ.get('DB_SSLMODE', 'require')
    }
    return psycopg2.connect(**db_config)


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        body=json.dumps({"status": "healthy", "message": "Azure Function is running successfully"}),
        mimetype="application/json",
        status_code=200
    )


@app.route(route="convert/pdf-to-docx", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def convert_pdf_to_docx(req: func.HttpRequest) -> func.HttpResponse:
    """
    Full PDF to DOCX conversion workflow with database tracking.
    
    Expected JSON payload:
    {
        "execution_id": "uuid",
        "blob_name": "uploads/pdf/{uuid}.pdf"
    }
    """
    execution_id = None
    temp_pdf_path = None
    temp_docx_path = None
    
    try:
        logger.info("=" * 100)
        logger.info("🚀 PDF TO DOCX CONVERSION STARTED")
        logger.info("=" * 100)
        
        # Parse request body
        try:
            req_body = req.get_json()
            execution_id = req_body.get('execution_id')
            blob_name = req_body.get('blob_name')
            
            logger.info(f"📋 Request Details:")
            logger.info(f"   Execution ID: {execution_id}")
            logger.info(f"   Blob Name: {blob_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to parse request body: {e}")
            return func.HttpResponse(
                body=json.dumps({"error": "Invalid JSON payload", "details": str(e)}),
                mimetype="application/json",
                status_code=400
            )
        
        if not execution_id or not blob_name:
            logger.error("❌ Missing required parameters")
            return func.HttpResponse(
                body=json.dumps({"error": "Missing execution_id or blob_name"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Update database: processing
        logger.info("-" * 100)
        logger.info("📝 UPDATING DATABASE STATUS: processing")
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tool_executions SET status = %s, updated_at = NOW() WHERE id = %s",
                ('processing', execution_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: status = processing")
        except Exception as db_error:
            logger.warning(f"⚠️ Failed to update database (continuing anyway): {db_error}")
        
        # Initialize blob service client
        logger.info("-" * 100)
        logger.info("🔐 INITIALIZING BLOB STORAGE CLIENT")
        blob_service_client = get_blob_service_client()
        logger.info("✅ Blob service client initialized")
        
        # Download PDF from blob storage
        logger.info("-" * 100)
        logger.info(f"📥 DOWNLOADING PDF FROM BLOB STORAGE")
        logger.info(f"   Blob: {blob_name}")
        
        try:
            # Remove 'uploads/' prefix if present
            if blob_name.startswith('uploads/'):
                actual_blob_name = blob_name.replace('uploads/', '', 1)
            else:
                actual_blob_name = blob_name
            
            logger.info(f"   Container: uploads")
            logger.info(f"   Blob path: {actual_blob_name}")
            
            blob_client = blob_service_client.get_blob_client(
                container="uploads",
                blob=actual_blob_name
            )
            
            # Check if blob exists
            if not blob_client.exists():
                logger.error(f"❌ Blob not found: uploads/{actual_blob_name}")
                raise Exception(f"Blob not found: {blob_name}")
            
            # Download to temp file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
                blob_data = blob_client.download_blob()
                temp_pdf.write(blob_data.readall())
            
            pdf_size = Path(temp_pdf_path).stat().st_size
            logger.info(f"✅ PDF downloaded to {temp_pdf_path}")
            logger.info(f"   Size: {pdf_size:,} bytes ({pdf_size / 1024 / 1024:.2f} MB)")
            
        except Exception as blob_error:
            logger.error(f"❌ Failed to download blob: {blob_error}")
            raise
        
        # Convert PDF to DOCX
        logger.info("-" * 100)
        logger.info(f"🔄 CONVERTING PDF TO DOCX")
        logger.info(f"   Input: {temp_pdf_path}")
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_docx:
                temp_docx_path = temp_docx.name
            
            logger.info(f"   Output: {temp_docx_path}")
            logger.info(f"   Starting conversion...")
            
            # Perform conversion
            cv = Converter(temp_pdf_path)
            cv.convert(temp_docx_path, start=0, end=None)
            cv.close()
            
            docx_size = Path(temp_docx_path).stat().st_size
            logger.info(f"✅ Conversion completed")
            logger.info(f"   Output size: {docx_size:,} bytes ({docx_size / 1024 / 1024:.2f} MB)")
            
        except Exception as convert_error:
            logger.error(f"❌ Conversion failed: {convert_error}")
            raise
        
        # Upload DOCX to blob storage
        logger.info("-" * 100)
        logger.info(f"📤 UPLOADING DOCX TO BLOB STORAGE")
        
        try:
            output_blob_name = f"docx/{execution_id}.docx"
            logger.info(f"   Container: processed")
            logger.info(f"   Blob: {output_blob_name}")
            
            output_blob_client = blob_service_client.get_blob_client(
                container="processed",
                blob=output_blob_name
            )
            
            with open(temp_docx_path, 'rb') as docx_file:
                output_blob_client.upload_blob(
                    docx_file,
                    overwrite=True,
                    metadata={
                        'execution_id': execution_id,
                        'converted_at': datetime.now(timezone.utc).isoformat(),
                        'original_format': 'pdf',
                        'output_format': 'docx'
                    }
                )
            
            output_blob_path = f"processed/{output_blob_name}"
            logger.info(f"✅ DOCX uploaded successfully")
            logger.info(f"   Full path: {output_blob_path}")
            
        except Exception as upload_error:
            logger.error(f"❌ Upload failed: {upload_error}")
            raise
        
        # Update database: completed
        logger.info("-" * 100)
        logger.info("📝 UPDATING DATABASE STATUS: completed")
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE tool_executions 
                   SET status = %s, 
                       output_blob_path = %s,
                       output_size = %s,
                       updated_at = NOW(),
                       completed_at = NOW()
                   WHERE id = %s""",
                ('completed', output_blob_path, docx_size, execution_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: status = completed")
            logger.info(f"   Output blob path: {output_blob_path}")
            logger.info(f"   Output size: {docx_size:,} bytes")
        except Exception as db_error:
            logger.error(f"❌ Failed to update database: {db_error}")
            # Don't raise - conversion succeeded even if DB update failed
        
        # Cleanup temp files
        logger.info("-" * 100)
        logger.info("🧹 CLEANING UP TEMPORARY FILES")
        try:
            if temp_pdf_path and Path(temp_pdf_path).exists():
                Path(temp_pdf_path).unlink()
                logger.info(f"   Deleted: {temp_pdf_path}")
            if temp_docx_path and Path(temp_docx_path).exists():
                Path(temp_docx_path).unlink()
                logger.info(f"   Deleted: {temp_docx_path}")
            logger.info("✅ Cleanup completed")
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Cleanup warning: {cleanup_error}")
        
        # Success response
        logger.info("=" * 100)
        logger.info("✅ PDF TO DOCX CONVERSION COMPLETED SUCCESSFULLY")
        logger.info(f"   Execution ID: {execution_id}")
        logger.info(f"   Input: {blob_name}")
        logger.info(f"   Output: {output_blob_path}")
        logger.info("=" * 100)
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "success",
                "execution_id": execution_id,
                "input_blob": blob_name,
                "output_blob": output_blob_path,
                "output_size_bytes": docx_size,
                "output_size_mb": round(docx_size / 1024 / 1024, 2)
            }, indent=2),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        # Handle any errors
        logger.error("=" * 100)
        logger.error("❌ PDF TO DOCX CONVERSION FAILED")
        logger.error(f"   Execution ID: {execution_id}")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error("=" * 100)
        logger.error("Full traceback:", exc_info=True)
        
        # Update database: failed
        if execution_id:
            try:
                logger.info("📝 Updating database status: failed")
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE tool_executions 
                       SET status = %s, 
                           error_message = %s,
                           updated_at = NOW()
                       WHERE id = %s""",
                    ('failed', str(e), execution_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                logger.info("✅ Database updated: status = failed")
            except Exception as db_error:
                logger.error(f"❌ Failed to update database: {db_error}")
        
        # Cleanup temp files
        try:
            if temp_pdf_path and Path(temp_pdf_path).exists():
                Path(temp_pdf_path).unlink()
            if temp_docx_path and Path(temp_docx_path).exists():
                Path(temp_docx_path).unlink()
        except:
            pass
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "error",
                "error": str(e),
                "execution_id": execution_id,
                "error_type": type(e).__name__
            }),
            mimetype="application/json",
            status_code=500
        )


@app.route(route="storage/list-blobs", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def list_blobs(req: func.HttpRequest) -> func.HttpResponse:
    """List all blobs in uploads and processed containers."""
    try:
        logger.info("📂 Listing blobs in storage containers")
        
        blob_service = get_blob_service_client()
        containers = ["uploads", "processed"]
        
        result = {}
        
        for container_name in containers:
            logger.info(f"📁 Container: {container_name}")
            try:
                container_client = blob_service.get_container_client(container_name)
                blobs = list(container_client.list_blobs())
                
                result[container_name] = []
                for blob in blobs:
                    result[container_name].append({
                        "name": blob.name,
                        "size": blob.size,
                        "last_modified": blob.last_modified.isoformat() if blob.last_modified else None,
                        "content_type": blob.content_settings.content_type if blob.content_settings else None
                    })
                
                logger.info(f"   Found {len(blobs)} blobs")
                
            except Exception as e:
                logger.error(f"   Error accessing container {container_name}: {e}")
                result[container_name] = {"error": str(e)}
        
        return func.HttpResponse(
            body=json.dumps(result, indent=2),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"❌ Error listing blobs: {e}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )


@app.route(route="video/rotate", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def rotate_video(req: func.HttpRequest) -> func.HttpResponse:
    """
    Rotate video from blob storage.
    
    Expected JSON payload:
    {
        "execution_id": "uuid",
        "blob_name": "video-uploads/video/{uuid}.mp4",
        "rotation": "90_cw|90_ccw|180"
    }
    """
    import subprocess
    
    execution_id = None
    temp_input_path = None
    temp_output_path = None
    
    # Rotation configurations
    ROTATION_ANGLES = {
        "90_cw": {"transpose": "1", "name": "90° Clockwise"},
        "90_ccw": {"transpose": "2", "name": "90° Counter-Clockwise"},
        "180": {"transpose": "2,transpose=2", "name": "180°"},
    }
    
    try:
        logger.info("=" * 100)
        logger.info("🎬 VIDEO ROTATION STARTED")
        logger.info("=" * 100)
        
        # Parse request
        try:
            req_body = req.get_json()
            execution_id = req_body.get('execution_id')
            blob_name = req_body.get('blob_name')
            rotation = req_body.get('rotation')
            
            logger.info(f"📋 Request Details:")
            logger.info(f"   Execution ID: {execution_id}")
            logger.info(f"   Blob Name: {blob_name}")
            logger.info(f"   Rotation: {rotation}")
            
        except Exception as e:
            logger.error(f"❌ Failed to parse request: {e}")
            return func.HttpResponse(
                body=json.dumps({"error": "Invalid JSON payload"}),
                mimetype="application/json",
                status_code=400
            )
        
        if not all([execution_id, blob_name, rotation]):
            return func.HttpResponse(
                body=json.dumps({"error": "Missing required parameters"}),
                mimetype="application/json",
                status_code=400
            )
        
        if rotation not in ROTATION_ANGLES:
            return func.HttpResponse(
                body=json.dumps({"error": f"Invalid rotation: {rotation}"}),
                mimetype="application/json",
                status_code=400
            )
        
        rotation_config = ROTATION_ANGLES[rotation]
        
        # Update database: processing
        try:
            logger.info("📝 Updating database status: processing")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE tool_executions 
                   SET status = %s, 
                       started_at = NOW()
                   WHERE id = %s""",
                ('processing', execution_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: status = processing")
        except Exception as db_error:
            logger.warning(f"⚠️ Failed to update database: {db_error}")
        
        # Initialize blob service
        logger.info("-" * 100)
        logger.info("🔐 INITIALIZING BLOB STORAGE CLIENT")
        blob_service = get_blob_service_client()
        logger.info("✅ Blob service client initialized")
        
        # Download video from blob storage
        logger.info("-" * 100)
        logger.info(f"📥 DOWNLOADING VIDEO FROM BLOB STORAGE")
        logger.info(f"   Blob: {blob_name}")
        
        try:
            # Remove container prefix if present
            if blob_name.startswith('video-uploads/'):
                actual_blob_name = blob_name.replace('video-uploads/', '', 1)
            else:
                actual_blob_name = blob_name
            
            blob_client = blob_service.get_blob_client(
                container="video-uploads",
                blob=actual_blob_name
            )
            
            if not blob_client.exists():
                raise Exception(f"Blob not found: {blob_name}")
            
            # Get blob metadata
            blob_properties = blob_client.get_blob_properties()
            original_filename = blob_properties.metadata.get('original_filename', 'video.mp4')
            video_size = blob_properties.size
            
            logger.info(f"   Original filename: {original_filename}")
            logger.info(f"   Video size: {video_size:,} bytes ({video_size / 1024 / 1024:.2f} MB)")
            
            # Download to temp file
            file_ext = Path(original_filename).suffix
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_input:
                temp_input_path = temp_input.name
                blob_data = blob_client.download_blob()
                temp_input.write(blob_data.readall())
            
            logger.info(f"✅ Video downloaded: {temp_input_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to download video: {e}")
            raise
        
        # Rotate video using FFmpeg
        logger.info("-" * 100)
        logger.info(f"🔄 ROTATING VIDEO: {rotation_config['name']}")
        start_time = datetime.now(timezone.utc)
        
        try:
            # Get FFmpeg executable path from imageio-ffmpeg
            try:
                from imageio_ffmpeg import get_ffmpeg_exe
                ffmpeg_path = get_ffmpeg_exe()
                logger.info(f"   Using FFmpeg from: {ffmpeg_path}")
            except ImportError:
                # Fallback to system ffmpeg
                ffmpeg_path = "ffmpeg"
                logger.warning("   imageio-ffmpeg not available, using system ffmpeg")
            
            # Create temp output file
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_output:
                temp_output_path = temp_output.name
            
            # Build FFmpeg command
            cmd = [
                ffmpeg_path,
                "-i", temp_input_path,
                "-vf", f"transpose={rotation_config['transpose']}",
                "-c:a", "copy",  # Copy audio without re-encoding
                "-c:v", "libx264",  # Re-encode video with H.264
                "-preset", "fast",  # Fast encoding
                "-crf", "23",  # Quality
                "-y",  # Overwrite output
                temp_output_path,
            ]
            
            logger.info(f"   FFmpeg command: {' '.join(cmd)}")
            
            # Execute FFmpeg
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600,  # 10 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode("utf-8", errors="ignore")
                logger.error(f"❌ FFmpeg error: {error_msg[:500]}")
                raise Exception(f"FFmpeg failed: {error_msg[:200]}")
            
            # Verify output
            if not os.path.exists(temp_output_path) or os.path.getsize(temp_output_path) == 0:
                raise Exception("Output file was not created")
            
            output_size = os.path.getsize(temp_output_path)
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(f"✅ Rotation completed in {duration:.2f}s")
            logger.info(f"   Output size: {output_size:,} bytes ({output_size / 1024 / 1024:.2f} MB)")
            
        except subprocess.TimeoutExpired:
            logger.error("❌ FFmpeg timeout (10 minutes)")
            raise Exception("Video rotation timed out")
        except Exception as e:
            logger.error(f"❌ Rotation failed: {e}")
            raise
        
        # Upload rotated video to blob storage
        logger.info("-" * 100)
        logger.info(f"📤 UPLOADING ROTATED VIDEO TO BLOB STORAGE")
        
        try:
            # Generate output filename
            input_stem = Path(original_filename).stem
            output_filename = f"{input_stem}_rotated_{rotation}{file_ext}"
            output_blob_name = f"video/{execution_id}{file_ext}"
            
            logger.info(f"   Container: video-processed")
            logger.info(f"   Blob: {output_blob_name}")
            logger.info(f"   Filename: {output_filename}")
            
            output_blob_client = blob_service.get_blob_client(
                container="video-processed",
                blob=output_blob_name
            )
            
            # Upload with metadata
            with open(temp_output_path, "rb") as video_file:
                output_blob_client.upload_blob(
                    video_file,
                    overwrite=True,
                    metadata={
                        "execution_id": execution_id,
                        "original_filename": original_filename,
                        "output_filename": output_filename,
                        "rotation": rotation,
                        "source_blob": blob_name,
                    }
                )
            
            logger.info(f"✅ Rotated video uploaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to upload rotated video: {e}")
            raise
        
        # Update database: completed
        try:
            logger.info("📝 Updating database status: completed")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE tool_executions 
                   SET status = %s,
                       completed_at = NOW(),
                       output_filename = %s,
                       output_size = %s,
                       output_blob_path = %s
                   WHERE id = %s""",
                ('completed', output_filename, output_size, f"video-processed/{output_blob_name}", execution_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: status = completed")
        except Exception as db_error:
            logger.warning(f"⚠️ Failed to update database: {db_error}")
        
        # Cleanup temp files
        try:
            if temp_input_path and os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if temp_output_path and os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
        except:
            pass
        
        logger.info("=" * 100)
        logger.info("✅ VIDEO ROTATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 100)
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "success",
                "execution_id": execution_id,
                "output_filename": output_filename,
                "output_size": output_size,
                "duration_seconds": duration
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error("=" * 100)
        logger.error("❌ VIDEO ROTATION FAILED")
        logger.error(f"   Execution ID: {execution_id}")
        logger.error(f"   Error: {str(e)}")
        logger.error("=" * 100)
        
        # Update database: failed
        if execution_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE tool_executions 
                       SET status = %s, 
                           error_message = %s,
                           updated_at = NOW()
                       WHERE id = %s""",
                    ('failed', str(e), execution_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as db_error:
                logger.error(f"❌ Failed to update database: {db_error}")
        
        # Cleanup temp files
        try:
            if temp_input_path and os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if temp_output_path and os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
        except:
            pass
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "error",
                "error": str(e),
                "execution_id": execution_id
            }),
            mimetype="application/json",
            status_code=500
        )


@app.route(route="image/convert", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def convert_image(req: func.HttpRequest) -> func.HttpResponse:
    """
    Convert image format using Pillow.
    
    Expected JSON payload:
    {
        "execution_id": "uuid",
        "blob_name": "image/{uuid}.jpg",
        "output_format": "png|jpg|webp|gif|bmp|tiff|ico",
        "quality": 85,
        "width": null,
        "height": null
    }
    """
    from PIL import Image
    
    execution_id = None
    temp_input_path = None
    temp_output_path = None
    
    # Format configurations
    FORMAT_CONFIG = {
        'jpg': {'pil_format': 'JPEG', 'extension': '.jpg', 'supports_quality': True},
        'jpeg': {'pil_format': 'JPEG', 'extension': '.jpg', 'supports_quality': True},
        'png': {'pil_format': 'PNG', 'extension': '.png', 'supports_quality': False},
        'webp': {'pil_format': 'WEBP', 'extension': '.webp', 'supports_quality': True},
        'gif': {'pil_format': 'GIF', 'extension': '.gif', 'supports_quality': False},
        'bmp': {'pil_format': 'BMP', 'extension': '.bmp', 'supports_quality': False},
        'tiff': {'pil_format': 'TIFF', 'extension': '.tiff', 'supports_quality': False},
        'ico': {'pil_format': 'ICO', 'extension': '.ico', 'supports_quality': False},
    }
    
    try:
        logger.info("=" * 100)
        logger.info("🖼️ IMAGE CONVERSION STARTED")
        logger.info("=" * 100)
        
        # Parse request
        try:
            req_body = req.get_json()
            execution_id = req_body.get('execution_id')
            blob_name = req_body.get('blob_name')
            output_format = req_body.get('output_format', 'jpg').lower()
            quality = int(req_body.get('quality', 85))
            width = req_body.get('width')
            height = req_body.get('height')
            
            logger.info(f"📋 Request Details:")
            logger.info(f"   Execution ID: {execution_id}")
            logger.info(f"   Blob Name: {blob_name}")
            logger.info(f"   Output Format: {output_format}")
            logger.info(f"   Quality: {quality}")
            logger.info(f"   Resize: {width}x{height}" if width or height else "   Resize: None")
            
        except Exception as e:
            logger.error(f"❌ Failed to parse request: {e}")
            return func.HttpResponse(
                body=json.dumps({"error": "Invalid JSON payload"}),
                mimetype="application/json",
                status_code=400
            )
        
        if not all([execution_id, blob_name]):
            return func.HttpResponse(
                body=json.dumps({"error": "Missing required parameters"}),
                mimetype="application/json",
                status_code=400
            )
        
        if output_format not in FORMAT_CONFIG:
            return func.HttpResponse(
                body=json.dumps({"error": f"Unsupported format: {output_format}"}),
                mimetype="application/json",
                status_code=400
            )
        
        format_config = FORMAT_CONFIG[output_format]
        
        # Update database: processing
        try:
            logger.info("📝 Updating database status: processing")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tool_executions SET status = %s, started_at = NOW() WHERE id = %s",
                ('processing', execution_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: status = processing")
        except Exception as db_error:
            logger.warning(f"⚠️ Failed to update database: {db_error}")
        
        # Initialize blob service
        logger.info("-" * 100)
        logger.info("🔐 INITIALIZING BLOB STORAGE CLIENT")
        blob_service = get_blob_service_client()
        logger.info("✅ Blob service client initialized")
        
        # Download image from blob storage
        logger.info("-" * 100)
        logger.info(f"📥 DOWNLOADING IMAGE FROM BLOB STORAGE")
        
        try:
            # Parse blob path
            if blob_name.startswith('uploads/'):
                actual_blob_name = blob_name.replace('uploads/', '', 1)
            else:
                actual_blob_name = blob_name
            
            logger.info(f"   Container: uploads")
            logger.info(f"   Blob path: {actual_blob_name}")
            
            blob_client = blob_service.get_blob_client(
                container="uploads",
                blob=actual_blob_name
            )
            
            if not blob_client.exists():
                raise Exception(f"Blob not found: {blob_name}")
            
            # Get metadata
            blob_properties = blob_client.get_blob_properties()
            original_filename = blob_properties.metadata.get('original_filename', 'image.jpg')
            
            # Download to temp file
            input_ext = Path(original_filename).suffix or '.jpg'
            with tempfile.NamedTemporaryFile(suffix=input_ext, delete=False) as temp_input:
                temp_input_path = temp_input.name
                blob_data = blob_client.download_blob()
                temp_input.write(blob_data.readall())
            
            input_size = Path(temp_input_path).stat().st_size
            logger.info(f"✅ Image downloaded: {temp_input_path}")
            logger.info(f"   Size: {input_size:,} bytes")
            
        except Exception as e:
            logger.error(f"❌ Failed to download image: {e}")
            raise
        
        # Convert image
        logger.info("-" * 100)
        logger.info(f"🔄 CONVERTING IMAGE TO {output_format.upper()}")
        
        try:
            # Open image
            img = Image.open(temp_input_path)
            original_size = img.size
            logger.info(f"   Original dimensions: {original_size[0]}x{original_size[1]}")
            
            # Resize if requested
            if width or height:
                if width and height:
                    new_size = (int(width), int(height))
                elif width:
                    ratio = int(width) / original_size[0]
                    new_size = (int(width), int(original_size[1] * ratio))
                else:
                    ratio = int(height) / original_size[1]
                    new_size = (int(original_size[0] * ratio), int(height))
                
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"   Resized to: {new_size[0]}x{new_size[1]}")
            
            # Convert color mode if needed
            if format_config['pil_format'] == 'JPEG' and img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            elif format_config['pil_format'] == 'ICO':
                # ICO has size limitations
                img = img.resize((256, 256), Image.Resampling.LANCZOS)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=format_config['extension'], delete=False) as temp_output:
                temp_output_path = temp_output.name
            
            save_kwargs = {'format': format_config['pil_format']}
            if format_config['supports_quality']:
                save_kwargs['quality'] = quality
            
            img.save(temp_output_path, **save_kwargs)
            img.close()
            
            output_size = Path(temp_output_path).stat().st_size
            logger.info(f"✅ Conversion completed")
            logger.info(f"   Output size: {output_size:,} bytes")
            
        except Exception as e:
            logger.error(f"❌ Conversion failed: {e}")
            raise
        
        # Upload converted image to blob storage
        logger.info("-" * 100)
        logger.info(f"📤 UPLOADING CONVERTED IMAGE TO BLOB STORAGE")
        
        try:
            input_stem = Path(original_filename).stem
            output_filename = f"{input_stem}{format_config['extension']}"
            output_blob_name = f"image/{execution_id}{format_config['extension']}"
            
            logger.info(f"   Container: processed")
            logger.info(f"   Blob: {output_blob_name}")
            
            output_blob_client = blob_service.get_blob_client(
                container="processed",
                blob=output_blob_name
            )
            
            with open(temp_output_path, "rb") as img_file:
                output_blob_client.upload_blob(
                    img_file,
                    overwrite=True,
                    metadata={
                        "execution_id": execution_id,
                        "original_filename": original_filename,
                        "output_filename": output_filename,
                        "output_format": output_format,
                    }
                )
            
            logger.info(f"✅ Image uploaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to upload image: {e}")
            raise
        
        # Update database: completed
        try:
            logger.info("📝 Updating database status: completed")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE tool_executions 
                   SET status = %s,
                       completed_at = NOW(),
                       output_filename = %s,
                       output_size = %s,
                       output_blob_path = %s
                   WHERE id = %s""",
                ('completed', output_filename, output_size, f"processed/{output_blob_name}", execution_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: status = completed")
        except Exception as db_error:
            logger.warning(f"⚠️ Failed to update database: {db_error}")
        
        # Cleanup temp files
        try:
            if temp_input_path and os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if temp_output_path and os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
        except:
            pass
        
        logger.info("=" * 100)
        logger.info("✅ IMAGE CONVERSION COMPLETED SUCCESSFULLY")
        logger.info("=" * 100)
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "success",
                "execution_id": execution_id,
                "output_filename": output_filename,
                "output_size": output_size
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error("=" * 100)
        logger.error("❌ IMAGE CONVERSION FAILED")
        logger.error(f"   Execution ID: {execution_id}")
        logger.error(f"   Error: {str(e)}")
        logger.error("=" * 100)
        
        # Update database: failed
        if execution_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE tool_executions 
                       SET status = %s, 
                           error_message = %s,
                           updated_at = NOW()
                       WHERE id = %s""",
                    ('failed', str(e), execution_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as db_error:
                logger.error(f"❌ Failed to update database: {db_error}")
        
        # Cleanup temp files
        try:
            if temp_input_path and os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if temp_output_path and os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
        except:
            pass
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "error",
                "error": str(e),
                "execution_id": execution_id
            }),
            mimetype="application/json",
            status_code=500
        )


@app.route(route="gpx/convert", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def convert_gpx_kml(req: func.HttpRequest) -> func.HttpResponse:
    """
    Convert GPX to KML or KML to GPX.
    
    Expected JSON payload:
    {
        "execution_id": "uuid",
        "blob_name": "gpx/{uuid}.gpx",
        "conversion_type": "gpx_to_kml|kml_to_gpx"
    }
    """
    import xml.etree.ElementTree as ET
    
    execution_id = None
    temp_input_path = None
    temp_output_path = None
    
    try:
        logger.info("=" * 100)
        logger.info("🗺️ GPX/KML CONVERSION STARTED")
        logger.info("=" * 100)
        
        # Parse request
        try:
            req_body = req.get_json()
            execution_id = req_body.get('execution_id')
            blob_name = req_body.get('blob_name')
            conversion_type = req_body.get('conversion_type')
            
            logger.info(f"📋 Request Details:")
            logger.info(f"   Execution ID: {execution_id}")
            logger.info(f"   Blob Name: {blob_name}")
            logger.info(f"   Conversion Type: {conversion_type}")
            
        except Exception as e:
            logger.error(f"❌ Failed to parse request: {e}")
            return func.HttpResponse(
                body=json.dumps({"error": "Invalid JSON payload"}),
                mimetype="application/json",
                status_code=400
            )
        
        if not all([execution_id, blob_name, conversion_type]):
            return func.HttpResponse(
                body=json.dumps({"error": "Missing required parameters"}),
                mimetype="application/json",
                status_code=400
            )
        
        if conversion_type not in ('gpx_to_kml', 'kml_to_gpx'):
            return func.HttpResponse(
                body=json.dumps({"error": f"Invalid conversion type: {conversion_type}"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Update database: processing
        try:
            logger.info("📝 Updating database status: processing")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tool_executions SET status = %s, started_at = NOW() WHERE id = %s",
                ('processing', execution_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: status = processing")
        except Exception as db_error:
            logger.warning(f"⚠️ Failed to update database: {db_error}")
        
        # Initialize blob service
        logger.info("-" * 100)
        logger.info("🔐 INITIALIZING BLOB STORAGE CLIENT")
        blob_service = get_blob_service_client()
        logger.info("✅ Blob service client initialized")
        
        # Download file from blob storage
        logger.info("-" * 100)
        logger.info(f"📥 DOWNLOADING FILE FROM BLOB STORAGE")
        
        try:
            # Parse blob path
            if blob_name.startswith('uploads/'):
                actual_blob_name = blob_name.replace('uploads/', '', 1)
            else:
                actual_blob_name = blob_name
            
            logger.info(f"   Container: uploads")
            logger.info(f"   Blob path: {actual_blob_name}")
            
            blob_client = blob_service.get_blob_client(
                container="uploads",
                blob=actual_blob_name
            )
            
            if not blob_client.exists():
                raise Exception(f"Blob not found: {blob_name}")
            
            # Get metadata
            blob_properties = blob_client.get_blob_properties()
            original_filename = blob_properties.metadata.get('original_filename', 'file.gpx')
            
            # Download to temp file
            input_ext = '.gpx' if conversion_type == 'gpx_to_kml' else '.kml'
            with tempfile.NamedTemporaryFile(suffix=input_ext, delete=False) as temp_input:
                temp_input_path = temp_input.name
                blob_data = blob_client.download_blob()
                temp_input.write(blob_data.readall())
            
            logger.info(f"✅ File downloaded: {temp_input_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to download file: {e}")
            raise
        
        # Convert file
        logger.info("-" * 100)
        logger.info(f"🔄 CONVERTING: {conversion_type}")
        
        try:
            with open(temp_input_path, 'r', encoding='utf-8') as f:
                input_content = f.read()
            
            if conversion_type == 'gpx_to_kml':
                output_content = _gpx_to_kml(input_content)
                output_ext = '.kml'
            else:
                output_content = _kml_to_gpx(input_content)
                output_ext = '.gpx'
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=output_ext, delete=False, mode='w', encoding='utf-8') as temp_output:
                temp_output_path = temp_output.name
                temp_output.write(output_content)
            
            output_size = Path(temp_output_path).stat().st_size
            logger.info(f"✅ Conversion completed")
            logger.info(f"   Output size: {output_size:,} bytes")
            
        except Exception as e:
            logger.error(f"❌ Conversion failed: {e}")
            raise
        
        # Upload converted file to blob storage
        logger.info("-" * 100)
        logger.info(f"📤 UPLOADING CONVERTED FILE TO BLOB STORAGE")
        
        try:
            input_stem = Path(original_filename).stem
            output_filename = f"{input_stem}{output_ext}"
            output_blob_name = f"gpx/{execution_id}{output_ext}"
            
            logger.info(f"   Container: processed")
            logger.info(f"   Blob: {output_blob_name}")
            
            output_blob_client = blob_service.get_blob_client(
                container="processed",
                blob=output_blob_name
            )
            
            with open(temp_output_path, "rb") as gpx_file:
                output_blob_client.upload_blob(
                    gpx_file,
                    overwrite=True,
                    metadata={
                        "execution_id": execution_id,
                        "original_filename": original_filename,
                        "output_filename": output_filename,
                        "conversion_type": conversion_type,
                    }
                )
            
            logger.info(f"✅ File uploaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to upload file: {e}")
            raise
        
        # Update database: completed
        try:
            logger.info("📝 Updating database status: completed")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE tool_executions 
                   SET status = %s,
                       completed_at = NOW(),
                       output_filename = %s,
                       output_size = %s,
                       output_blob_path = %s
                   WHERE id = %s""",
                ('completed', output_filename, output_size, f"processed/{output_blob_name}", execution_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: status = completed")
        except Exception as db_error:
            logger.warning(f"⚠️ Failed to update database: {db_error}")
        
        # Cleanup temp files
        try:
            if temp_input_path and os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if temp_output_path and os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
        except:
            pass
        
        logger.info("=" * 100)
        logger.info("✅ GPX/KML CONVERSION COMPLETED SUCCESSFULLY")
        logger.info("=" * 100)
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "success",
                "execution_id": execution_id,
                "output_filename": output_filename,
                "output_size": output_size
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error("=" * 100)
        logger.error("❌ GPX/KML CONVERSION FAILED")
        logger.error(f"   Execution ID: {execution_id}")
        logger.error(f"   Error: {str(e)}")
        logger.error("=" * 100)
        
        # Update database: failed
        if execution_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE tool_executions 
                       SET status = %s, 
                           error_message = %s,
                           updated_at = NOW()
                       WHERE id = %s""",
                    ('failed', str(e), execution_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as db_error:
                logger.error(f"❌ Failed to update database: {db_error}")
        
        # Cleanup temp files
        try:
            if temp_input_path and os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if temp_output_path and os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
        except:
            pass
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "error",
                "error": str(e),
                "execution_id": execution_id
            }),
            mimetype="application/json",
            status_code=500
        )


def _gpx_to_kml(gpx_content: str) -> str:
    """Convert GPX XML content to KML format."""
    import xml.etree.ElementTree as ET
    
    # Parse GPX
    root = ET.fromstring(gpx_content)
    gpx_ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    
    # Create KML structure
    kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    document = ET.SubElement(kml, 'Document')
    
    # Extract track name
    name_elem = root.find('.//gpx:name', gpx_ns) or root.find('.//gpx:trk/gpx:name', gpx_ns)
    if name_elem is not None and name_elem.text:
        ET.SubElement(document, 'name').text = name_elem.text
    
    # Convert waypoints
    for wpt in root.findall('.//gpx:wpt', gpx_ns):
        lat = wpt.get('lat')
        lon = wpt.get('lon')
        if lat and lon:
            placemark = ET.SubElement(document, 'Placemark')
            wpt_name = wpt.find('gpx:name', gpx_ns)
            if wpt_name is not None and wpt_name.text:
                ET.SubElement(placemark, 'name').text = wpt_name.text
            point = ET.SubElement(placemark, 'Point')
            ele = wpt.find('gpx:ele', gpx_ns)
            ele_val = ele.text if ele is not None and ele.text else '0'
            ET.SubElement(point, 'coordinates').text = f"{lon},{lat},{ele_val}"
    
    # Convert tracks
    for trk in root.findall('.//gpx:trk', gpx_ns):
        placemark = ET.SubElement(document, 'Placemark')
        trk_name = trk.find('gpx:name', gpx_ns)
        if trk_name is not None and trk_name.text:
            ET.SubElement(placemark, 'name').text = trk_name.text
        
        linestring = ET.SubElement(placemark, 'LineString')
        ET.SubElement(linestring, 'tessellate').text = '1'
        
        coords = []
        for trkpt in trk.findall('.//gpx:trkpt', gpx_ns):
            lat = trkpt.get('lat')
            lon = trkpt.get('lon')
            if lat and lon:
                ele = trkpt.find('gpx:ele', gpx_ns)
                ele_val = ele.text if ele is not None and ele.text else '0'
                coords.append(f"{lon},{lat},{ele_val}")
        
        ET.SubElement(linestring, 'coordinates').text = ' '.join(coords)
    
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(kml, encoding='unicode')


def _kml_to_gpx(kml_content: str) -> str:
    """Convert KML XML content to GPX format."""
    import xml.etree.ElementTree as ET
    
    # Parse KML
    root = ET.fromstring(kml_content)
    kml_ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    # Create GPX structure
    gpx = ET.Element('gpx', {
        'version': '1.1',
        'creator': 'MagicToolbox',
        'xmlns': 'http://www.topografix.com/GPX/1/1'
    })
    
    # Extract name
    name_elem = root.find('.//kml:name', kml_ns)
    if name_elem is not None and name_elem.text:
        metadata = ET.SubElement(gpx, 'metadata')
        ET.SubElement(metadata, 'name').text = name_elem.text
    
    # Convert placemarks
    for placemark in root.findall('.//kml:Placemark', kml_ns):
        pm_name = placemark.find('kml:name', kml_ns)
        
        # Check for Point (waypoint)
        point = placemark.find('.//kml:Point/kml:coordinates', kml_ns)
        if point is not None and point.text:
            coords = point.text.strip().split(',')
            if len(coords) >= 2:
                wpt = ET.SubElement(gpx, 'wpt', lat=coords[1], lon=coords[0])
                if pm_name is not None and pm_name.text:
                    ET.SubElement(wpt, 'name').text = pm_name.text
                if len(coords) >= 3:
                    ET.SubElement(wpt, 'ele').text = coords[2]
        
        # Check for LineString (track)
        linestring = placemark.find('.//kml:LineString/kml:coordinates', kml_ns)
        if linestring is not None and linestring.text:
            trk = ET.SubElement(gpx, 'trk')
            if pm_name is not None and pm_name.text:
                ET.SubElement(trk, 'name').text = pm_name.text
            trkseg = ET.SubElement(trk, 'trkseg')
            
            for coord in linestring.text.strip().split():
                parts = coord.split(',')
                if len(parts) >= 2:
                    trkpt = ET.SubElement(trkseg, 'trkpt', lat=parts[1], lon=parts[0])
                    if len(parts) >= 3:
                        ET.SubElement(trkpt, 'ele').text = parts[2]
    
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(gpx, encoding='unicode')


@app.route(route="gpx/speed", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def modify_gpx_speed(req: func.HttpRequest) -> func.HttpResponse:
    """
    Modify GPX track speed by adjusting timestamps.
    
    Expected JSON payload:
    {
        "execution_id": "uuid",
        "blob_name": "gpx/{uuid}.gpx",
        "speed_multiplier": 2.0
    }
    """
    import xml.etree.ElementTree as ET
    from datetime import timedelta
    import re
    
    execution_id = None
    temp_input_path = None
    temp_output_path = None
    
    try:
        logger.info("=" * 100)
        logger.info("⚡ GPX SPEED MODIFICATION STARTED")
        logger.info("=" * 100)
        
        # Parse request
        try:
            req_body = req.get_json()
            execution_id = req_body.get('execution_id')
            blob_name = req_body.get('blob_name')
            speed_multiplier = float(req_body.get('speed_multiplier', 1.0))
            
            logger.info(f"📋 Request Details:")
            logger.info(f"   Execution ID: {execution_id}")
            logger.info(f"   Blob Name: {blob_name}")
            logger.info(f"   Speed Multiplier: {speed_multiplier}x")
            
        except Exception as e:
            logger.error(f"❌ Failed to parse request: {e}")
            return func.HttpResponse(
                body=json.dumps({"error": "Invalid JSON payload"}),
                mimetype="application/json",
                status_code=400
            )
        
        if not all([execution_id, blob_name]):
            return func.HttpResponse(
                body=json.dumps({"error": "Missing required parameters"}),
                mimetype="application/json",
                status_code=400
            )
        
        if speed_multiplier <= 0 or speed_multiplier > 100:
            return func.HttpResponse(
                body=json.dumps({"error": "Speed multiplier must be between 0 and 100"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Update database: processing
        try:
            logger.info("📝 Updating database status: processing")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tool_executions SET status = %s, started_at = NOW() WHERE id = %s",
                ('processing', execution_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: status = processing")
        except Exception as db_error:
            logger.warning(f"⚠️ Failed to update database: {db_error}")
        
        # Initialize blob service
        logger.info("-" * 100)
        logger.info("🔐 INITIALIZING BLOB STORAGE CLIENT")
        blob_service = get_blob_service_client()
        logger.info("✅ Blob service client initialized")
        
        # Download GPX from blob storage
        logger.info("-" * 100)
        logger.info(f"📥 DOWNLOADING GPX FROM BLOB STORAGE")
        
        try:
            # Parse blob path
            if blob_name.startswith('uploads/'):
                actual_blob_name = blob_name.replace('uploads/', '', 1)
            else:
                actual_blob_name = blob_name
            
            logger.info(f"   Container: uploads")
            logger.info(f"   Blob path: {actual_blob_name}")
            
            blob_client = blob_service.get_blob_client(
                container="uploads",
                blob=actual_blob_name
            )
            
            if not blob_client.exists():
                raise Exception(f"Blob not found: {blob_name}")
            
            # Get metadata
            blob_properties = blob_client.get_blob_properties()
            original_filename = blob_properties.metadata.get('original_filename', 'track.gpx')
            
            # Download to temp file
            with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as temp_input:
                temp_input_path = temp_input.name
                blob_data = blob_client.download_blob()
                temp_input.write(blob_data.readall())
            
            logger.info(f"✅ GPX downloaded: {temp_input_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to download GPX: {e}")
            raise
        
        # Modify GPX timestamps
        logger.info("-" * 100)
        logger.info(f"🔄 MODIFYING GPX TIMESTAMPS (x{speed_multiplier})")
        
        try:
            with open(temp_input_path, 'r', encoding='utf-8') as f:
                gpx_content = f.read()
            
            modified_content = _modify_gpx_timestamps(gpx_content, speed_multiplier)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False, mode='w', encoding='utf-8') as temp_output:
                temp_output_path = temp_output.name
                temp_output.write(modified_content)
            
            output_size = Path(temp_output_path).stat().st_size
            logger.info(f"✅ Modification completed")
            logger.info(f"   Output size: {output_size:,} bytes")
            
        except Exception as e:
            logger.error(f"❌ Modification failed: {e}")
            raise
        
        # Upload modified GPX to blob storage
        logger.info("-" * 100)
        logger.info(f"📤 UPLOADING MODIFIED GPX TO BLOB STORAGE")
        
        try:
            input_stem = Path(original_filename).stem
            output_filename = f"{input_stem}_speed_{speed_multiplier}x.gpx"
            output_blob_name = f"gpx/{execution_id}.gpx"
            
            logger.info(f"   Container: processed")
            logger.info(f"   Blob: {output_blob_name}")
            
            output_blob_client = blob_service.get_blob_client(
                container="processed",
                blob=output_blob_name
            )
            
            with open(temp_output_path, "rb") as gpx_file:
                output_blob_client.upload_blob(
                    gpx_file,
                    overwrite=True,
                    metadata={
                        "execution_id": execution_id,
                        "original_filename": original_filename,
                        "output_filename": output_filename,
                        "speed_multiplier": str(speed_multiplier),
                    }
                )
            
            logger.info(f"✅ GPX uploaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to upload GPX: {e}")
            raise
        
        # Update database: completed
        try:
            logger.info("📝 Updating database status: completed")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE tool_executions 
                   SET status = %s,
                       completed_at = NOW(),
                       output_filename = %s,
                       output_size = %s,
                       output_blob_path = %s
                   WHERE id = %s""",
                ('completed', output_filename, output_size, f"processed/{output_blob_name}", execution_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: status = completed")
        except Exception as db_error:
            logger.warning(f"⚠️ Failed to update database: {db_error}")
        
        # Cleanup temp files
        try:
            if temp_input_path and os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if temp_output_path and os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
        except:
            pass
        
        logger.info("=" * 100)
        logger.info("✅ GPX SPEED MODIFICATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 100)
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "success",
                "execution_id": execution_id,
                "output_filename": output_filename,
                "output_size": output_size,
                "speed_multiplier": speed_multiplier
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error("=" * 100)
        logger.error("❌ GPX SPEED MODIFICATION FAILED")
        logger.error(f"   Execution ID: {execution_id}")
        logger.error(f"   Error: {str(e)}")
        logger.error("=" * 100)
        
        # Update database: failed
        if execution_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE tool_executions 
                       SET status = %s, 
                           error_message = %s,
                           updated_at = NOW()
                       WHERE id = %s""",
                    ('failed', str(e), execution_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as db_error:
                logger.error(f"❌ Failed to update database: {db_error}")
        
        # Cleanup temp files
        try:
            if temp_input_path and os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if temp_output_path and os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
        except:
            pass
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "error",
                "error": str(e),
                "execution_id": execution_id
            }),
            mimetype="application/json",
            status_code=500
        )


def _modify_gpx_timestamps(gpx_content: str, speed_multiplier: float) -> str:
    """Modify timestamps in GPX content to change apparent speed."""
    import re
    from datetime import timedelta
    
    # Find all timestamps in the GPX
    timestamp_pattern = re.compile(r'<time>([^<]+)</time>')
    timestamps = timestamp_pattern.findall(gpx_content)
    
    if len(timestamps) < 2:
        return gpx_content  # Nothing to modify
    
    # Parse first timestamp as reference
    def parse_timestamp(ts: str) -> datetime:
        # Handle various ISO formats
        for fmt in ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%S%z']:
            try:
                return datetime.strptime(ts.replace('+00:00', 'Z').rstrip('Z') + 'Z', fmt.replace('%z', 'Z'))
            except ValueError:
                continue
        # Fallback
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    
    first_time = parse_timestamp(timestamps[0])
    modified_content = gpx_content
    
    for ts in timestamps:
        try:
            current_time = parse_timestamp(ts)
            time_diff = (current_time - first_time).total_seconds()
            new_time_diff = time_diff / speed_multiplier
            new_time = first_time + timedelta(seconds=new_time_diff)
            new_ts = new_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            modified_content = modified_content.replace(f'<time>{ts}</time>', f'<time>{new_ts}</time>', 1)
        except Exception:
            continue  # Skip timestamps that can't be parsed
    
    return modified_content