"""
GPX Speed Modifier tool.

Modifies track speeds in GPX files while preserving distance and elevation data.
Recalculates timestamps based on speed multiplier.
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from django.core.files.uploadedfile import UploadedFile

from apps.core.exceptions import ToolExecutionError
from apps.tools.base import BaseTool


class GPXSpeedModifier(BaseTool):
    """
    Modify GPX track speeds by adjusting timestamps.

    Changes track speed by applying a multiplier to recalculate timestamps while preserving the geographical path.
    """

    # Tool metadata
    name = "gpx-speed-modifier"
    display_name = "GPX Speed Modifier"
    description = (
        "Modify GPS track speeds by adjusting timestamps while preserving the exact geographical path and elevation profile. "
        "Supports speed multipliers from 0.1x to 10x, perfect for training scenarios, pace simulation, and GPS timing corrections."
    )
    category = "file"
    version = "1.0.0"
    icon = "speedometer2"

    # File constraints
    allowed_input_types = [".gpx"]
    max_file_size = 50 * 1024 * 1024  # 50MB

    def validate(
        self, input_file: UploadedFile, parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate input file and parameters.

        Required parameters:
        - speed_multiplier: Float multiplier for speed (0.5 = half speed, 2.0 = double speed)
        """
        # Validate file type
        if not self.validate_file_type(input_file.name):
            return False, f"File type not supported. Allowed: {', '.join(self.allowed_input_types)}"

        # Validate file size
        if not self.validate_file_size(input_file):
            return False, f"File size exceeds maximum of {self.max_file_size / (1024*1024):.1f}MB"

        # Validate speed_multiplier
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
        Modify GPX file speed by adjusting timestamps.

        Returns:
            Tuple of (output_file_path, output_filename)
        """
        speed_multiplier = float(parameters["speed_multiplier"])
        
        temp_input = None
        temp_output = None

        try:
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=".gpx") as tmp_in:
                for chunk in input_file.chunks():
                    tmp_in.write(chunk)
                temp_input = tmp_in.name

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
                f"Successfully modified {input_file.name} with {speed_multiplier}x speed: {output_size / 1024:.1f} KB"
            )

            # Cleanup input temp file
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)

            return temp_output, output_filename

        except Exception as e:
            self.logger.error(f"GPX speed modification failed: {e}", exc_info=True)

            # Cleanup on error
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)
            if temp_output and os.path.exists(temp_output):
                os.unlink(temp_output)

            raise ToolExecutionError(f"GPX speed modification failed: {str(e)}")

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
