"""
Minimal Azure Function App for testing function discovery.
Starting with health check and video rotation only.
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
    logger.info("🏥 Health check requested")
    return func.HttpResponse(
        body=json.dumps({
            "status": "healthy",
            "message": "Azure Function is running successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }),
        mimetype="application/json",
        status_code=200
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
        
        # Update database status to 'processing'
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tools_toolexecution
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
        container_name = parts[0] if len(parts) > 1 else 'uploads'
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
        
        import subprocess
        cmd = [
            'ffmpeg',
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
        
        # Upload result to 'processed' container
        output_blob_name = f"processed/video/{execution_id}.mp4"
        logger.info(f"📤 Uploading to: {output_blob_name}")
        
        output_blob_client = blob_service_client.get_blob_client(
            container='processed',
            blob=f"video/{execution_id}.mp4"
        )
        
        with open(temp_output_path, 'rb') as f:
            output_blob_client.upload_blob(f, overwrite=True)
        
        logger.info(f"✅ Upload complete: {output_blob_name}")
        
        # Update database status to 'completed'
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tools_toolexecution
                SET status = 'completed',
                    output_blob_path = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """, (output_blob_name, execution_id))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"✅ Database updated: status=completed")
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
                    UPDATE tools_toolexecution
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
        
        # Update database: processing
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tools_toolexecution
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
        container_name = parts[0] if len(parts) > 1 else 'uploads'
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
        output_blob_name = f"processed/gpx/{execution_id}{output_ext}"
        logger.info(f"📤 Uploading to: {output_blob_name}")
        
        output_blob_client = blob_service.get_blob_client(
            container='processed',
            blob=f"gpx/{execution_id}{output_ext}"
        )
        
        with open(temp_output_path, 'rb') as f:
            output_blob_client.upload_blob(f, overwrite=True)
        
        logger.info("✅ Upload complete")
        
        # Update database: completed
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tools_toolexecution
                SET status = 'completed',
                    output_blob_path = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """, (output_blob_name, execution_id))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: completed")
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
                    UPDATE tools_toolexecution
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
