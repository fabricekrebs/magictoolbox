"""
Minimal Azure Function App - incrementally adding working functions.
Currently: health check, video rotation, GPX conversion, PDF conversion, image conversion.
"""

import logging
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import psycopg2
from pdf2docx import Converter
from PIL import Image

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
    """Get BlobServiceClient using connection string or Managed Identity."""
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    
    if connection_string and "127.0.0.1" in connection_string:
        logger.info("🔧 Using local Azurite for blob storage")
        return BlobServiceClient.from_connection_string(connection_string)
    
    storage_account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
    if not storage_account_name:
        logger.error("❌ Storage account name not configured")
        raise ValueError("AZURE_STORAGE_ACCOUNT_NAME not configured")
    
    logger.info(f"🔐 Using Azure Managed Identity for storage account: {storage_account_name}")
    account_url = f"https://{storage_account_name}.blob.core.windows.net"
    credential = DefaultAzureCredential()
    return BlobServiceClient(account_url=account_url, credential=credential)


def get_blob_client(container_name: str, blob_name: str):
    """Get BlobClient for a specific blob."""
    blob_service = get_blob_service_client()
    return blob_service.get_blob_client(container=container_name, blob=blob_name)


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
    logger.info(f"🔌 Connecting to database: {db_config['host']}:{db_config['port']}/{db_config['database']} as {db_config['user']}")
    try:
        conn = psycopg2.connect(**db_config)
        logger.info("✅ Database connection successful")
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint - validates blob storage and database connectivity.
    Query params:
        - detailed=true: Include connectivity test results
    """
    logger.info("🏥 Health check requested")
    
    detailed = req.params.get('detailed', '').lower() == 'true'
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "function_app": "running"
    }
    
    if detailed:
        # Test blob storage
        try:
            blob_service = get_blob_service_client()
            # Try to list containers
            containers = list(blob_service.list_containers(results_per_page=1))
            health_status["blob_storage"] = {
                "status": "connected",
                "account": os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "unknown")
            }
            logger.info("✅ Blob storage: Connected")
        except Exception as e:
            health_status["blob_storage"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "degraded"
            logger.error(f"❌ Blob storage: {e}")
        
        # Test database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            health_status["database"] = {
                "status": "connected",
                "host": os.environ.get("DB_HOST", "unknown")
            }
            logger.info("✅ Database: Connected")
        except Exception as e:
            health_status["database"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "degraded"
            logger.error(f"❌ Database: {e}")
    
    status_code = 200 if health_status["status"] in ["healthy", "degraded"] else 503
    
    return func.HttpResponse(
        body=json.dumps(health_status, indent=2),
        mimetype="application/json",
        status_code=status_code
    )


@app.route(route="video/rotate", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def rotate_video(req: func.HttpRequest) -> func.HttpResponse:
    """
    Rotate a video file uploaded to Azure Blob Storage.
    
    Expected JSON payload:
    {
        "execution_id": "uuid",
        "blob_name": "uploads/video/{uuid}.mp4",
        "rotation": 90  // 90, 180, or 270 degrees clockwise
    }
    """
    execution_id = None
    temp_input_path = None
    temp_output_path = None
    
    try:
        logger.info("=" * 80)
        logger.info("🎬 VIDEO ROTATION STARTED")
        logger.info("=" * 80)
        
        # Parse request
        try:
            req_body = req.get_json()
            execution_id = req_body.get('execution_id')
            blob_name = req_body.get('blob_name')
            rotation = int(req_body.get('rotation', 90))
            
            logger.info(f"📝 Execution ID: {execution_id}")
            logger.info(f"📦 Input blob: {blob_name}")
            logger.info(f"🔄 Rotation: {rotation}°")
            
            if not all([execution_id, blob_name]):
                raise ValueError("Missing required parameters: execution_id, blob_name")
            
            if rotation not in [90, 180, 270]:
                raise ValueError(f"Invalid rotation: {rotation}. Must be 90, 180, or 270")
                
        except (ValueError, KeyError) as e:
            logger.error(f"❌ Invalid request: {e}")
            return func.HttpResponse(
                body=json.dumps({"status": "error", "error": f"Invalid request: {str(e)}"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Get input filename from database
        input_filename = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT input_filename FROM tool_executions WHERE id = %s
            """, (execution_id,))
            result = cursor.fetchone()
            if result:
                input_filename = result[0]
            cursor.close()
            conn.close()
            logger.info(f"📝 Input filename: {input_filename}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to get input filename: {e}")
        
        # Update database status to 'processing'
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'processing',
                    updated_at = NOW()
                WHERE id = %s
            """, (execution_id,))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"✅ Database updated: status=processing")
        except Exception as db_error:
            logger.warning(f"⚠️  Database update failed: {db_error}")
        
        # Download video from blob storage
        logger.info("📥 Downloading video from blob storage...")
        blob_service_client = get_blob_service_client()
        
        # Extract container and blob path
        parts = blob_name.split('/', 1)
        container_name = parts[0] if len(parts) > 1 else 'video-uploads'
        blob_path = parts[1] if len(parts) > 1 else blob_name
        
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
        
        # Create temp file for input
        temp_input_path = tempfile.mktemp(suffix=Path(blob_name).suffix)
        with open(temp_input_path, 'wb') as f:
            blob_data = blob_client.download_blob()
            f.write(blob_data.readall())
        
        input_size = os.path.getsize(temp_input_path)
        logger.info(f"✅ Downloaded {input_size:,} bytes to {temp_input_path}")
        
        # Rotate video using ffmpeg
        logger.info(f"🔄 Rotating video {rotation}° clockwise...")
        temp_output_path = tempfile.mktemp(suffix='.mp4')
        
        # FFmpeg transpose values:
        # 90° clockwise: transpose=1
        # 180°: transpose=1,transpose=1
        # 270° clockwise (90° counter-clockwise): transpose=2
        transpose_map = {
            90: "transpose=1",
            180: "transpose=1,transpose=1",
            270: "transpose=2"
        }
        transpose_filter = transpose_map[rotation]
        
        # Use bundled ffmpeg from imageio-ffmpeg
        import subprocess
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        logger.info(f"📹 Using ffmpeg: {ffmpeg_exe}")
        
        cmd = [
            ffmpeg_exe,
            '-i', temp_input_path,
            '-vf', transpose_filter,
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-y',  # Overwrite output file
            temp_output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
        
        output_size = os.path.getsize(temp_output_path)
        logger.info(f"✅ Rotated video: {output_size:,} bytes")
        
        # Upload result to 'video-processed' container
        output_blob_name = f"video-processed/{execution_id}.mp4"
        logger.info(f"📤 Uploading to: {output_blob_name}")
        
        output_blob_client = blob_service_client.get_blob_client(
            container='video-processed',
            blob=f"{execution_id}.mp4"
        )
        
        with open(temp_output_path, 'rb') as f:
            output_blob_client.upload_blob(f, overwrite=True)
        
        logger.info(f"✅ Upload complete: {output_blob_name}")
        
        # Determine output filename (preserve original name, keep .mp4 extension)
        if input_filename:
            output_filename = Path(input_filename).stem + '.mp4'
        else:
            output_filename = f"{execution_id}.mp4"
        
        # Update database status to 'completed'
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'completed',
                    output_blob_path = %s,
                    output_filename = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """, (output_blob_name, output_filename, execution_id))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"✅ Database updated: status=completed, output_filename={output_filename}")
        except Exception as db_error:
            logger.warning(f"⚠️  Database update failed: {db_error}")
        
        logger.info("=" * 80)
        logger.info("✅ VIDEO ROTATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "success",
                "execution_id": execution_id,
                "output_blob": output_blob_name,
                "rotation": rotation
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"❌ Error during video rotation: {str(e)}", exc_info=True)
        
        # Update database status to 'failed'
        if execution_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tool_executions
                    SET status = 'failed',
                        error_message = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (str(e), execution_id))
                conn.commit()
                cursor.close()
                conn.close()
                logger.info(f"✅ Database updated: status=failed")
            except Exception as db_error:
                logger.warning(f"⚠️  Database update failed: {db_error}")
        
        return func.HttpResponse(
            body=json.dumps({"status": "error", "error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
        
    finally:
        # Cleanup temp files
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
            logger.info(f"🧹 Cleaned up temp input file")
        if temp_output_path and os.path.exists(temp_output_path):
            os.remove(temp_output_path)
            logger.info(f"🧹 Cleaned up temp output file")

@app.route(route="pdf/convert", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def convert_pdf_to_docx(req: func.HttpRequest) -> func.HttpResponse:
    """
    Convert PDF to DOCX.
    
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
        logger.info("=" * 80)
        logger.info("📄 PDF TO DOCX CONVERSION STARTED")
        logger.info("=" * 80)
        
        # Parse request
        req_body = req.get_json()
        execution_id = req_body.get('execution_id')
        blob_name = req_body.get('blob_name')
        
        logger.info(f"📝 Execution ID: {execution_id}")
        logger.info(f"📦 Blob: {blob_name}")
        
        if not all([execution_id, blob_name]):
            raise ValueError("Missing required parameters")
        
        # Get input filename from database
        input_filename = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT input_filename FROM tool_executions WHERE id = %s
            """, (execution_id,))
            result = cursor.fetchone()
            if result:
                input_filename = result[0]
            cursor.close()
            conn.close()
            logger.info(f"📝 Input filename: {input_filename}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to get input filename: {e}")
        
        # Update database: processing
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'processing', updated_at = NOW()
                WHERE id = %s
            """, (execution_id,))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: processing")
        except Exception as e:
            logger.warning(f"⚠️  Database update failed: {e}")
        
        # Download PDF
        logger.info("📥 Downloading PDF...")
        blob_service = get_blob_service_client()
        
        parts = blob_name.split('/', 1)
        container_name = parts[0] if len(parts) > 1 else 'pdf-uploads'
        blob_path = parts[1] if len(parts) > 1 else blob_name
        
        blob_client = blob_service.get_blob_client(container=container_name, blob=blob_path)
        
        temp_pdf_path = tempfile.mktemp(suffix='.pdf')
        with open(temp_pdf_path, 'wb') as f:
            blob_data = blob_client.download_blob()
            f.write(blob_data.readall())
        
        pdf_size = os.path.getsize(temp_pdf_path)
        logger.info(f"✅ Downloaded: {pdf_size:,} bytes")
        
        # Convert
        logger.info("🔄 Converting PDF to DOCX...")
        temp_docx_path = tempfile.mktemp(suffix='.docx')
        
        cv = Converter(temp_pdf_path)
        cv.convert(temp_docx_path, start=0, end=None)
        cv.close()
        
        docx_size = os.path.getsize(temp_docx_path)
        logger.info(f"✅ Converted: {docx_size:,} bytes")
        
        # Upload result
        output_blob_name = f"pdf-processed/{execution_id}.docx"
        logger.info(f"📤 Uploading to: {output_blob_name}")
        
        output_blob_client = blob_service.get_blob_client(
            container='pdf-processed',
            blob=f"{execution_id}.docx"
        )
        
        with open(temp_docx_path, 'rb') as f:
            output_blob_client.upload_blob(f, overwrite=True)
        
        logger.info("✅ Upload complete")
        
        # Determine output filename (preserve original name, change extension)
        if input_filename:
            output_filename = Path(input_filename).stem + '.docx'
        else:
            output_filename = f"{execution_id}.docx"
        
        # Update database: completed
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'completed',
                    output_blob_path = %s,
                    output_filename = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """, (output_blob_name, output_filename, execution_id))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"✅ Database updated: completed, output_filename={output_filename}")
        except Exception as e:
            logger.warning(f"⚠️  Database update failed: {e}")
        
        logger.info("=" * 80)
        logger.info("✅ PDF TO DOCX CONVERSION COMPLETED")
        logger.info("=" * 80)
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "success",
                "execution_id": execution_id,
                "output_blob": output_blob_name
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        
        if execution_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tool_executions
                    SET status = 'failed',
                        error_message = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (str(e), execution_id))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as db_error:
                logger.warning(f"⚠️  Database update failed: {db_error}")
        
        return func.HttpResponse(
            body=json.dumps({"status": "error", "error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
        
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            logger.info("🧹 Cleaned up temp PDF")
        if temp_docx_path and os.path.exists(temp_docx_path):
            os.remove(temp_docx_path)
            logger.info("🧹 Cleaned up temp DOCX")

# Helper functions for GPX/KML conversion
def _gpx_to_kml(gpx_content: str) -> str:
    """Convert GPX XML content to KML format."""
    import xml.etree.ElementTree as ET
    
    root = ET.fromstring(gpx_content)
    gpx_ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    
    kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    document = ET.SubElement(kml, 'Document')
    
    name_elem = root.find('.//gpx:name', gpx_ns) or root.find('.//gpx:trk/gpx:name', gpx_ns)
    if name_elem is not None and name_elem.text:
        ET.SubElement(document, 'name').text = name_elem.text
    
    for wpt in root.findall('.//gpx:wpt', gpx_ns):
        lat, lon = wpt.get('lat'), wpt.get('lon')
        if lat and lon:
            placemark = ET.SubElement(document, 'Placemark')
            wpt_name = wpt.find('gpx:name', gpx_ns)
            if wpt_name is not None and wpt_name.text:
                ET.SubElement(placemark, 'name').text = wpt_name.text
            point = ET.SubElement(placemark, 'Point')
            ele = wpt.find('gpx:ele', gpx_ns)
            ele_val = ele.text if ele is not None and ele.text else '0'
            ET.SubElement(point, 'coordinates').text = f"{lon},{lat},{ele_val}"
    
    for trk in root.findall('.//gpx:trk', gpx_ns):
        placemark = ET.SubElement(document, 'Placemark')
        trk_name = trk.find('gpx:name', gpx_ns)
        if trk_name is not None and trk_name.text:
            ET.SubElement(placemark, 'name').text = trk_name.text
        
        linestring = ET.SubElement(placemark, 'LineString')
        ET.SubElement(linestring, 'tessellate').text = '1'
        
        coords = []
        for trkpt in trk.findall('.//gpx:trkpt', gpx_ns):
            lat, lon = trkpt.get('lat'), trkpt.get('lon')
            if lat and lon:
                ele = trkpt.find('gpx:ele', gpx_ns)
                ele_val = ele.text if ele is not None and ele.text else '0'
                coords.append(f"{lon},{lat},{ele_val}")
        
        ET.SubElement(linestring, 'coordinates').text = ' '.join(coords)
    
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(kml, encoding='unicode')


def _kml_to_gpx(kml_content: str) -> str:
    """Convert KML XML content to GPX format."""
    import xml.etree.ElementTree as ET
    
    root = ET.fromstring(kml_content)
    kml_ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    gpx = ET.Element('gpx', {
        'version': '1.1',
        'creator': 'MagicToolbox',
        'xmlns': 'http://www.topografix.com/GPX/1/1'
    })
    
    name_elem = root.find('.//kml:name', kml_ns)
    if name_elem is not None and name_elem.text:
        metadata = ET.SubElement(gpx, 'metadata')
        ET.SubElement(metadata, 'name').text = name_elem.text
    
    for placemark in root.findall('.//kml:Placemark', kml_ns):
        pm_name = placemark.find('kml:name', kml_ns)
        
        point = placemark.find('.//kml:Point/kml:coordinates', kml_ns)
        if point is not None and point.text:
            coords = point.text.strip().split(',')
            if len(coords) >= 2:
                wpt = ET.SubElement(gpx, 'wpt', lat=coords[1], lon=coords[0])
                if pm_name is not None and pm_name.text:
                    ET.SubElement(wpt, 'name').text = pm_name.text
                if len(coords) >= 3:
                    ET.SubElement(wpt, 'ele').text = coords[2]
        
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


@app.route(route="gpx/convert", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def convert_gpx_kml(req: func.HttpRequest) -> func.HttpResponse:
    """
    Convert GPX to KML or KML to GPX.
    
    Expected JSON payload:
    {
        "execution_id": "uuid",
        "blob_name": "uploads/gpx/{uuid}.gpx",
        "conversion_type": "gpx_to_kml" or "kml_to_gpx"
    }
    """
    import xml.etree.ElementTree as ET
    
    execution_id = None
    temp_input_path = None
    temp_output_path = None
    
    try:
        logger.info("=" * 80)
        logger.info("🗺️  GPX/KML CONVERSION STARTED")
        logger.info("=" * 80)
        
        # Parse request
        req_body = req.get_json()
        execution_id = req_body.get('execution_id')
        blob_name = req_body.get('blob_name')
        conversion_type = req_body.get('conversion_type')
        
        logger.info(f"📝 Execution ID: {execution_id}")
        logger.info(f"📦 Blob: {blob_name}")
        logger.info(f"🔄 Type: {conversion_type}")
        
        if not all([execution_id, blob_name, conversion_type]):
            raise ValueError("Missing required parameters")
        
        if conversion_type not in ('gpx_to_kml', 'kml_to_gpx'):
            raise ValueError(f"Invalid conversion type: {conversion_type}")
        
        # Get input filename from database
        input_filename = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT input_filename FROM tool_executions WHERE id = %s
            """, (execution_id,))
            result = cursor.fetchone()
            if result:
                input_filename = result[0]
            cursor.close()
            conn.close()
            logger.info(f"📝 Input filename: {input_filename}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to get input filename: {e}")
        
        # Update database: processing
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'processing', updated_at = NOW()
                WHERE id = %s
            """, (execution_id,))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: processing")
        except Exception as e:
            logger.warning(f"⚠️  Database update failed: {e}")
        
        # Download file
        logger.info("📥 Downloading file...")
        blob_service = get_blob_service_client()
        
        parts = blob_name.split('/', 1)
        container_name = parts[0] if len(parts) > 1 else 'gpx-uploads'
        blob_path = parts[1] if len(parts) > 1 else blob_name
        
        blob_client = blob_service.get_blob_client(container=container_name, blob=blob_path)
        
        input_ext = '.gpx' if conversion_type == 'gpx_to_kml' else '.kml'
        temp_input_path = tempfile.mktemp(suffix=input_ext)
        
        with open(temp_input_path, 'wb') as f:
            blob_data = blob_client.download_blob()
            f.write(blob_data.readall())
        
        logger.info(f"✅ Downloaded: {os.path.getsize(temp_input_path):,} bytes")
        
        # Convert
        logger.info(f"🔄 Converting: {conversion_type}")
        with open(temp_input_path, 'r', encoding='utf-8') as f:
            input_content = f.read()
        
        if conversion_type == 'gpx_to_kml':
            output_content = _gpx_to_kml(input_content)
            output_ext = '.kml'
        else:
            output_content = _kml_to_gpx(input_content)
            output_ext = '.gpx'
        
        temp_output_path = tempfile.mktemp(suffix=output_ext)
        with open(temp_output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        output_size = os.path.getsize(temp_output_path)
        logger.info(f"✅ Converted: {output_size:,} bytes")
        
        # Upload result
        output_blob_name = f"gpx-processed/{execution_id}{output_ext}"
        logger.info(f"📤 Uploading to: {output_blob_name}")
        
        output_blob_client = blob_service.get_blob_client(
            container='gpx-processed',
            blob=f"{execution_id}{output_ext}"
        )
        
        with open(temp_output_path, 'rb') as f:
            output_blob_client.upload_blob(f, overwrite=True)
        
        logger.info("✅ Upload complete")
        
        # Determine output filename (preserve original name, change extension)
        if input_filename:
            output_filename = Path(input_filename).stem + output_ext
        else:
            output_filename = f"{execution_id}{output_ext}"
        
        # Update database: completed
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'completed',
                    output_blob_path = %s,
                    output_filename = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """, (output_blob_name, output_filename, execution_id))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"✅ Database updated: completed, output_filename={output_filename}")
        except Exception as e:
            logger.warning(f"⚠️  Database update failed: {e}")
        
        logger.info("=" * 80)
        logger.info("✅ GPX/KML CONVERSION COMPLETED")
        logger.info("=" * 80)
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "success",
                "execution_id": execution_id,
                "output_blob": output_blob_name,
                "conversion_type": conversion_type
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        
        if execution_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tool_executions
                    SET status = 'failed',
                        error_message = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (str(e), execution_id))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as db_error:
                logger.warning(f"⚠️  Database update failed: {db_error}")
        
        return func.HttpResponse(
            body=json.dumps({"status": "error", "error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
        
    finally:
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
            logger.info("🧹 Cleaned up temp input")
        if temp_output_path and os.path.exists(temp_output_path):
            os.remove(temp_output_path)
            logger.info("🧹 Cleaned up temp output")


@app.route(route="image/convert", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def convert_image(req: func.HttpRequest) -> func.HttpResponse:
    """Convert images between different formats (jpg, png, webp, gif, bmp)."""
    execution_id = None
    temp_input_path = None
    temp_output_path = None
    
    try:
        # Parse request body
        req_body = req.get_json()
        execution_id = req_body.get("execution_id")
        input_format = req_body.get("input_format", "").lower()
        output_format = req_body.get("output_format", "png").lower()
        quality = req_body.get("quality", 95)
        resize_width = req_body.get("resize_width")
        resize_height = req_body.get("resize_height")
        
        logger.info(f"🖼️  Image conversion request - ID: {execution_id}")
        logger.info(f"📝 Format: {input_format} → {output_format}, Quality: {quality}")
        
        if not execution_id:
            return func.HttpResponse(
                body=json.dumps({"status": "error", "error": "Missing execution_id"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Validate formats
        valid_formats = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp']
        if input_format not in valid_formats or output_format not in valid_formats:
            return func.HttpResponse(
                body=json.dumps({
                    "status": "error",
                    "error": f"Invalid format. Supported: {', '.join(valid_formats)}"
                }),
                mimetype="application/json",
                status_code=400
            )
        
        # Get input filename from database
        input_filename = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT input_filename FROM tool_executions WHERE id = %s
            """, (execution_id,))
            result = cursor.fetchone()
            if result:
                input_filename = result[0]
            cursor.close()
            conn.close()
            logger.info(f"📝 Input filename: {input_filename}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to get input filename: {e}")
        
        # Update status to processing
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'processing',
                    updated_at = NOW()
                WHERE id = %s
            """, (execution_id,))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Updated status to processing")
        except Exception as db_error:
            logger.warning(f"⚠️  Database update failed: {db_error}")
        
        # Download input image from blob storage
        input_ext = f".{input_format}" if input_format != 'jpeg' else '.jpg'
        blob_path = f"{execution_id}{input_ext}"
        logger.info(f"📥 Downloading from blob: image-uploads/{blob_path}")
        
        blob_client = get_blob_client("image-uploads", blob_path)
        temp_input_path = f"/tmp/{execution_id}_input{input_ext}"
        
        with open(temp_input_path, "wb") as f:
            blob_data = blob_client.download_blob()
            f.write(blob_data.readall())
        logger.info(f"✅ Downloaded input image: {os.path.getsize(temp_input_path)} bytes")
        
        # Convert image
        output_ext = f".{output_format}" if output_format != 'jpeg' else '.jpg'
        temp_output_path = f"/tmp/{execution_id}_output{output_ext}"
        
        logger.info("🔄 Converting image...")
        img = Image.open(temp_input_path)
        
        # Resize if requested
        if resize_width or resize_height:
            original_size = img.size
            if resize_width and resize_height:
                new_size = (resize_width, resize_height)
            elif resize_width:
                ratio = resize_width / img.size[0]
                new_size = (resize_width, int(img.size[1] * ratio))
            else:
                ratio = resize_height / img.size[1]
                new_size = (int(img.size[0] * ratio), resize_height)
            
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"📐 Resized: {original_size} → {new_size}")
        
        # Convert mode if necessary
        if output_format in ['jpg', 'jpeg']:
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
        elif output_format == 'png':
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGBA')
        
        # Save with appropriate settings
        save_kwargs = {}
        pil_format = output_format.upper()
        if output_format in ['jpg', 'jpeg']:
            pil_format = 'JPEG'  # PIL requires 'JPEG' not 'JPG'
            save_kwargs = {'quality': quality, 'optimize': True}
        elif output_format == 'png':
            save_kwargs = {'optimize': True}
        elif output_format == 'webp':
            save_kwargs = {'quality': quality}
        
        img.save(temp_output_path, format=pil_format, **save_kwargs)
        logger.info(f"✅ Converted image: {os.path.getsize(temp_output_path)} bytes")
        
        # Upload to processed container
        output_blob_path = f"{execution_id}{output_ext}"
        logger.info(f"📤 Uploading to blob: image-processed/{output_blob_path}")
        
        output_blob_client = get_blob_client("image-processed", output_blob_path)
        with open(temp_output_path, "rb") as f:
            output_blob_client.upload_blob(f, overwrite=True)
        logger.info("✅ Uploaded converted image")
        
        # Determine output filename (preserve original name, change extension)
        if input_filename:
            output_filename = Path(input_filename).stem + output_ext
        else:
            output_filename = f"{execution_id}{output_ext}"
        
        # Update database with success
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Set output_blob_path to include container and blob path for download endpoint
            output_blob_full_path = f"image-processed/{execution_id}{output_ext}"
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'completed',
                    output_file = %s,
                    output_blob_path = %s,
                    output_filename = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """, (f"{execution_id}{output_ext}", output_blob_full_path, output_filename, execution_id))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"✅ Updated database with completed status, output_filename={output_filename}")
        except Exception as db_error:
            logger.warning(f"⚠️  Database update failed: {db_error}")
        
        return func.HttpResponse(
            body=json.dumps({"status": "success", "message": "Image converted successfully"}),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"❌ Image conversion failed: {str(e)}")
        
        # Update database with failure
        if execution_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tool_executions
                    SET status = 'failed',
                        error_message = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (str(e), execution_id))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as db_error:
                logger.warning(f"⚠️  Database update failed: {db_error}")
        
        return func.HttpResponse(
            body=json.dumps({"status": "error", "error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
        
    finally:
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
            logger.info("🧹 Cleaned up temp input")
        if temp_output_path and os.path.exists(temp_output_path):
            os.remove(temp_output_path)
            logger.info("🧹 Cleaned up temp output")


@app.route(route="gpx/speed", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def modify_gpx_speed(req: func.HttpRequest) -> func.HttpResponse:
    """Modify GPX track speed by adjusting timestamps."""
    execution_id = None
    temp_input_path = None
    temp_output_path = None
    
    try:
        # Parse request body
        req_body = req.get_json()
        execution_id = req_body.get("execution_id")
        speed_multiplier = float(req_body.get("speed_multiplier", 1.0))
        
        logger.info(f"⚡ GPX speed modification - ID: {execution_id}, multiplier: {speed_multiplier}x")
        
        if not execution_id:
            return func.HttpResponse(
                body=json.dumps({"status": "error", "error": "Missing execution_id"}),
                mimetype="application/json",
                status_code=400
            )
        
        if speed_multiplier <= 0 or speed_multiplier > 100:
            return func.HttpResponse(
                body=json.dumps({"status": "error", "error": "Speed multiplier must be between 0 and 100"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Update status to processing
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'processing',
                    updated_at = NOW()
                WHERE id = %s
            """, (execution_id,))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Updated status to processing")
        except Exception as db_error:
            logger.warning(f"⚠️  Database update failed: {db_error}")
        
        # Download input GPX from blob storage
        blob_path = f"{execution_id}.gpx"
        logger.info(f"📥 Downloading from blob: gpx-uploads/{blob_path}")
        
        blob_client = get_blob_client("gpx-uploads", blob_path)
        temp_input_path = f"/tmp/{execution_id}_input.gpx"
        
        with open(temp_input_path, "wb") as f:
            blob_data = blob_client.download_blob()
            f.write(blob_data.readall())
        logger.info(f"✅ Downloaded input GPX: {os.path.getsize(temp_input_path)} bytes")
        
        # Modify GPX timestamps
        logger.info(f"🔄 Modifying timestamps (speed x{speed_multiplier})...")
        
        with open(temp_input_path, 'r', encoding='utf-8') as f:
            gpx_content = f.read()
        
        modified_content = _modify_gpx_timestamps(gpx_content, speed_multiplier)
        
        temp_output_path = f"/tmp/{execution_id}_output.gpx"
        with open(temp_output_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        logger.info(f"✅ Modified GPX: {os.path.getsize(temp_output_path)} bytes")
        
        # Upload to processed container
        output_blob_path = f"{execution_id}.gpx"
        logger.info(f"📤 Uploading to blob: gpx-processed/{output_blob_path}")
        
        output_blob_client = get_blob_client("gpx-processed", output_blob_path)
        with open(temp_output_path, "rb") as f:
            output_blob_client.upload_blob(f, overwrite=True)
        logger.info("✅ Uploaded modified GPX")
        
        # Get input filename for output naming
        input_filename = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT input_filename FROM tool_executions WHERE id = %s
            """, (execution_id,))
            result = cursor.fetchone()
            if result:
                input_filename = result[0]
            cursor.close()
            conn.close()
        except Exception as e:
            logger.warning(f"⚠️  Failed to get input filename: {e}")
        
        # Determine output filename (preserve original name)
        if input_filename:
            output_filename = input_filename
        else:
            output_filename = f"{execution_id}.gpx"
        
        # Update database with success
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            output_blob_full_path = f"gpx-processed/{execution_id}.gpx"
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'completed',
                    output_file = %s,
                    output_blob_path = %s,
                    output_filename = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """, (f"{execution_id}.gpx", output_blob_full_path, output_filename, execution_id))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"✅ Updated database with completed status, output_filename={output_filename}")
        except Exception as db_error:
            logger.warning(f"⚠️  Database update failed: {db_error}")
        
        return func.HttpResponse(
            body=json.dumps({"status": "success", "message": "GPX speed modified successfully"}),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"❌ GPX speed modification failed: {str(e)}")
        
        # Update database with failure
        if execution_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tool_executions
                    SET status = 'failed',
                        error_message = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (str(e), execution_id))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as db_error:
                logger.warning(f"⚠️  Database update failed: {db_error}")
        
        return func.HttpResponse(
            body=json.dumps({"status": "error", "error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
        
    finally:
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
            logger.info("🧹 Cleaned up temp input")
        if temp_output_path and os.path.exists(temp_output_path):
            os.remove(temp_output_path)
            logger.info("🧹 Cleaned up temp output")


def _modify_gpx_timestamps(gpx_content: str, speed_multiplier: float) -> str:
    """Modify timestamps in GPX content to change apparent speed."""
    import re
    from datetime import datetime, timedelta
    
    # Find all timestamps in the GPX
    timestamp_pattern = re.compile(r'<time>([^<]+)</time>')
    timestamps = timestamp_pattern.findall(gpx_content)
    
    if len(timestamps) < 2:
        return gpx_content  # Nothing to modify
    
    # Parse first timestamp as reference
    def parse_timestamp(ts: str) -> datetime:
        # Handle various ISO formats
        for fmt in ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%fZ']:
            try:
                return datetime.strptime(ts.replace('+00:00', 'Z').rstrip('Z') + 'Z', fmt)
            except ValueError:
                continue
        # Fallback: use fromisoformat
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


@app.route(route="image/ocr", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def extract_text_ocr(req: func.HttpRequest) -> func.HttpResponse:
    """Extract text from images using OCR (Optical Character Recognition)."""
    execution_id = None
    temp_input_path = None
    temp_output_path = None
    
    try:
        # Parse request body
        req_body = req.get_json()
        execution_id = req_body.get("execution_id")
        input_format = req_body.get("input_format", "png").lower()
        language = req_body.get("language", "eng")
        
        logger.info(f"📝 OCR extraction - ID: {execution_id}, language: {language}")
        
        if not execution_id:
            return func.HttpResponse(
                body=json.dumps({"status": "error", "error": "Missing execution_id"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Update status to processing
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'processing',
                    updated_at = NOW()
                WHERE id = %s
            """, (execution_id,))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Updated status to processing")
        except Exception as db_error:
            logger.warning(f"⚠️  Database update failed: {db_error}")
        
        # Download input image from blob storage
        input_ext = f".{input_format}"
        blob_path = f"image/{execution_id}{input_ext}"
        logger.info(f"📥 Downloading from blob: ocr-uploads/{blob_path}")
        
        blob_client = get_blob_client("ocr-uploads", blob_path)
        temp_input_path = f"/tmp/{execution_id}_input{input_ext}"
        
        with open(temp_input_path, "wb") as f:
            blob_data = blob_client.download_blob()
            f.write(blob_data.readall())
        logger.info(f"✅ Downloaded input image: {os.path.getsize(temp_input_path)} bytes")
        
        # Perform OCR using PaddleOCR
        logger.info(f"🔄 Extracting text with PaddleOCR...")
        
        try:
            from paddleocr import PaddleOCR
            
            # Map tesseract language codes to PaddleOCR codes
            lang_map = {
                'eng': 'en',
                'fra': 'french',
                'deu': 'german',
                'spa': 'spanish',
                'ita': 'italian',
                'por': 'portuguese',
                'rus': 'russian',
                'jpn': 'japan',
                'kor': 'korean',
                'chi_sim': 'ch',
                'chi_tra': 'chinese_cht',
                'ara': 'arabic',
            }
            paddle_lang = lang_map.get(language, 'en')
            
            logger.info(f"🔧 Initializing PaddleOCR for language: {paddle_lang}")
            # Initialize PaddleOCR (use_angle_cls=True for better accuracy, use_gpu=False for CPU)
            ocr = PaddleOCR(use_angle_cls=True, lang=paddle_lang, use_gpu=False, show_log=False)
            
            # Perform OCR
            logger.info(f"📖 Reading text from image...")
            result = ocr.ocr(temp_input_path, cls=True)
            
            # Extract text from results
            extracted_text = ""
            if result and result[0]:
                for line in result[0]:
                    if line and len(line) > 1:
                        text = line[1][0]  # line[1] is (text, confidence)
                        extracted_text += text + "\n"
            
            text_length = len(extracted_text)
            logger.info(f"✅ Extracted {text_length} characters")
            
        except ImportError:
            raise Exception("paddleocr not installed. Install with: pip install paddleocr")
        except Exception as ocr_err:
            raise Exception(f"OCR failed: {ocr_err}")
        
        # Save extracted text to temp file
        temp_output_path = f"/tmp/{execution_id}_output.txt"
        with open(temp_output_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        logger.info(f"✅ Saved text: {os.path.getsize(temp_output_path)} bytes")
        
        # Upload to processed container
        output_blob_path = f"{execution_id}.txt"
        full_output_blob_path = f"ocr-processed/{output_blob_path}"
        logger.info(f"📤 Uploading to blob: {full_output_blob_path}")
        
        output_blob_client = get_blob_client("ocr-processed", output_blob_path)
        with open(temp_output_path, "rb") as f:
            output_blob_client.upload_blob(f, overwrite=True)
        logger.info("✅ Uploaded OCR result")
        
        # Get input filename for output naming
        input_filename = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT input_filename FROM tool_executions WHERE id = %s
            """, (execution_id,))
            result = cursor.fetchone()
            if result:
                input_filename = result[0]
            cursor.close()
            conn.close()
        except Exception as e:
            logger.warning(f"⚠️  Failed to get input filename: {e}")
        
        # Determine output filename (preserve original name, change extension to .txt)
        if input_filename:
            output_filename = Path(input_filename).stem + '.txt'
        else:
            output_filename = f"{execution_id}.txt"
        
        # Update database with success
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'completed',
                    output_file = %s,
                    output_blob_path = %s,
                    output_filename = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (f"{execution_id}.txt", full_output_blob_path, output_filename, execution_id))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"✅ Updated database with completed status, output_filename={output_filename}")
        except Exception as db_error:
            logger.warning(f"⚠️  Database update failed: {db_error}")
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "success",
                "message": "OCR extraction completed",
                "text_length": text_length,
                "output_blob": full_output_blob_path,
                "output_size_bytes": os.path.getsize(temp_output_path)
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"❌ OCR extraction failed: {str(e)}")
        
        # Update database with failure
        if execution_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tool_executions
                    SET status = 'failed',
                        error_message = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (str(e), execution_id))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as db_error:
                logger.warning(f"⚠️  Database update failed: {db_error}")
        
        return func.HttpResponse(
            body=json.dumps({"status": "error", "error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
        
    finally:
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
            logger.info("🧹 Cleaned up temp input")
        if temp_output_path and os.path.exists(temp_output_path):
            os.remove(temp_output_path)
            logger.info("🧹 Cleaned up temp output")


@app.route(route="gpx/merge", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def merge_gpx_files(req: func.HttpRequest) -> func.HttpResponse:
    """Merge multiple GPX files into a single file."""
    execution_id = None
    temp_files = []
    temp_output_path = None
    
    try:
        # Parse request body
        req_body = req.get_json()
        execution_id = req_body.get("execution_id")
        file_count = req_body.get("file_count", 2)
        
        logger.info(f"🔗 GPX merge - ID: {execution_id}, files: {file_count}")
        
        if not execution_id or file_count < 2:
            return func.HttpResponse(
                body=json.dumps({"status": "error", "error": "Missing execution_id or file_count < 2"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Update status to processing
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'processing',
                    updated_at = NOW()
                WHERE id = %s
            """, (execution_id,))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Updated status to processing")
        except Exception as db_error:
            logger.warning(f"⚠️  Database update failed: {db_error}")
        
        # Download all GPX files from blob storage
        import xml.etree.ElementTree as ET
        
        gpx_roots = []
        for i in range(file_count):
            blob_path = f"{execution_id}_{i:03d}.gpx"
            logger.info(f"📥 Downloading [{i+1}/{file_count}]: gpx-uploads/{blob_path}")
            
            blob_client = get_blob_client("gpx-uploads", blob_path)
            temp_path = f"/tmp/{execution_id}_input_{i}.gpx"
            temp_files.append(temp_path)
            
            with open(temp_path, "wb") as f:
                blob_data = blob_client.download_blob()
                f.write(blob_data.readall())
            
            # Parse GPX
            tree = ET.parse(temp_path)
            gpx_roots.append(tree.getroot())
            logger.info(f"   ✅ Downloaded: {os.path.getsize(temp_path)} bytes")
        
        # Merge GPX files - simple sequential merge
        logger.info(f"🔄 Merging {file_count} GPX files...")
        
        GPX_NS = "{http://www.topografix.com/GPX/1/1}"
        
        # Use first file as base
        merged_root = gpx_roots[0]
        
        # Add all trackpoints from other files
        for gpx_root in gpx_roots[1:]:
            # Find all trackpoints
            for trk in gpx_root.findall(f"{GPX_NS}trk"):
                merged_root.append(trk)
        
        # Convert to string
        merged_tree = ET.ElementTree(merged_root)
        temp_output_path = f"/tmp/{execution_id}_output.gpx"
        merged_tree.write(temp_output_path, encoding='utf-8', xml_declaration=True)
        
        logger.info(f"✅ Merged GPX: {os.path.getsize(temp_output_path)} bytes")
        
        # Upload to processed container
        output_blob_path = f"{execution_id}.gpx"
        logger.info(f"📤 Uploading to blob: gpx-processed/{output_blob_path}")
        
        output_blob_client = get_blob_client("gpx-processed", output_blob_path)
        with open(temp_output_path, "rb") as f:
            output_blob_client.upload_blob(f, overwrite=True)
        logger.info("✅ Uploaded merged GPX")
        
        # Get input filename for output naming
        input_filename = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT input_filename FROM tool_executions WHERE id = %s
            """, (execution_id,))
            result = cursor.fetchone()
            if result:
                input_filename = result[0]
            cursor.close()
            conn.close()
        except Exception as e:
            logger.warning(f"⚠️  Failed to get input filename: {e}")
        
        # Determine output filename
        if input_filename:
            output_filename = 'merged_' + input_filename
        else:
            output_filename = f"merged_{execution_id}.gpx"
        
        # Update database with success
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            output_blob_full_path = f"gpx-processed/{execution_id}.gpx"
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'completed',
                    output_file = %s,
                    output_blob_path = %s,
                    output_filename = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """, (f"{execution_id}.gpx", output_blob_full_path, output_filename, execution_id))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Updated database with completed status")
        except Exception as db_error:
            logger.warning(f"⚠️  Database update failed: {db_error}")
        
        return func.HttpResponse(
            body=json.dumps({"status": "success", "message": f"Merged {file_count} GPX files"}),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"❌ GPX merge failed: {str(e)}")
        
        # Update database with failure
        if execution_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tool_executions
                    SET status = 'failed',
                        error_message = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (str(e), execution_id))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as db_error:
                logger.warning(f"⚠️  Database update failed: {db_error}")
        
        return func.HttpResponse(
            body=json.dumps({"status": "error", "error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
        
    finally:
        # Cleanup all temp files
        for temp_path in temp_files:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        if temp_output_path and os.path.exists(temp_output_path):
            os.remove(temp_output_path)
        logger.info("🧹 Cleaned up temp files")
