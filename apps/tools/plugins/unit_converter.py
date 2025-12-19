"""
Comprehensive Unit Converter Tool - 18 Categories

Supports: Length, Volume, Area, Energy, Force, Speed, Fuel Consumption,
Data Storage, Currency, Weight/Mass, Temperature, Pressure, Power, Time,
Angle, Numbers, Dry Volume, and Text Case transformations.
"""

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from django.core.files.uploadedfile import UploadedFile

from apps.tools.base import BaseTool


class UnitConverter(BaseTool):
    """Comprehensive tool for converting between 18 categories of units."""

    name = "unit-converter"
    display_name = "Unit Converter"
    description = "Convert between 160+ units across 18 categories including length, volume, area, energy, temperature, currency, and data storage. Features instant bidirectional conversion allowing you to edit either source or destination value."
    category = "conversion"
    version = "2.0.0"
    icon = "calculator"

    allowed_input_types = []
    max_file_size = 0
    requires_file_upload = False

    # Path to unit data JSON (loaded lazily)
    _data_path = Path(__file__).parent / "unit_converter_data.json"
    _UNIT_DATA = None  # Loaded on first access

    # Temperature units (special conversion logic)
    TEMPERATURE_UNITS = {
        "celsius": {"name": "Celsius"},
        "fahrenheit": {"name": "Fahrenheit"},
        "kelvin": {"name": "Kelvin"},
    }

    @classmethod
    def _load_unit_data(cls):
        """Lazily load unit data from JSON file."""
        if cls._UNIT_DATA is None:
            with open(cls._data_path, "r") as f:
                cls._UNIT_DATA = json.load(f)
        return cls._UNIT_DATA

    # Supported conversion types (for easy reference)
    SUPPORTED_TYPES = [
        "length",
        "volume",
        "area",
        "energy",
        "force",
        "speed",
        "fuel",
        "data",
        "currency",
        "weight",
        "temperature",
        "pressure",
        "power",
        "time",
        "angle",
        "numbers",
        "dry volume",
        "case",
    ]

    def get_metadata(self) -> Dict[str, Any]:
        """Return tool metadata including supported units."""
        base_metadata = super().get_metadata()

        # Extract all unit keys from the JSON data
        unit_data = self._load_unit_data()
        base_metadata.update(
            {
                "supported_conversion_types": list(unit_data.keys())
                + ["Temperature", "Fuel Consumption", "Currency", "Numbers", "Case"],
                "length_units": {
                    k: v["name"] for k, v in unit_data.get("Length", {}).get("units", {}).items()
                },
                "temperature_units": {k: v["name"] for k, v in self.TEMPERATURE_UNITS.items()},
                "volume_units": {
                    k: v["name"] for k, v in unit_data.get("Volume", {}).get("units", {}).items()
                },
                "area_units": {
                    k: v["name"] for k, v in unit_data.get("Area", {}).get("units", {}).items()
                },
                "energy_units": {
                    k: v["name"] for k, v in unit_data.get("Energy", {}).get("units", {}).items()
                },
                "requires_file_upload": False,
            }
        )
        return base_metadata

    def validate(
        self,
        input_file: Optional[UploadedFile] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate conversion parameters."""
        if parameters is None:
            return False, "No parameters provided"

        conversion_type = parameters.get("conversion_type")
        from_unit = parameters.get("from_unit")
        to_unit = parameters.get("to_unit")
        value = parameters.get("value")

        if not all([conversion_type, from_unit, to_unit, value is not None]):
            return False, "Missing required parameters: conversion_type, from_unit, to_unit, value"

        # Normalize conversion_type - allow case-insensitive exact matches
        # Build valid types list
        unit_data = self._load_unit_data()
        valid_types_exact = list(unit_data.keys()) + [
            "Temperature",
            "Fuel Consumption",
            "Currency",
            "Numbers",
            "Case",
        ]
        valid_types_lower = {t.lower(): t for t in valid_types_exact}

        conversion_type_lower = (
            conversion_type.lower()
            if isinstance(conversion_type, str)
            else str(conversion_type).lower()
        )

        # Check if it's a valid type (case-insensitive)
        if conversion_type_lower not in valid_types_lower:
            return (
                False,
                f"Unsupported conversion type: {conversion_type}. Supported types: {', '.join(self.SUPPORTED_TYPES)}",
            )

        # Get the canonical name
        conversion_type_key = valid_types_lower[conversion_type_lower]

        # Validate conversion_type exists
        if conversion_type_key not in valid_types_exact:
            return (
                False,
                f"Unsupported conversion type: {conversion_type}. Supported types: {', '.join(self.SUPPORTED_TYPES)}",
            )

        # Validate from_unit and to_unit exist for the type
        if conversion_type_key == "Temperature":
            valid_units = self.TEMPERATURE_UNITS.keys()
        elif conversion_type_key == "Fuel Consumption":
            valid_units = ["liters_per_100km", "km_per_liter", "mpg_us", "mpg_imperial"]
        elif conversion_type_key == "Currency":
            valid_units = ["usd", "eur", "gbp", "jpy", "cad", "aud", "chf", "cny", "inr"]
        elif conversion_type_key == "Numbers":
            valid_units = ["binary", "octal", "decimal", "hexadecimal"]
        elif conversion_type_key == "Case":
            valid_units = [
                "lowercase",
                "uppercase",
                "titlecase",
                "sentencecase",
                "snakecase",
                "camelcase",
                "pascalcase",
                "kebabcase",
            ]
        elif conversion_type_key in unit_data:
            valid_units = unit_data[conversion_type_key]["units"].keys()
        else:
            return False, f"Unknown conversion type: {conversion_type_key}"

        if from_unit not in valid_units:
            return (
                False,
                f"Invalid source unit: {from_unit}. Valid units for {conversion_type_key}: {', '.join(valid_units)}",
            )

        if to_unit not in valid_units:
            return (
                False,
                f"Invalid target unit: {to_unit}. Valid units for {conversion_type_key}: {', '.join(valid_units)}",
            )

        # Validate value for numeric conversions (not Case)
        if conversion_type_key != "Case":
            if conversion_type_key == "Numbers":
                # Numbers can be hex, binary, octal strings
                if not isinstance(value, (str, int, float)):
                    return False, "Value must be a string or number for number base conversion"
            else:
                try:
                    Decimal(str(value))
                except (InvalidOperation, ValueError, TypeError):
                    return False, f"Invalid numeric value: {value}"

        return True, None

    def process(
        self,
        input_file: Optional[UploadedFile] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, str]:
        """Process the unit conversion."""
        if parameters is None:
            raise ValueError("No parameters provided")

        conversion_type = parameters["conversion_type"]
        from_unit = parameters["from_unit"]
        to_unit = parameters["to_unit"]
        value = parameters["value"]

        # Normalize conversion_type
        conversion_type_normalized = (
            conversion_type.title() if isinstance(conversion_type, str) else conversion_type
        )
        type_mapping = {
            "fuel": "Fuel Consumption",
            "fuel consumption": "Fuel Consumption",
            "data": "Data Storage",
            "data storage": "Data Storage",
            "weight": "Weight and Mass",
            "mass": "Weight and Mass",
            "weight and mass": "Weight and Mass",
            "dry volume": "Volume - Dry",
            "volume - dry": "Volume - Dry",
            "numbers": "Numbers",
            "case": "Case",
        }
        conversion_type_key = type_mapping.get(conversion_type.lower(), conversion_type_normalized)

        try:
            # Route to appropriate conversion method
            if conversion_type_key == "Temperature":
                result = self._convert_temperature(value, from_unit, to_unit)
            elif conversion_type_key == "Fuel Consumption":
                result = self._convert_fuel(value, from_unit, to_unit)
            elif conversion_type_key == "Numbers":
                result = self._convert_number_base(value, from_unit, to_unit)
            elif conversion_type_key == "Case":
                result = self._convert_case(value, from_unit, to_unit)
            elif conversion_type_key == "Currency":
                result = self._convert_currency(value, from_unit, to_unit)
            elif conversion_type_key in self._load_unit_data():
                result = self._convert_standard(conversion_type_key, value, from_unit, to_unit)
            else:
                raise ValueError(f"Unsupported conversion type: {conversion_type_key}")

            # Return result in expected format
            result_dict = {
                "conversion_type": conversion_type_key,
                "input_value": (
                    float(value)
                    if conversion_type_key != "Case" and conversion_type_key != "Numbers"
                    else value
                ),
                "input_unit": from_unit,
                "output_value": (
                    float(result)
                    if conversion_type_key != "Case" and conversion_type_key != "Numbers"
                    else result
                ),
                "output_unit": to_unit,
                "formatted_result": f"{value} {from_unit} = {result} {to_unit}",
            }

            result_string = f"{value} {from_unit} = {result} {to_unit}"
            return result_dict, result_string

        except Exception as e:
            error_dict = {
                "status": "error",
                "message": f"Conversion failed: {str(e)}",
            }
            return error_dict, f"error: {str(e)}"

    def _convert_standard(self, category: str, value: str, from_unit: str, to_unit: str) -> Decimal:
        """Convert using standard factor-based conversion."""
        unit_data = self._load_unit_data()
        units = unit_data[category]["units"]

        if from_unit not in units:
            raise ValueError(f"Unknown source unit: {from_unit}")
        if to_unit not in units:
            raise ValueError(f"Unknown target unit: {to_unit}")

        # Convert to base unit, then to target unit
        value_decimal = Decimal(str(value))
        from_factor = Decimal(units[from_unit]["factor"])
        to_factor = Decimal(units[to_unit]["factor"])

        base_value = value_decimal * from_factor
        result = base_value / to_factor

        return result

    def _convert_temperature(self, value: str, from_unit: str, to_unit: str) -> Decimal:
        """Convert temperature with special formulas."""
        value_decimal = Decimal(str(value))

        # Convert to Celsius first
        if from_unit == "celsius":
            celsius = value_decimal
        elif from_unit == "fahrenheit":
            celsius = (value_decimal - Decimal("32")) * Decimal("5") / Decimal("9")
        elif from_unit == "kelvin":
            celsius = value_decimal - Decimal("273.15")
        else:
            raise ValueError(f"Unknown temperature unit: {from_unit}")

        # Convert from Celsius to target
        if to_unit == "celsius":
            result = celsius
        elif to_unit == "fahrenheit":
            result = celsius * Decimal("9") / Decimal("5") + Decimal("32")
        elif to_unit == "kelvin":
            result = celsius + Decimal("273.15")
        else:
            raise ValueError(f"Unknown temperature unit: {to_unit}")

        return result

    def _convert_fuel(self, value: str, from_unit: str, to_unit: str) -> Decimal:
        """
        Convert fuel consumption (inverse relationship).
        L/100km <-> km/L, mpg_us, mpg_imperial
        """
        value_decimal = Decimal(str(value))

        # Convert to L/100km as base
        if from_unit == "liters_per_100km":
            base_l_100km = value_decimal
        elif from_unit == "km_per_liter":
            base_l_100km = Decimal("100") / value_decimal
        elif from_unit == "mpg_us":
            # mpg_us to L/100km: 235.214583 / mpg
            base_l_100km = Decimal("235.214583") / value_decimal
        elif from_unit == "mpg_imperial":
            # mpg_imperial to L/100km: 282.481 / mpg
            base_l_100km = Decimal("282.48093627967") / value_decimal
        else:
            raise ValueError(f"Unknown fuel unit: {from_unit}")

        # Convert from L/100km to target
        if to_unit == "liters_per_100km":
            result = base_l_100km
        elif to_unit == "km_per_liter":
            result = Decimal("100") / base_l_100km
        elif to_unit == "mpg_us":
            result = Decimal("235.214583") / base_l_100km
        elif to_unit == "mpg_imperial":
            result = Decimal("282.48093627967") / base_l_100km
        else:
            raise ValueError(f"Unknown fuel unit: {to_unit}")

        return result

    def _convert_number_base(self, value: str, from_base: str, to_base: str) -> str:
        """Convert between number bases (binary, octal, decimal, hexadecimal)."""
        bases = {
            "binary": 2,
            "octal": 8,
            "decimal": 10,
            "hexadecimal": 16,
        }

        if from_base not in bases:
            raise ValueError(f"Unknown source base: {from_base}")
        if to_base not in bases:
            raise ValueError(f"Unknown target base: {to_base}")

        # Convert to decimal integer first
        try:
            decimal_value = int(str(value), bases[from_base])
        except ValueError:
            raise ValueError(f"Invalid {from_base} value: {value}")

        # Convert to target base
        if to_base == "binary":
            result = bin(decimal_value)[2:]  # Remove '0b' prefix
        elif to_base == "octal":
            result = oct(decimal_value)[2:]  # Remove '0o' prefix
        elif to_base == "decimal":
            result = str(decimal_value)
        elif to_base == "hexadecimal":
            result = hex(decimal_value)[2:].upper()  # Remove '0x' prefix, uppercase
        else:
            result = str(decimal_value)

        return result

    def _convert_case(self, value: str, from_case: str, to_case: str) -> str:
        """Convert text between different case formats."""
        text = str(value)

        # First, handle from_case if needed (currently just use raw text)
        # In practice, from_case is informational - we convert the input text to to_case

        if to_case == "lowercase":
            result = text.lower()
        elif to_case == "uppercase":
            result = text.upper()
        elif to_case == "titlecase":
            result = text.title()
        elif to_case == "sentencecase":
            result = text.capitalize()
        elif to_case == "snakecase":
            # Convert to snake_case
            result = re.sub(r"[\s\-]+", "_", text)
            result = re.sub(r"([a-z])([A-Z])", r"\1_\2", result)
            result = result.lower()
        elif to_case == "camelcase":
            # Convert to camelCase
            words = re.split(r"[\s_\-]+", text)
            result = words[0].lower() + "".join(word.capitalize() for word in words[1:])
        elif to_case == "pascalcase":
            # Convert to PascalCase
            words = re.split(r"[\s_\-]+", text)
            result = "".join(word.capitalize() for word in words)
        elif to_case == "kebabcase":
            # Convert to kebab-case
            result = re.sub(r"[\s_]+", "-", text)
            result = re.sub(r"([a-z])([A-Z])", r"\1-\2", result)
            result = result.lower()
        else:
            raise ValueError(f"Unknown case type: {to_case}")

        return result

    def _convert_currency(self, value: str, from_curr: str, to_curr: str) -> Decimal:
        """
        Convert currency using static exchange rates.
        Note: In production, this should use a live API.
        """
        # Static rates relative to USD
        rates = {
            "usd": Decimal("1"),
            "eur": Decimal("0.92"),
            "gbp": Decimal("0.79"),
            "jpy": Decimal("149.50"),
            "cad": Decimal("1.36"),
            "aud": Decimal("1.53"),
            "chf": Decimal("0.88"),
            "cny": Decimal("7.24"),
            "inr": Decimal("83.12"),
        }

        if from_curr not in rates:
            raise ValueError(f"Unknown currency: {from_curr}")
        if to_curr not in rates:
            raise ValueError(f"Unknown currency: {to_curr}")

        value_decimal = Decimal(str(value))

        # Convert to USD, then to target currency
        usd_value = value_decimal / rates[from_curr]
        result = usd_value * rates[to_curr]

        return result

    def cleanup(self, *file_paths: str) -> None:
        """No cleanup needed for this tool (no temporary files created)."""
        pass
