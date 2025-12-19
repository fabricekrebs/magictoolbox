"""
GPX Track Analyzer tool.

Analyzes GPX files and provides detailed statistics about tracks including
distance, speed, elevation, and timing information.
"""

import json
import math
import os
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from django.core.files.uploadedfile import UploadedFile

from apps.core.exceptions import ToolExecutionError
from apps.tools.base import BaseTool


class GPXAnalyzer(BaseTool):
    """
    Analyze GPX tracks and provide detailed statistics.

    Provides comprehensive analysis including distance, speed, elevation, and timing data.
    """

    # Tool metadata
    name = "gpx-analyzer"
    display_name = "GPX Track Analyzer"
    description = (
        "Analyze GPS tracks and get detailed statistics including distance, elevation gain/loss, average and maximum speeds, moving time, and pace calculations. "
        "Exports comprehensive JSON data perfect for workout analysis, hiking routes, cycling tracks, and fitness tracking."
    )
    category = "file"
    version = "1.0.0"
    icon = "graph-up"

    # File constraints
    allowed_input_types = [".gpx"]
    max_file_size = 50 * 1024 * 1024  # 50MB

    # XML namespaces
    GPX_NS = {"gpx": "http://www.topografix.com/GPX/1/1"}

    @staticmethod
    def _find_elements_any_ns(parent: ET.Element, tag: str) -> list:
        """Find elements with given tag name, regardless of namespace."""
        ns_elements = parent.findall(f'.//{{{GPXAnalyzer.GPX_NS["gpx"]}}}{tag}')
        if ns_elements:
            return ns_elements
        return parent.findall(f".//{tag}")

    @staticmethod
    def _find_element_any_ns(parent: ET.Element, tag: str) -> Optional[ET.Element]:
        """Find first element with given tag name, regardless of namespace."""
        ns_element = parent.find(f'{{{GPXAnalyzer.GPX_NS["gpx"]}}}{tag}')
        if ns_element is not None:
            return ns_element
        return parent.find(tag)

    def validate(
        self, input_file: UploadedFile, parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate input GPX file."""
        if not self.validate_file_type(input_file.name):
            return False, f"File type not supported. Allowed: {', '.join(self.allowed_input_types)}"

        if not self.validate_file_size(input_file):
            return False, f"File size exceeds maximum of {self.max_file_size / (1024*1024):.1f}MB"

        return True, None

    def process(self, input_file: UploadedFile, parameters: Dict[str, Any]) -> Tuple[str, str]:
        """
        Analyze GPX file and return statistics as JSON.

        Returns:
            Tuple of (output_file_path, output_filename)
        """
        temp_input = None
        temp_output = None

        try:
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=".gpx") as tmp_in:
                for chunk in input_file.chunks():
                    tmp_in.write(chunk)
                temp_input = tmp_in.name

            # Parse GPX file
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
                json.dump(stats, tmp_out, indent=2)

            output_size = os.path.getsize(temp_output)
            self.logger.info(
                f"Successfully analyzed {input_file.name}: {output_size / 1024:.1f} KB"
            )

            # Cleanup input temp file
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)

            return temp_output, output_filename

        except Exception as e:
            self.logger.error(f"GPX analysis failed: {e}", exc_info=True)

            # Cleanup on error
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)
            if temp_output and os.path.exists(temp_output):
                os.unlink(temp_output)

            raise ToolExecutionError(f"GPX analysis failed: {str(e)}")

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
            "average_pace_min_per_km": "0:00",
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

                # Average pace (min/km)
                if stats["total_distance_km"] > 0:
                    pace_seconds = duration / stats["total_distance_km"]
                    pace_minutes = int(pace_seconds // 60)
                    pace_secs = int(pace_seconds % 60)
                    stats["average_pace_min_per_km"] = f"{pace_minutes}:{pace_secs:02d}"

        stats["max_speed_kmh"] = round(max_speed, 2)
        stats["total_distance_km"] = round(stats["total_distance_km"], 2)
        stats["elevation_gain_m"] = round(stats["elevation_gain_m"], 1)
        stats["elevation_loss_m"] = round(stats["elevation_loss_m"], 1)

        if stats["min_elevation_m"] is not None:
            stats["min_elevation_m"] = round(stats["min_elevation_m"], 1)
        if stats["max_elevation_m"] is not None:
            stats["max_elevation_m"] = round(stats["max_elevation_m"], 1)

        return stats

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
        """Clean up temporary files."""
        for path in file_paths:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                    self.logger.debug(f"Cleaned up temp file: {path}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup {path}: {e}")
