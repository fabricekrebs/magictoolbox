"""
GPX to KML converter tool.

Converts GPS exchange format files between GPX and KML formats.
Supports bidirectional conversion with coordinate preservation.
"""

from typing import Any, Dict, Optional, Tuple
from django.core.files.uploadedfile import UploadedFile
from apps.tools.base import BaseTool
from apps.core.exceptions import ToolValidationError, ToolExecutionError
from pathlib import Path
import tempfile
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime


class GPXKMLConverter(BaseTool):
    """
    Convert GPS files between GPX and KML formats.

    Supports: GPX <-> KML conversion with waypoints, tracks, and routes
    """

    # Tool metadata
    name = "gpx-kml-converter"
    display_name = "GPX/KML Converter"
    description = "Convert GPS files between GPX and KML formats"
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

    def process(self, input_file: UploadedFile, parameters: Dict[str, Any]) -> Tuple[str, str]:
        """
        Convert GPS file between GPX and KML formats.

        Returns:
            Tuple of (output_file_path, output_filename)
        """
        conversion_type = parameters["conversion_type"].lower()
        doc_name = parameters.get("name", Path(input_file.name).stem)

        temp_input = None
        temp_output = None

        try:
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=Path(input_file.name).suffix
            ) as tmp_in:
                for chunk in input_file.chunks():
                    tmp_in.write(chunk)
                temp_input = tmp_in.name

            # Parse input file
            try:
                tree = ET.parse(temp_input)
                root = tree.getroot()
            except ET.ParseError as e:
                raise ToolExecutionError(f"Invalid XML file: {str(e)}")

            # Perform conversion
            if conversion_type == "gpx_to_kml":
                output_tree = self._gpx_to_kml(root, doc_name)
                output_ext = ".kml"
            elif conversion_type == "kml_to_gpx":
                output_tree = self._kml_to_gpx(root, doc_name)
                output_ext = ".gpx"
            else:
                raise ToolExecutionError(f"Unsupported conversion: {conversion_type}")

            # Create output file - always use original filename with new extension
            output_filename = f"{Path(input_file.name).stem}{output_ext}"
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=output_ext, mode="w", encoding="utf-8"
            ) as tmp_out:
                temp_output = tmp_out.name
                # Pretty print XML
                xml_str = ET.tostring(output_tree, encoding="unicode")
                dom = minidom.parseString(xml_str)
                tmp_out.write(dom.toprettyxml(indent="  "))

            output_size = os.path.getsize(temp_output)
            self.logger.info(
                f"Successfully converted {input_file.name} ({conversion_type}): {output_size / 1024:.1f} KB"
            )

            # Cleanup input temp file
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)

            return temp_output, output_filename

        except Exception as e:
            self.logger.error(f"GPS conversion failed: {e}", exc_info=True)

            # Cleanup on error
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)
            if temp_output and os.path.exists(temp_output):
                os.unlink(temp_output)

            raise ToolExecutionError(f"GPS conversion failed: {str(e)}")

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
        """Remove temporary files."""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                    self.logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup file {file_path}: {e}")
