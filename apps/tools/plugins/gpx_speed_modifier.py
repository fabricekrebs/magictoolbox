"""
GPX Speed Modifier tool.

Analyzes GPX files and allows modification of track speeds while preserving
distance and elevation data. Provides detailed statistics about the track.
"""

import math
import os
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from xml.dom import minidom

from django.core.files.uploadedfile import UploadedFile

from apps.core.exceptions import ToolExecutionError, ToolValidationError
from apps.tools.base import BaseTool

# Register namespaces once at module level to preserve original prefixes
# Note: The order and prefixes must match Garmin's original GPX files
try:
    ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")
    ET.register_namespace("ns3", "http://www.garmin.com/xmlschemas/TrackPointExtension/v1")
    ET.register_namespace("ns2", "http://www.garmin.com/xmlschemas/GpxExtensions/v3")
except ValueError:
    # Already registered, ignore
    pass


class GPXSpeedModifier(BaseTool):
    """
    Analyze and modify GPX track speeds.

    Supports: Speed analysis, statistics, and speed modification with time recalculation
    """

    # Tool metadata
    name = "gpx-speed-modifier"
    display_name = "GPX Speed Modifier"
    description = (
        "Analyze GPX tracks and modify average speed while preserving distance and elevation"
    )
    category = "file"
    version = "1.0.0"
    icon = "speedometer2"

    # File constraints
    allowed_input_types = [".gpx"]
    max_file_size = 50 * 1024 * 1024  # 50MB

    # XML namespaces
    GPX_NS = {"gpx": "http://www.topografix.com/GPX/1/1"}

    @staticmethod
    def _find_elements_any_ns(parent: ET.Element, tag: str) -> list:
        """Find elements with given tag name, regardless of namespace."""
        # Try with namespace
        ns_elements = parent.findall(f'.//{{{GPXSpeedModifier.GPX_NS["gpx"]}}}{tag}')
        if ns_elements:
            return ns_elements
        # Try without namespace (for legacy files)
        return parent.findall(f".//{tag}")

    @staticmethod
    def _find_element_any_ns(parent: ET.Element, tag: str) -> Optional[ET.Element]:
        """Find first element with given tag name, regardless of namespace."""
        # Try with namespace
        ns_element = parent.find(f'{{{GPXSpeedModifier.GPX_NS["gpx"]}}}{tag}')
        if ns_element is not None:
            return ns_element
        # Try without namespace (for legacy files)
        return parent.find(tag)

    def validate(
        self, input_file: UploadedFile, parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate input file and parameters.

        Required parameters:
        - mode: 'analyze' or 'modify'

        Optional parameters (for modify mode):
        - speed_multiplier: Float multiplier for speed (0.5 = half speed, 2.0 = double speed)
        """
        # Validate file type
        if not self.validate_file_type(input_file.name):
            return False, f"File type not supported. Allowed: {', '.join(self.allowed_input_types)}"

        # Validate file size
        if not self.validate_file_size(input_file):
            return False, f"File size exceeds maximum of {self.max_file_size / (1024*1024):.1f}MB"

        # Validate mode
        mode = parameters.get("mode", "").lower()
        if not mode:
            return False, "Missing required parameter: mode"

        if mode not in ["analyze", "modify"]:
            return False, "Mode must be 'analyze' or 'modify'"

        # Validate speed_multiplier for modify mode
        if mode == "modify":
            speed_multiplier = parameters.get("speed_multiplier")
            if speed_multiplier is None:
                return False, "Missing required parameter: speed_multiplier"

            try:
                speed_multiplier = float(speed_multiplier)
                if not 0.1 <= speed_multiplier <= 10.0:
                    return False, "Speed multiplier must be between 0.1 and 10.0"
            except (ValueError, TypeError):
                return False, "Speed multiplier must be a number"

        return True, None

    def process(self, input_file: UploadedFile, parameters: Dict[str, Any]) -> Tuple[str, str]:
        """
        Process GPX file - analyze or modify speed.

        Returns:
            Tuple of (output_file_path, output_filename)
        """
        mode = parameters["mode"].lower()

        temp_input = None
        temp_output = None

        try:
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=".gpx") as tmp_in:
                for chunk in input_file.chunks():
                    tmp_in.write(chunk)
                temp_input = tmp_in.name

            if mode == "analyze":
                # Parse for analysis only
                try:
                    tree = ET.parse(temp_input)
                    root = tree.getroot()
                except ET.ParseError as e:
                    raise ToolExecutionError(f"Invalid GPX file: {str(e)}")

                # Analyze the track
                stats = self._analyze_gpx(root)

                # Return a JSON file with statistics
                output_filename = f"{Path(input_file.name).stem}_analysis.json"
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".json", mode="w", encoding="utf-8"
                ) as tmp_out:
                    temp_output = tmp_out.name
                    import json

                    json.dump(stats, tmp_out, indent=2)

            else:  # modify mode
                speed_multiplier = float(parameters["speed_multiplier"])

                # Read the entire GPX file as text
                with open(temp_input, "r", encoding="utf-8") as f:
                    gpx_content = f.read()

                # Modify timestamps using regex while preserving exact structure
                modified_content = self._modify_timestamps_in_text(gpx_content, speed_multiplier)

                # Create output file
                output_filename = f"{Path(input_file.name).stem}_speed_{speed_multiplier}x.gpx"
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".gpx", mode="w", encoding="utf-8"
                ) as tmp_out:
                    temp_output = tmp_out.name
                    tmp_out.write(modified_content)

            output_size = os.path.getsize(temp_output)
            self.logger.info(
                f"Successfully processed {input_file.name} ({mode} mode): {output_size / 1024:.1f} KB"
            )

            # Cleanup input temp file
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)

            return temp_output, output_filename

        except Exception as e:
            self.logger.error(f"GPX processing failed: {e}", exc_info=True)

            # Cleanup on error
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)
            if temp_output and os.path.exists(temp_output):
                os.unlink(temp_output)

            raise ToolExecutionError(f"GPX processing failed: {str(e)}")

    def _analyze_gpx(self, root: ET.Element) -> Dict[str, Any]:
        """
        Analyze GPX track and calculate statistics.

        Returns:
            Dictionary with track statistics
        """
        stats = {
            "total_distance_km": 0.0,
            "total_duration_seconds": 0,
            "total_duration_formatted": "0:00:00",
            "average_speed_kmh": 0.0,
            "max_speed_kmh": 0.0,
            "elevation_gain_m": 0.0,
            "elevation_loss_m": 0.0,
            "min_elevation_m": None,
            "max_elevation_m": None,
            "total_points": 0,
            "start_time": None,
            "end_time": None,
        }

        # Find all track points
        all_points = []
        for trk in self._find_elements_any_ns(root, "trk"):
            for trkseg in self._find_elements_any_ns(trk, "trkseg"):
                for trkpt in self._find_elements_any_ns(trkseg, "trkpt"):
                    lat = float(trkpt.get("lat"))
                    lon = float(trkpt.get("lon"))

                    ele_elem = self._find_element_any_ns(trkpt, "ele")
                    ele = float(ele_elem.text) if ele_elem is not None else None

                    time_elem = self._find_element_any_ns(trkpt, "time")
                    time = None
                    if time_elem is not None and time_elem.text:
                        try:
                            time = datetime.fromisoformat(time_elem.text.replace("Z", "+00:00"))
                        except (ValueError, AttributeError):
                            pass

                    all_points.append({"lat": lat, "lon": lon, "ele": ele, "time": time})

        if not all_points:
            return stats

        stats["total_points"] = len(all_points)

        # Calculate statistics
        prev_point = None
        max_speed = 0.0

        for point in all_points:
            # Elevation stats
            if point["ele"] is not None:
                if stats["min_elevation_m"] is None or point["ele"] < stats["min_elevation_m"]:
                    stats["min_elevation_m"] = point["ele"]
                if stats["max_elevation_m"] is None or point["ele"] > stats["max_elevation_m"]:
                    stats["max_elevation_m"] = point["ele"]

            if prev_point:
                # Distance calculation
                dist = self._haversine_distance(
                    prev_point["lat"], prev_point["lon"], point["lat"], point["lon"]
                )
                stats["total_distance_km"] += dist

                # Elevation gain/loss
                if prev_point["ele"] is not None and point["ele"] is not None:
                    ele_diff = point["ele"] - prev_point["ele"]
                    if ele_diff > 0:
                        stats["elevation_gain_m"] += ele_diff
                    else:
                        stats["elevation_loss_m"] += abs(ele_diff)

                # Speed calculation
                if prev_point["time"] and point["time"]:
                    time_diff = (point["time"] - prev_point["time"]).total_seconds()
                    if time_diff > 0:
                        speed_kmh = (dist / time_diff) * 3600
                        if speed_kmh > max_speed and speed_kmh < 200:  # Reasonable max speed
                            max_speed = speed_kmh

            prev_point = point

        # Time-based statistics
        times = [p["time"] for p in all_points if p["time"]]
        if times:
            stats["start_time"] = times[0].isoformat()
            stats["end_time"] = times[-1].isoformat()
            duration = (times[-1] - times[0]).total_seconds()
            stats["total_duration_seconds"] = int(duration)

            # Format duration
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            stats["total_duration_formatted"] = f"{hours}:{minutes:02d}:{seconds:02d}"

            # Average speed
            if duration > 0:
                stats["average_speed_kmh"] = round(
                    (stats["total_distance_km"] / duration) * 3600, 2
                )

        stats["max_speed_kmh"] = round(max_speed, 2)
        stats["total_distance_km"] = round(stats["total_distance_km"], 2)
        stats["elevation_gain_m"] = round(stats["elevation_gain_m"], 1)
        stats["elevation_loss_m"] = round(stats["elevation_loss_m"], 1)

        if stats["min_elevation_m"] is not None:
            stats["min_elevation_m"] = round(stats["min_elevation_m"], 1)
        if stats["max_elevation_m"] is not None:
            stats["max_elevation_m"] = round(stats["max_elevation_m"], 1)

        return stats

    def _modify_timestamps_in_text(self, gpx_content: str, speed_multiplier: float) -> str:
        """
        Modify timestamps in GPX text while preserving exact file structure.

        This approach uses regex to find and replace timestamps without parsing XML,
        ensuring the file structure, namespaces, and formatting remain identical.

        Args:
            gpx_content: Original GPX file content as string
            speed_multiplier: Speed multiplier factor

        Returns:
            Modified GPX content with adjusted timestamps
        """
        import re

        # Find all <time> elements with their timestamps
        time_pattern = r"<time>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z)</time>"
        matches = list(re.finditer(time_pattern, gpx_content))

        if not matches:
            return gpx_content

        # Parse first timestamp as reference
        first_timestamp_str = matches[0].group(1)
        start_time = datetime.fromisoformat(first_timestamp_str.replace("Z", "+00:00"))

        # Calculate time multiplier (inverse of speed)
        time_multiplier = 1.0 / speed_multiplier

        # Build replacement map
        replacements = {}
        current_time = start_time

        for i, match in enumerate(matches):
            old_timestamp_str = match.group(1)

            if i == 0:
                # Keep first timestamp as-is
                new_time = start_time
            else:
                # Calculate original time difference from previous point
                orig_time = datetime.fromisoformat(old_timestamp_str.replace("Z", "+00:00"))
                prev_timestamp_str = matches[i - 1].group(1)
                prev_time = datetime.fromisoformat(prev_timestamp_str.replace("Z", "+00:00"))

                time_diff = (orig_time - prev_time).total_seconds()

                # Apply time multiplier
                new_time_diff = time_diff * time_multiplier
                new_time = current_time + timedelta(seconds=new_time_diff)

            current_time = new_time

            # Format new timestamp to match original format (with or without milliseconds)
            if "." in old_timestamp_str:
                new_timestamp_str = new_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            else:
                new_timestamp_str = new_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            replacements[old_timestamp_str] = new_timestamp_str

        # Apply replacements in reverse order to avoid offset issues
        result = gpx_content
        for match in reversed(matches):
            old_ts = match.group(1)
            new_ts = replacements[old_ts]
            start_pos = match.start(1)
            end_pos = match.end(1)
            result = result[:start_pos] + new_ts + result[end_pos:]

        return result

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula.

        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def cleanup(self, *file_paths: str) -> None:
        """
        Clean up temporary files after download.

        Args:
            *file_paths: Paths to temporary files to delete
        """
        for path in file_paths:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                    self.logger.debug(f"Cleaned up temp file: {path}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup {path}: {e}")
