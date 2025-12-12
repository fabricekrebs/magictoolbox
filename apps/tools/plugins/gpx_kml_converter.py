"""
GPX to KML converter tool.

Converts GPS exchange format files between GPX and KML formats.
Supports bidirectional conversion with coordinate preservation.
Uses Azure Functions for async processing.
"""

import os
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from xml.dom import minidom

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from apps.core.exceptions import ToolExecutionError, ToolValidationError
from apps.tools.base import BaseTool

try:
    from azure.identity import AzureCliCredential, DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
except ImportError:
    AzureCliCredential = None
    DefaultAzureCredential = None
    BlobServiceClient = None


class GPXKMLConverter(BaseTool):
    """
    Convert GPS files between GPX and KML formats.

    Supports: GPX <-> KML conversion with waypoints, tracks, and routes.
    Uses async processing via Azure Functions for scalability.
    """

    # Tool metadata
    name = "gpx-kml-converter"
    display_name = "GPX ↔ KML Converter"
    description = "Convert GPS files bidirectionally between GPX and KML formats with full preservation of waypoints, tracks, and routes. Supports both single file and bulk conversion for easy GPS data interchange."
    category = "file"
    version = "1.0.0"
    icon = "geo-alt"

    # File constraints
    allowed_input_types = [".gpx", ".kml"]
    max_file_size = 50 * 1024 * 1024  # 50MB

    # Supported conversions
    SUPPORTED_CONVERSIONS = {
        "gpx_to_kml": {"from": "gpx", "to": "kml", "name": "GPX to KML"},
        "kml_to_gpx": {"from": "kml", "to": "gpx", "name": "KML to GPX"},
    }

    # XML namespaces
    GPX_NS = {"gpx": "http://www.topografix.com/GPX/1/1"}
    KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}

    def validate(
        self, input_file: UploadedFile, parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate input file and parameters.

        Required parameters:
        - conversion_type: Type of conversion (gpx_to_kml or kml_to_gpx)

        Optional parameters:
        - name: Document name for output file
        """
        # Validate file type
        if not self.validate_file_type(input_file.name):
            return False, f"File type not supported. Allowed: {', '.join(self.allowed_input_types)}"

        # Validate file size
        if not self.validate_file_size(input_file):
            return False, f"File size exceeds maximum of {self.max_file_size / (1024*1024):.1f}MB"

        # Validate conversion type
        conversion_type = parameters.get("conversion_type", "").lower()
        if not conversion_type:
            # Auto-detect from file extension
            file_ext = Path(input_file.name).suffix.lower()
            if file_ext == ".gpx":
                conversion_type = "gpx_to_kml"
            elif file_ext == ".kml":
                conversion_type = "kml_to_gpx"
            else:
                return False, "Cannot determine conversion type from file extension"
            parameters["conversion_type"] = conversion_type

        if conversion_type not in self.SUPPORTED_CONVERSIONS:
            return False, f"Unsupported conversion type: {conversion_type}"

        # Validate input file matches expected format
        file_ext = Path(input_file.name).suffix.lower()[1:]  # Remove dot
        expected_format = self.SUPPORTED_CONVERSIONS[conversion_type]["from"]
        if file_ext != expected_format:
            return (
                False,
                f"File extension .{file_ext} doesn't match conversion type (expected .{expected_format})",
            )

        return True, None

    def process(
        self, input_file: UploadedFile, parameters: Dict[str, Any], execution_id: str = None
    ) -> Tuple[str, Optional[str]]:
        """
        Upload GPS file to Azure Blob Storage for async processing.

        This method only uploads the file. The actual conversion is done by Azure Function.

        Args:
            input_file: Uploaded GPS file (GPX or KML)
            parameters: Must contain 'conversion_type' key
            execution_id: Optional execution ID (generated if not provided)

        Returns:
            Tuple of (execution_id, None) - None indicates async processing

        Raises:
            ToolExecutionError: If upload fails
        """
        conversion_type = parameters["conversion_type"].lower()
        doc_name = parameters.get("name", Path(input_file.name).stem)

        # Generate execution ID if not provided
        if not execution_id:
            execution_id = str(uuid.uuid4())

        try:
            self.logger.info("=" * 80)
            self.logger.info("📤 STARTING GPS FILE UPLOAD FOR ASYNC PROCESSING")
            self.logger.info(f"   Execution ID: {execution_id}")
            self.logger.info(f"   Original filename: {input_file.name}")
            self.logger.info(f"   File size: {input_file.size:,} bytes")
            self.logger.info(f"   Conversion type: {conversion_type}")
            self.logger.info("=" * 80)

            # Get blob service client
            blob_service = self._get_blob_service_client()

            # Upload to gpx container
            file_ext = Path(input_file.name).suffix
            blob_name = f"gpx/{execution_id}{file_ext}"
            blob_client = blob_service.get_blob_client(
                container="uploads",
                blob=blob_name
            )

            # Prepare metadata for Azure Function
            metadata = {
                "execution_id": execution_id,
                "original_filename": input_file.name,
                "conversion_type": conversion_type,
                "doc_name": doc_name,
                "file_size": str(input_file.size),
            }

            self.logger.info(f"📋 Blob metadata prepared: {metadata}")

            # Upload file
            self.logger.info(f"⬆️  Uploading GPS file to blob storage: {blob_name}")
            file_content = input_file.read()
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                metadata=metadata
            )

            self.logger.info("✅ GPS file uploaded successfully to Azure Blob Storage")
            self.logger.info(f"   Blob name: {blob_name}")
            self.logger.info(f"   Container: uploads")
            self.logger.info(f"   Size: {len(file_content):,} bytes")

            # Return execution_id and None to indicate async processing
            return execution_id, None

        except Exception as e:
            self.logger.error(f"❌ Failed to upload GPS file: {e}")
            raise ToolExecutionError(f"GPS file upload failed: {str(e)}")

    def _get_blob_service_client(self) -> BlobServiceClient:
        """
        Get Azure Blob Storage client.

        Uses connection string for local Azurite, DefaultAzureCredential for Azure.
        """
        connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)

        # Check for local development (Azurite)
        if connection_string and "127.0.0.1" in connection_string:
            self.logger.info("🔧 Using local Azurite for blob storage")
            return BlobServiceClient.from_connection_string(connection_string)

        # Production: Use Managed Identity / DefaultAzureCredential
        storage_account_name = getattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None) or getattr(
            settings, "AZURE_ACCOUNT_NAME", None
        )
        if not storage_account_name:
            self.logger.error("❌ Storage account name not configured")
            raise ToolExecutionError(
                "AZURE_STORAGE_ACCOUNT_NAME or AZURE_ACCOUNT_NAME not configured for production environment"
            )

        account_url = f"https://{storage_account_name}.blob.core.windows.net"

        # Use AzureCliCredential for local/testing, DefaultAzureCredential for production
        use_cli_auth = os.getenv("USE_AZURE_CLI_AUTH", "false").lower() == "true" or settings.DEBUG

        if use_cli_auth:
            self.logger.info(
                f"🔐 Using Azure CLI credential for storage account: {storage_account_name}"
            )
            credential = AzureCliCredential()
        else:
            self.logger.info(
                f"🔐 Using Azure Managed Identity for storage account: {storage_account_name}"
            )
            credential = DefaultAzureCredential()

        return BlobServiceClient(account_url=account_url, credential=credential)

    def _gpx_to_kml(self, gpx_root: ET.Element, doc_name: str) -> ET.Element:
        """Convert GPX to KML format."""
        # Create KML structure
        kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
        document = ET.SubElement(kml, "Document")

        # Add document name
        name_elem = ET.SubElement(document, "name")
        name_elem.text = doc_name

        # Add description
        desc_elem = ET.SubElement(document, "description")
        desc_elem.text = f'Converted from GPX on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

        # Define styles for different feature types
        self._add_kml_styles(document)

        # Extract namespace
        ns = {"gpx": "http://www.topografix.com/GPX/1/1"}
        if "}" in gpx_root.tag:
            ns_url = gpx_root.tag.split("}")[0][1:]
            ns = {"gpx": ns_url}

        # Convert waypoints
        waypoints = gpx_root.findall(".//gpx:wpt", ns)
        if waypoints:
            folder = ET.SubElement(document, "Folder")
            folder_name = ET.SubElement(folder, "name")
            folder_name.text = "Waypoints"

            for wpt in waypoints:
                self._convert_waypoint_to_placemark(wpt, folder, ns)

        # Convert tracks
        tracks = gpx_root.findall(".//gpx:trk", ns)
        if tracks:
            folder = ET.SubElement(document, "Folder")
            folder_name = ET.SubElement(folder, "name")
            folder_name.text = "Tracks"

            for trk in tracks:
                self._convert_track_to_placemark(trk, folder, ns)

        # Convert routes
        routes = gpx_root.findall(".//gpx:rte", ns)
        if routes:
            folder = ET.SubElement(document, "Folder")
            folder_name = ET.SubElement(folder, "name")
            folder_name.text = "Routes"

            for rte in routes:
                self._convert_route_to_placemark(rte, folder, ns)

        return kml

    def _kml_to_gpx(self, kml_root: ET.Element, doc_name: str) -> ET.Element:
        """Convert KML to GPX format."""
        # Create GPX structure
        gpx = ET.Element(
            "gpx",
            version="1.1",
            creator="MagicToolbox GPX/KML Converter",
            xmlns="http://www.topografix.com/GPX/1/1",
            attrib={
                "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": "http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd"
            },
        )

        # Add metadata
        metadata = ET.SubElement(gpx, "metadata")
        name_elem = ET.SubElement(metadata, "name")
        name_elem.text = doc_name
        desc_elem = ET.SubElement(metadata, "desc")
        desc_elem.text = f'Converted from KML on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        time_elem = ET.SubElement(metadata, "time")
        time_elem.text = datetime.now().isoformat() + "Z"

        # Extract namespace
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        if "}" in kml_root.tag:
            ns_url = kml_root.tag.split("}")[0][1:]
            ns = {"kml": ns_url}

        # Find all Placemarks
        placemarks = kml_root.findall(".//kml:Placemark", ns)

        for placemark in placemarks:
            # Check for Point (waypoint)
            point = placemark.find(".//kml:Point", ns)
            if point is not None:
                self._convert_placemark_to_waypoint(placemark, gpx, ns)
                continue

            # Check for LineString (track or route)
            linestring = placemark.find(".//kml:LineString", ns)
            if linestring is not None:
                self._convert_placemark_to_track(placemark, gpx, ns)
                continue

        return gpx

    def _add_kml_styles(self, document: ET.Element) -> None:
        """Add KML styles for different feature types."""
        # Waypoint style
        style = ET.SubElement(document, "Style", id="waypointStyle")
        icon_style = ET.SubElement(style, "IconStyle")
        icon = ET.SubElement(icon_style, "Icon")
        href = ET.SubElement(icon, "href")
        href.text = "http://maps.google.com/mapfiles/kml/pushpin/red-pushpin.png"

        # Track style
        style = ET.SubElement(document, "Style", id="trackStyle")
        line_style = ET.SubElement(style, "LineStyle")
        color = ET.SubElement(line_style, "color")
        color.text = "ff0000ff"  # Red
        width = ET.SubElement(line_style, "width")
        width.text = "3"

        # Route style
        style = ET.SubElement(document, "Style", id="routeStyle")
        line_style = ET.SubElement(style, "LineStyle")
        color = ET.SubElement(line_style, "color")
        color.text = "ff00ff00"  # Green
        width = ET.SubElement(line_style, "width")
        width.text = "3"

    def _convert_waypoint_to_placemark(self, wpt: ET.Element, parent: ET.Element, ns: dict) -> None:
        """Convert GPX waypoint to KML Placemark."""
        placemark = ET.SubElement(parent, "Placemark")

        # Name
        name_elem = wpt.find("gpx:name", ns)
        if name_elem is not None and name_elem.text:
            name = ET.SubElement(placemark, "name")
            name.text = name_elem.text

        # Description
        desc_elem = wpt.find("gpx:desc", ns)
        if desc_elem is not None and desc_elem.text:
            description = ET.SubElement(placemark, "description")
            description.text = desc_elem.text

        # Style
        style_url = ET.SubElement(placemark, "styleUrl")
        style_url.text = "#waypointStyle"

        # Point
        point = ET.SubElement(placemark, "Point")
        coordinates = ET.SubElement(point, "coordinates")

        lat = wpt.get("lat")
        lon = wpt.get("lon")
        ele_elem = wpt.find("gpx:ele", ns)
        ele = ele_elem.text if ele_elem is not None else "0"

        coordinates.text = f"{lon},{lat},{ele}"

    def _convert_track_to_placemark(self, trk: ET.Element, parent: ET.Element, ns: dict) -> None:
        """Convert GPX track to KML Placemark."""
        placemark = ET.SubElement(parent, "Placemark")

        # Name
        name_elem = trk.find("gpx:name", ns)
        if name_elem is not None and name_elem.text:
            name = ET.SubElement(placemark, "name")
            name.text = name_elem.text
        else:
            name = ET.SubElement(placemark, "name")
            name.text = "Track"

        # Description
        desc_elem = trk.find("gpx:desc", ns)
        if desc_elem is not None and desc_elem.text:
            description = ET.SubElement(placemark, "description")
            description.text = desc_elem.text

        # Style
        style_url = ET.SubElement(placemark, "styleUrl")
        style_url.text = "#trackStyle"

        # LineString
        linestring = ET.SubElement(placemark, "LineString")
        tessellate = ET.SubElement(linestring, "tessellate")
        tessellate.text = "1"
        coordinates = ET.SubElement(linestring, "coordinates")

        # Collect all track points
        coords = []
        trkpts = trk.findall(".//gpx:trkpt", ns)
        for trkpt in trkpts:
            lat = trkpt.get("lat")
            lon = trkpt.get("lon")
            ele_elem = trkpt.find("gpx:ele", ns)
            ele = ele_elem.text if ele_elem is not None else "0"
            coords.append(f"{lon},{lat},{ele}")

        coordinates.text = " ".join(coords)

    def _convert_route_to_placemark(self, rte: ET.Element, parent: ET.Element, ns: dict) -> None:
        """Convert GPX route to KML Placemark."""
        placemark = ET.SubElement(parent, "Placemark")

        # Name
        name_elem = rte.find("gpx:name", ns)
        if name_elem is not None and name_elem.text:
            name = ET.SubElement(placemark, "name")
            name.text = name_elem.text
        else:
            name = ET.SubElement(placemark, "name")
            name.text = "Route"

        # Description
        desc_elem = rte.find("gpx:desc", ns)
        if desc_elem is not None and desc_elem.text:
            description = ET.SubElement(placemark, "description")
            description.text = desc_elem.text

        # Style
        style_url = ET.SubElement(placemark, "styleUrl")
        style_url.text = "#routeStyle"

        # LineString
        linestring = ET.SubElement(placemark, "LineString")
        tessellate = ET.SubElement(linestring, "tessellate")
        tessellate.text = "1"
        coordinates = ET.SubElement(linestring, "coordinates")

        # Collect all route points
        coords = []
        rtepts = rte.findall(".//gpx:rtept", ns)
        for rtept in rtepts:
            lat = rtept.get("lat")
            lon = rtept.get("lon")
            ele_elem = rtept.find("gpx:ele", ns)
            ele = ele_elem.text if ele_elem is not None else "0"
            coords.append(f"{lon},{lat},{ele}")

        coordinates.text = " ".join(coords)

    def _convert_placemark_to_waypoint(
        self, placemark: ET.Element, gpx: ET.Element, ns: dict
    ) -> None:
        """Convert KML Placemark with Point to GPX waypoint."""
        point = placemark.find(".//kml:Point", ns)
        if point is None:
            return

        coords_elem = point.find("kml:coordinates", ns)
        if coords_elem is None or not coords_elem.text:
            return

        # Parse coordinates (lon,lat,ele or lon,lat)
        coords = coords_elem.text.strip().split(",")
        if len(coords) < 2:
            return

        lon, lat = coords[0].strip(), coords[1].strip()
        ele = coords[2].strip() if len(coords) > 2 else "0"

        # Create waypoint
        wpt = ET.SubElement(gpx, "wpt", lat=lat, lon=lon)

        # Add elevation
        ele_elem = ET.SubElement(wpt, "ele")
        ele_elem.text = ele

        # Name
        name_elem = placemark.find("kml:name", ns)
        if name_elem is not None and name_elem.text:
            name = ET.SubElement(wpt, "name")
            name.text = name_elem.text

        # Description
        desc_elem = placemark.find("kml:description", ns)
        if desc_elem is not None and desc_elem.text:
            desc = ET.SubElement(wpt, "desc")
            desc.text = desc_elem.text

    def _convert_placemark_to_track(self, placemark: ET.Element, gpx: ET.Element, ns: dict) -> None:
        """Convert KML Placemark with LineString to GPX track."""
        linestring = placemark.find(".//kml:LineString", ns)
        if linestring is None:
            return

        coords_elem = linestring.find("kml:coordinates", ns)
        if coords_elem is None or not coords_elem.text:
            return

        # Create track
        trk = ET.SubElement(gpx, "trk")

        # Name
        name_elem = placemark.find("kml:name", ns)
        if name_elem is not None and name_elem.text:
            name = ET.SubElement(trk, "name")
            name.text = name_elem.text

        # Description
        desc_elem = placemark.find("kml:description", ns)
        if desc_elem is not None and desc_elem.text:
            desc = ET.SubElement(trk, "desc")
            desc.text = desc_elem.text

        # Track segment
        trkseg = ET.SubElement(trk, "trkseg")

        # Parse coordinates
        coords_text = coords_elem.text.strip()
        coord_pairs = coords_text.split()

        for coord_pair in coord_pairs:
            coords = coord_pair.split(",")
            if len(coords) < 2:
                continue

            lon, lat = coords[0].strip(), coords[1].strip()
            ele = coords[2].strip() if len(coords) > 2 else "0"

            # Create track point
            trkpt = ET.SubElement(trkseg, "trkpt", lat=lat, lon=lon)
            ele_elem = ET.SubElement(trkpt, "ele")
            ele_elem.text = ele

    def cleanup(self, *file_paths: str) -> None:
        """
        Remove temporary files (not used in async mode).

        Args:
            *file_paths: Paths to files to remove
        """
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                    self.logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup {file_path}: {e}")

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get tool metadata including conversion options.

        Returns:
            Dictionary with tool information and conversion options
        """
        metadata = super().get_metadata()
        metadata["conversionOptions"] = [
            {
                "value": key,
                "label": config["name"],
                "from": config["from"],
                "to": config["to"],
            }
            for key, config in self.SUPPORTED_CONVERSIONS.items()
        ]
        return metadata
