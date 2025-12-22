"""
EXIF Metadata Extractor Tool

Extracts EXIF metadata from images and provides formatted output.
Supports JSON and CSV export formats.
"""

import csv
import io
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from django.core.files.uploadedfile import UploadedFile

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

from apps.tools.base import BaseTool


class EXIFExtractor(BaseTool):
    """Tool for extracting EXIF metadata from images."""

    name = "exif-extractor"
    display_name = "EXIF Metadata Extractor"
    description = "Extract EXIF metadata from images including camera settings, GPS location, timestamps, and more. Export as JSON or CSV."
    category = "image"
    version = "1.0.0"
    icon = "image"

    allowed_input_types = [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".heic"]
    max_file_size = 20 * 1024 * 1024  # 20MB
    requires_file_upload = True

    def get_metadata(self) -> Dict[str, Any]:
        """Return tool metadata."""
        base_metadata = super().get_metadata()
        base_metadata.update(
            {
                "export_formats": ["json", "csv"],
                "supports_gps": True,
                "max_file_size_mb": self.max_file_size / (1024 * 1024),
            }
        )
        return base_metadata

    def validate(
        self,
        input_file: Optional[UploadedFile] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate input image file.

        Args:
            input_file: Uploaded image file
            parameters: Optional export format preference

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not input_file:
            return False, "No image file provided."

        # Check file size
        if input_file.size > self.max_file_size:
            max_mb = self.max_file_size / (1024 * 1024)
            return False, f"File size exceeds maximum limit of {max_mb}MB."

        # Check file type
        file_ext = f".{input_file.name.split('.')[-1].lower()}"
        if file_ext not in self.allowed_input_types:
            allowed = ", ".join(self.allowed_input_types)
            return False, f"File type {file_ext} not supported. Allowed types: {allowed}"

        # Validate it's actually an image
        try:
            input_file.seek(0)
            with Image.open(input_file) as img:
                img.verify()
            input_file.seek(0)  # Reset for later processing
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"

        # Validate export format if specified
        if parameters:
            export_format = parameters.get("export_format", "").lower()
            if export_format and export_format not in ["json", "csv", ""]:
                return False, "Invalid export format. Must be 'json' or 'csv'."

        return True, None

    def _parse_gps_info(self, gps_info: Dict) -> Dict[str, Any]:
        """
        Parse GPS information from EXIF data.

        Args:
            gps_info: Raw GPS info from EXIF

        Returns:
            Formatted GPS data dictionary
        """
        gps_data = {}

        for key, val in gps_info.items():
            tag_name = GPSTAGS.get(key, key)
            gps_data[tag_name] = val

        # Convert GPS coordinates to decimal format
        if all(
            k in gps_data
            for k in ["GPSLatitude", "GPSLatitudeRef", "GPSLongitude", "GPSLongitudeRef"]
        ):
            try:
                lat = self._convert_to_degrees(gps_data["GPSLatitude"])
                if gps_data["GPSLatitudeRef"] == "S":
                    lat = -lat

                lon = self._convert_to_degrees(gps_data["GPSLongitude"])
                if gps_data["GPSLongitudeRef"] == "W":
                    lon = -lon

                gps_data["DecimalLatitude"] = lat
                gps_data["DecimalLongitude"] = lon
                gps_data["MapsURL"] = f"https://www.google.com/maps?q={lat},{lon}"
            except Exception as e:
                self.logger.warning(f"⚠️ Could not parse GPS coordinates: {str(e)}")

        return gps_data

    def _convert_to_degrees(self, value) -> float:
        """
        Convert GPS coordinates to decimal degrees.

        Args:
            value: GPS coordinate in (degrees, minutes, seconds) format

        Returns:
            Decimal degrees
        """
        d, m, s = value
        return float(d) + float(m) / 60.0 + float(s) / 3600.0

    def _format_exif_value(self, value: Any) -> str:
        """
        Format EXIF value for display.

        Args:
            value: Raw EXIF value

        Returns:
            Formatted string
        """
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8", errors="ignore")
            except (UnicodeDecodeError, AttributeError):
                return str(value)
        elif isinstance(value, (tuple, list)):
            return ", ".join(str(v) for v in value)
        else:
            return str(value)

    def process(
        self,
        input_file: Optional[UploadedFile] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], None]:
        """
        Extract EXIF metadata from image.

        Args:
            input_file: Uploaded image file
            parameters: Optional export format preference

        Returns:
            Tuple of (exif_data_dict, None) - None signals synchronous processing

        Raises:
            Exception: If extraction fails
        """
        if not input_file:
            raise Exception("No image file provided")

        if parameters is None:
            parameters = {}

        try:
            self.logger.info(f"📸 Extracting EXIF from: {input_file.name}")
            input_file.seek(0)

            # Open image and extract EXIF
            with Image.open(input_file) as img:
                # Get basic image info
                image_info = {
                    "Filename": input_file.name,
                    "Format": img.format,
                    "Mode": img.mode,
                    "Width": img.width,
                    "Height": img.height,
                    "Size": f"{img.width} x {img.height}",
                    "FileSize": f"{input_file.size / 1024:.2f} KB",
                }

                # Extract EXIF data
                exif_data = {}
                gps_data = {}

                exif = img.getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag_name = TAGS.get(tag_id, tag_id)

                        # Handle GPS info separately
                        if tag_name == "GPSInfo":
                            gps_data = self._parse_gps_info(value)
                        else:
                            exif_data[tag_name] = self._format_exif_value(value)

                    self.logger.info(f"✅ Extracted {len(exif_data)} EXIF tags")
                else:
                    self.logger.warning("⚠️ No EXIF data found in image")

            # Combine all metadata
            result = {
                "image_info": image_info,
                "exif_data": exif_data if exif_data else None,
                "gps_data": gps_data if gps_data else None,
                "has_exif": bool(exif_data),
                "has_gps": bool(gps_data),
                "total_tags": len(exif_data),
            }

            # Generate export data if requested
            export_format = parameters.get("export_format", "").lower()
            if export_format:
                result["export_data"] = self._generate_export(
                    image_info, exif_data, gps_data, export_format
                )
                result["export_format"] = export_format

            self.logger.info(f"✅ Successfully extracted metadata from {input_file.name}")

            # Save result to temp JSON file for API return
            import tempfile

            temp_fd, temp_path = tempfile.mkstemp(suffix=".json", prefix="exif_")
            os.close(temp_fd)

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # Return path to JSON file and filename
            return temp_path, "exif_data.json"

        except Exception as e:
            self.logger.error(f"❌ EXIF extraction failed: {str(e)}")
            raise Exception(f"Failed to extract EXIF data: {str(e)}")

    def _generate_export(
        self,
        image_info: Dict,
        exif_data: Dict,
        gps_data: Dict,
        format: str,
    ) -> str:
        """
        Generate export data in requested format.

        Args:
            image_info: Basic image information
            exif_data: EXIF metadata
            gps_data: GPS information
            format: Export format (json or csv)

        Returns:
            Formatted export string
        """
        if format == "json":
            export_obj = {
                "image_info": image_info,
                "exif_data": exif_data if exif_data else {},
                "gps_data": gps_data if gps_data else {},
            }
            return json.dumps(export_obj, indent=2, ensure_ascii=False)

        elif format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)

            # Write headers
            writer.writerow(["Category", "Tag", "Value"])

            # Write image info
            for key, value in image_info.items():
                writer.writerow(["Image Info", key, value])

            # Write EXIF data
            if exif_data:
                for key, value in exif_data.items():
                    writer.writerow(["EXIF", key, value])

            # Write GPS data
            if gps_data:
                for key, value in gps_data.items():
                    writer.writerow(["GPS", key, value])

            return output.getvalue()

        return ""

    def cleanup(self, *file_paths: str) -> None:
        """
        Clean up temporary files (not needed for this tool).

        Args:
            *file_paths: Paths to temporary files
        """
        # No file cleanup needed for synchronous processing
        pass
