"""
Unit Converter Tool

Converts between various units of measurement including:
- Length: Meter, Kilometer, Centimeter, Millimeter, Micrometer, Nanometer, Mile, Yard, Foot, Inch, Light Year
- Temperature: Celsius, Kelvin, Fahrenheit
- Volume: Metric, Imperial/US, Specialized, Scientific, and Practical units
- Area: Metric, Imperial/US, Scientific, and Specialized units
- Energy: SI, Electrical, Thermal, Mechanical, Fuel, and Scientific units
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple

from django.core.files.uploadedfile import UploadedFile

from apps.tools.base import BaseTool


class UnitConverter(BaseTool):
    """
    Tool for converting between different units of measurement.
    
    Supports:
    - Length conversions (11 units)
    - Temperature conversions (3 units)
    - Volume conversions (52 units)
    - Area conversions (22 units)
    - Energy conversions (35 units)
    
    This tool does NOT require file upload - it works with direct input values.
    """

    name = "unit-converter"
    display_name = "Unit Converter"
    description = "Convert between various units of length, temperature, volume, area, and energy"
    category = "conversion"
    version = "1.0.0"
    icon = "calculator"
    
    # This tool doesn't require file upload
    allowed_input_types = []
    max_file_size = 0
    requires_file_upload = False

    # Length conversion factors to meters (base unit)
    LENGTH_UNITS = {
        "meter": Decimal("1"),
        "kilometer": Decimal("1000"),
        "centimeter": Decimal("0.01"),
        "millimeter": Decimal("0.001"),
        "micrometer": Decimal("0.000001"),
        "nanometer": Decimal("0.000000001"),
        "mile": Decimal("1609.344"),
        "yard": Decimal("0.9144"),
        "foot": Decimal("0.3048"),
        "inch": Decimal("0.0254"),
        "light_year": Decimal("9460730472580800"),  # meters in a light year
    }

    # Temperature units
    TEMPERATURE_UNITS = ["celsius", "kelvin", "fahrenheit"]

    # Volume conversion factors to cubic meters (base unit)
    VOLUME_UNITS = {
        # Metric Units
        "cubic_meter": Decimal("1"),
        "cubic_centimeter": Decimal("0.000001"),
        "cubic_millimeter": Decimal("0.000000001"),
        "liter": Decimal("0.001"),
        "milliliter": Decimal("0.000001"),
        "microliter": Decimal("0.000000001"),
        "cubic_decimeter": Decimal("0.001"),
        "deciliter": Decimal("0.0001"),
        "centiliter": Decimal("0.00001"),
        "hectoliter": Decimal("0.1"),
        # Imperial / US Units
        "cubic_inch": Decimal("0.000016387064"),
        "cubic_foot": Decimal("0.028316846592"),
        "cubic_yard": Decimal("0.764554857984"),
        "gallon_us": Decimal("0.003785411784"),
        "gallon_uk": Decimal("0.00454609"),
        "quart_us": Decimal("0.000946352946"),
        "quart_uk": Decimal("0.0011365225"),
        "pint_us": Decimal("0.000473176473"),
        "pint_uk": Decimal("0.00056826125"),
        "cup_us": Decimal("0.0002365882365"),
        "cup_uk": Decimal("0.0002841306"),
        "fluid_ounce_us": Decimal("0.0000295735295625"),
        "fluid_ounce_uk": Decimal("0.0000284130625"),
        "tablespoon_us": Decimal("0.00001478676478125"),
        "tablespoon_uk": Decimal("0.00001420653125"),
        "teaspoon_us": Decimal("0.00000492892159375"),
        "teaspoon_uk": Decimal("0.00000473551041667"),
        # Specialized Units
        "barrel_oil": Decimal("0.158987294928"),
        "barrel_beer": Decimal("0.117347765304"),
        "bushel": Decimal("0.03523907016688"),
        "peck": Decimal("0.00880976754172"),
        "cord": Decimal("3.624556363776"),
        "board_foot": Decimal("0.002359737216"),
        # Scientific Units
        "cubic_kilometer": Decimal("1000000000"),
        "cubic_micrometer": Decimal("0.000000000000000001"),
        "cubic_nanometer": Decimal("0.000000000000000000000000001"),
        "cubic_angstrom": Decimal("0.000000000000000000000000000001"),
        # Other Practical Units
        "acre_foot": Decimal("1233.48183754752"),
        "register_ton": Decimal("2.8316846592"),
        "freight_ton": Decimal("1.13267386368"),
        "dry_gallon": Decimal("0.00440488377086"),
        "dry_quart": Decimal("0.001101220942715"),
        "dry_pint": Decimal("0.0005506104713575"),
        "dry_cup": Decimal("0.00027530523567875"),
        "dry_tablespoon": Decimal("0.000017206577229921875"),
        "dry_teaspoon": Decimal("0.000005735525743307291667"),
        "drop": Decimal("0.00000005"),
        "shot": Decimal("0.0000443602943"),
        "jigger": Decimal("0.0000443602943"),
    }

    # Area conversion factors to square meters (base unit)
    AREA_UNITS = {
        # Metric Units
        "square_millimeter": Decimal("0.000001"),
        "square_centimeter": Decimal("0.0001"),
        "square_decimeter": Decimal("0.01"),
        "square_meter": Decimal("1"),
        "square_kilometer": Decimal("1000000"),
        "hectare": Decimal("10000"),
        # Imperial / US Units
        "square_inch": Decimal("0.00064516"),
        "square_foot": Decimal("0.09290304"),
        "square_yard": Decimal("0.83612736"),
        "square_mile": Decimal("2589988.110336"),
        "acre": Decimal("4046.8564224"),
        "rood": Decimal("1011.7141056"),
        # Other Practical Units
        "are": Decimal("100"),
        "barn": Decimal("0.0000000000000000000000000001"),
        "board_foot": Decimal("0.002359737216"),
        # Specialized / Rare Units
        "square_rod": Decimal("25.29285264"),
        "square_chain": Decimal("404.68564224"),
        "square_furlong": Decimal("40468.564224"),
        "square_nautical_mile": Decimal("3429904"),
        # Scientific Units
        "square_micrometer": Decimal("0.000000000001"),
        "square_nanometer": Decimal("0.000000000000000001"),
        "square_angstrom": Decimal("0.00000000000000000001"),
    }

    # Energy conversion factors to joules (base unit)
    ENERGY_UNITS = {
        # SI Units
        "joule": Decimal("1"),
        "kilojoule": Decimal("1000"),
        "megajoule": Decimal("1000000"),
        "gigajoule": Decimal("1000000000"),
        # Electrical / Power-Related
        "watt_hour": Decimal("3600"),
        "kilowatt_hour": Decimal("3600000"),
        "megawatt_hour": Decimal("3600000000"),
        "gigawatt_hour": Decimal("3600000000000"),
        # Heat / Thermal
        "calorie": Decimal("4.184"),
        "kilocalorie": Decimal("4184"),
        "btu": Decimal("1055.05585262"),
        "therm": Decimal("105505585.262"),
        # Mechanical / Work
        "erg": Decimal("0.0000001"),
        "foot_pound": Decimal("1.3558179483314004"),
        "inch_pound": Decimal("0.1129848290276167"),
        # Fuel / Combustion
        "barrel_oil_equivalent": Decimal("6117863200"),
        "ton_oil_equivalent": Decimal("41868000000"),
        "cubic_meter_natural_gas": Decimal("38000000"),
        # Scientific / Specialized
        "electronvolt": Decimal("0.00000000000000000016021766208"),
        "kiloelectronvolt": Decimal("0.00000000000000016021766208"),
        "megaelectronvolt": Decimal("0.00000000000016021766208"),
        "gigaelectronvolt": Decimal("0.00000000016021766208"),
        "hartree": Decimal("0.0000000000000000043597447222071"),
        "rydberg": Decimal("0.00000000000000000217987236110356"),
        "thermochemical_calorie": Decimal("4.184"),
        # Other Practical Units
        "horsepower_hour": Decimal("2684519.537696172792"),
        "quad": Decimal("1055055852620000"),
        "thermie": Decimal("4185800"),
        "kilogram_force_meter": Decimal("9.80665"),
        "newton_meter": Decimal("1"),
    }

    # Supported conversion types
    SUPPORTED_TYPES = ["length", "temperature", "volume", "area", "energy"]

    def get_metadata(self) -> Dict[str, Any]:
        """Return tool metadata including supported units."""
        base_metadata = super().get_metadata()
        base_metadata.update({
            "supported_conversion_types": self.SUPPORTED_TYPES,
            "length_units": list(self.LENGTH_UNITS.keys()),
            "temperature_units": self.TEMPERATURE_UNITS,
            "volume_units": list(self.VOLUME_UNITS.keys()),
            "area_units": list(self.AREA_UNITS.keys()),
            "energy_units": list(self.ENERGY_UNITS.keys()),
            "requires_file_upload": False,
        })
        return base_metadata

    def validate(
        self, input_file: Optional[UploadedFile] = None, parameters: Dict[str, Any] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate conversion parameters.

        Args:
            input_file: Not used for this tool (always None)
            parameters: Must include conversion_type, value, from_unit, to_unit

        Returns:
            Tuple of (is_valid, error_message)
        """
        if parameters is None:
            return False, "No parameters provided"
        
        # Check required parameters
        required_params = ["conversion_type", "value", "from_unit", "to_unit"]
        missing_params = [p for p in required_params if p not in parameters]
        if missing_params:
            return False, f"Missing required parameters: {', '.join(missing_params)}"

        conversion_type = parameters["conversion_type"].lower()
        from_unit = parameters["from_unit"].lower()
        to_unit = parameters["to_unit"].lower()
        value = parameters["value"]

        # Validate conversion type
        if conversion_type not in self.SUPPORTED_TYPES:
            return False, f"Unsupported conversion type: {conversion_type}. Supported types: {', '.join(self.SUPPORTED_TYPES)}"

        # Validate value
        try:
            Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return False, f"Invalid numeric value: {value}"

        # Validate units based on conversion type
        if conversion_type == "length":
            if from_unit not in self.LENGTH_UNITS:
                return False, f"Invalid source unit: {from_unit}. Supported units: {', '.join(self.LENGTH_UNITS.keys())}"
            if to_unit not in self.LENGTH_UNITS:
                return False, f"Invalid target unit: {to_unit}. Supported units: {', '.join(self.LENGTH_UNITS.keys())}"
        elif conversion_type == "temperature":
            if from_unit not in self.TEMPERATURE_UNITS:
                return False, f"Invalid source unit: {from_unit}. Supported units: {', '.join(self.TEMPERATURE_UNITS)}"
            if to_unit not in self.TEMPERATURE_UNITS:
                return False, f"Invalid target unit: {to_unit}. Supported units: {', '.join(self.TEMPERATURE_UNITS)}"
        elif conversion_type == "volume":
            if from_unit not in self.VOLUME_UNITS:
                return False, f"Invalid source unit: {from_unit}. Supported units: {', '.join(self.VOLUME_UNITS.keys())}"
            if to_unit not in self.VOLUME_UNITS:
                return False, f"Invalid target unit: {to_unit}. Supported units: {', '.join(self.VOLUME_UNITS.keys())}"
        elif conversion_type == "area":
            if from_unit not in self.AREA_UNITS:
                return False, f"Invalid source unit: {from_unit}. Supported units: {', '.join(self.AREA_UNITS.keys())}"
            if to_unit not in self.AREA_UNITS:
                return False, f"Invalid target unit: {to_unit}. Supported units: {', '.join(self.AREA_UNITS.keys())}"
        elif conversion_type == "energy":
            if from_unit not in self.ENERGY_UNITS:
                return False, f"Invalid source unit: {from_unit}. Supported units: {', '.join(self.ENERGY_UNITS.keys())}"
            if to_unit not in self.ENERGY_UNITS:
                return False, f"Invalid target unit: {to_unit}. Supported units: {', '.join(self.ENERGY_UNITS.keys())}"

        return True, None

    def convert_length(self, value: Decimal, from_unit: str, to_unit: str) -> Decimal:
        """
        Convert length between units.

        Args:
            value: Numeric value to convert
            from_unit: Source unit
            to_unit: Target unit

        Returns:
            Converted value
        """
        # Convert to meters first (base unit)
        value_in_meters = value * self.LENGTH_UNITS[from_unit]
        
        # Convert from meters to target unit
        result = value_in_meters / self.LENGTH_UNITS[to_unit]
        
        return result

    def convert_temperature(self, value: Decimal, from_unit: str, to_unit: str) -> Decimal:
        """
        Convert temperature between units.

        Args:
            value: Numeric value to convert
            from_unit: Source unit
            to_unit: Target unit

        Returns:
            Converted value
        """
        # Convert to celsius first (base unit)
        if from_unit == "celsius":
            value_in_celsius = value
        elif from_unit == "kelvin":
            value_in_celsius = value - Decimal("273.15")
        elif from_unit == "fahrenheit":
            value_in_celsius = (value - Decimal("32")) * Decimal("5") / Decimal("9")
        else:
            raise ValueError(f"Unsupported temperature unit: {from_unit}")
        
        # Convert from celsius to target unit
        if to_unit == "celsius":
            result = value_in_celsius
        elif to_unit == "kelvin":
            result = value_in_celsius + Decimal("273.15")
        elif to_unit == "fahrenheit":
            result = value_in_celsius * Decimal("9") / Decimal("5") + Decimal("32")
        else:
            raise ValueError(f"Unsupported temperature unit: {to_unit}")
        
        return result

    def convert_volume(self, value: Decimal, from_unit: str, to_unit: str) -> Decimal:
        """
        Convert volume between units.

        Args:
            value: Numeric value to convert
            from_unit: Source unit
            to_unit: Target unit

        Returns:
            Converted value
        """
        # Convert to cubic meters first (base unit)
        value_in_cubic_meters = value * self.VOLUME_UNITS[from_unit]
        
        # Convert from cubic meters to target unit
        result = value_in_cubic_meters / self.VOLUME_UNITS[to_unit]
        
        return result

    def convert_area(self, value: Decimal, from_unit: str, to_unit: str) -> Decimal:
        """
        Convert area between units.

        Args:
            value: Numeric value to convert
            from_unit: Source unit
            to_unit: Target unit

        Returns:
            Converted value
        """
        # Convert to square meters first (base unit)
        value_in_square_meters = value * self.AREA_UNITS[from_unit]
        
        # Convert from square meters to target unit
        result = value_in_square_meters / self.AREA_UNITS[to_unit]
        
        return result

    def convert_energy(self, value: Decimal, from_unit: str, to_unit: str) -> Decimal:
        """
        Convert energy between units.

        Args:
            value: Numeric value to convert
            from_unit: Source unit
            to_unit: Target unit

        Returns:
            Converted value
        """
        # Convert to joules first (base unit)
        value_in_joules = value * self.ENERGY_UNITS[from_unit]
        
        # Convert from joules to target unit
        result = value_in_joules / self.ENERGY_UNITS[to_unit]
        
        return result

    def process(
        self, input_file: Optional[UploadedFile] = None, parameters: Dict[str, Any] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Execute conversion.

        Args:
            input_file: Not used for this tool
            parameters: Must include conversion_type, value, from_unit, to_unit

        Returns:
            Tuple of (result_dict, result_string)
        """
        conversion_type = parameters["conversion_type"].lower()
        value = Decimal(str(parameters["value"]))
        from_unit = parameters["from_unit"].lower()
        to_unit = parameters["to_unit"].lower()

        # Perform conversion
        if conversion_type == "length":
            result = self.convert_length(value, from_unit, to_unit)
        elif conversion_type == "temperature":
            result = self.convert_temperature(value, from_unit, to_unit)
        elif conversion_type == "volume":
            result = self.convert_volume(value, from_unit, to_unit)
        elif conversion_type == "area":
            result = self.convert_area(value, from_unit, to_unit)
        elif conversion_type == "energy":
            result = self.convert_energy(value, from_unit, to_unit)
        else:
            raise ValueError(f"Unsupported conversion type: {conversion_type}")

        # Format result
        result_dict = {
            "conversion_type": conversion_type,
            "input_value": float(value),
            "input_unit": from_unit,
            "output_value": float(result),
            "output_unit": to_unit,
            "formatted_result": f"{value} {from_unit} = {result} {to_unit}",
        }

        result_string = f"{value} {from_unit} = {result:.10f} {to_unit}"

        return result_dict, result_string

    def cleanup(self, *file_paths: str) -> None:
        """
        Clean up temporary files (not needed for this tool).

        Args:
            *file_paths: Paths to temporary files to remove
        """
        # No cleanup needed for unit converter
        pass
