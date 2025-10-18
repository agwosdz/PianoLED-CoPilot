#!/usr/bin/env python3
"""
Unit conversion utilities for LED strip offset management.

Handles conversion between physical measurements (mm) and LED indices,
accounting for configurable LED density (LEDs per meter).

Formula:
  - LED density = LEDs per meter (e.g., 200 LEDs/m for WS2812B)
  - Physical spacing = 1000mm / LED density
  - offset_leds = offset_mm / physical_spacing_mm
  - offset_mm = offset_leds * physical_spacing_mm
"""

import logging
from typing import Dict, Any, Optional, Tuple
from backend.logging_config import get_logger

logger = get_logger(__name__)

# Standard LED strip densities
STANDARD_LED_DENSITIES = {
    60: "Standard 60 LEDs/m (16.67mm spacing)",
    120: "Standard 120 LEDs/m (8.33mm spacing)",
    144: "Standard 144 LEDs/m (6.94mm spacing)",
    180: "Standard 180 LEDs/m (5.56mm spacing)",
    200: "Standard 200 LEDs/m (5.0mm spacing) - Default WS2812B",
    240: "Standard 240 LEDs/m (4.17mm spacing)",
    288: "Standard 288 LEDs/m (3.47mm spacing)",
    300: "Standard 300 LEDs/m (3.33mm spacing)",
    330: "Standard 330 LEDs/m (3.03mm spacing)",
}


def get_physical_spacing_mm(leds_per_meter: int) -> float:
    """
    Calculate physical spacing in mm between LED centers.
    
    Args:
        leds_per_meter: LED density (e.g., 200 for WS2812B)
    
    Returns:
        float: Physical spacing in mm between LED centers
        
    Example:
        >>> get_physical_spacing_mm(200)
        5.0
        >>> get_physical_spacing_mm(60)
        16.666...
    """
    if not isinstance(leds_per_meter, (int, float)) or leds_per_meter <= 0:
        logger.warning(f"Invalid leds_per_meter: {leds_per_meter}, using default 200")
        leds_per_meter = 200
    
    spacing = 1000.0 / leds_per_meter
    logger.debug(f"Physical spacing: {spacing:.2f}mm per LED at {leds_per_meter} LEDs/m")
    return spacing


def mm_to_leds(offset_mm: float, leds_per_meter: int) -> int:
    """
    Convert offset in millimeters to LED index offset.
    
    Args:
        offset_mm: Offset in millimeters (positive or negative)
        leds_per_meter: LED density configuration
    
    Returns:
        int: Offset in LED units (rounded to nearest integer)
        
    Example:
        >>> mm_to_leds(5.0, 200)  # 5mm at 200 LEDs/m = 1 LED
        1
        >>> mm_to_leds(3.5, 200)  # 3.5mm at 200 LEDs/m = 0.7 LEDs ≈ 1 LED
        1
        >>> mm_to_leds(3.5, 60)   # 3.5mm at 60 LEDs/m = 0.21 LEDs ≈ 0 LEDs
        0
    """
    spacing = get_physical_spacing_mm(leds_per_meter)
    offset_leds = offset_mm / spacing
    result = round(offset_leds)
    
    logger.debug(f"Converted {offset_mm}mm to {result} LEDs (spacing: {spacing:.2f}mm/LED)")
    return result


def leds_to_mm(offset_leds: int, leds_per_meter: int) -> float:
    """
    Convert offset in LED units to millimeters.
    
    Args:
        offset_leds: Offset in LED units
        leds_per_meter: LED density configuration
    
    Returns:
        float: Offset in millimeters
        
    Example:
        >>> leds_to_mm(1, 200)     # 1 LED at 200 LEDs/m = 5.0mm
        5.0
        >>> leds_to_mm(2, 60)      # 2 LEDs at 60 LEDs/m = 33.33mm
        33.333...
    """
    spacing = get_physical_spacing_mm(leds_per_meter)
    offset_mm = offset_leds * spacing
    
    logger.debug(f"Converted {offset_leds} LEDs to {offset_mm:.2f}mm (spacing: {spacing:.2f}mm/LED)")
    return offset_mm


def normalize_offset(
    value: float,
    from_unit: str = "mm",
    to_unit: str = "led",
    leds_per_meter: int = 200
) -> Dict[str, Any]:
    """
    Normalize offset between units with detailed information.
    
    Args:
        value: Offset value
        from_unit: Source unit ("mm" or "led")
        to_unit: Target unit ("mm" or "led")
        leds_per_meter: LED density configuration
    
    Returns:
        dict: {
            'value_mm': float,
            'value_led': int,
            'spacing_mm': float,
            'leds_per_meter': int,
            'source_unit': str,
            'target_unit': str,
            'conversion_factor': float,
            'description': str
        }
        
    Example:
        >>> normalize_offset(3.5, from_unit="mm", to_unit="led", leds_per_meter=200)
        {
            'value_mm': 3.5,
            'value_led': 1,
            'spacing_mm': 5.0,
            ...
        }
    """
    try:
        value = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid offset value: {value}")
    
    from_unit = from_unit.lower().strip()
    to_unit = to_unit.lower().strip()
    
    if from_unit not in ("mm", "led"):
        raise ValueError(f"Invalid from_unit: {from_unit}, must be 'mm' or 'led'")
    if to_unit not in ("mm", "led"):
        raise ValueError(f"Invalid to_unit: {to_unit}, must be 'mm' or 'led'")
    
    spacing = get_physical_spacing_mm(leds_per_meter)
    
    # Convert to both units
    if from_unit == "mm":
        value_mm = value
        value_led = round(value_mm / spacing)
    else:  # from_unit == "led"
        value_led = int(value)
        value_mm = value_led * spacing
    
    # Calculate conversion factor for this specific conversion
    if to_unit == from_unit:
        conversion_factor = 1.0
    elif to_unit == "led":
        conversion_factor = 1.0 / spacing  # mm to led ratio
    else:  # to_unit == "mm"
        conversion_factor = spacing  # led to mm ratio
    
    description = (
        f"{value} {from_unit} = {value_mm:.2f}mm = {value_led} LEDs "
        f"(at {leds_per_meter} LEDs/m, {spacing:.2f}mm spacing)"
    )
    
    return {
        'value_mm': round(value_mm, 2),
        'value_led': value_led,
        'spacing_mm': round(spacing, 2),
        'leds_per_meter': leds_per_meter,
        'source_unit': from_unit,
        'target_unit': to_unit,
        'conversion_factor': round(conversion_factor, 4),
        'description': description
    }


def validate_offset(
    offset_value: float,
    offset_unit: str = "mm",
    leds_per_meter: int = 200,
    max_offset_mm: float = 50.0,
    max_offset_led: int = 15
) -> Tuple[bool, Optional[str]]:
    """
    Validate offset is within acceptable range.
    
    Args:
        offset_value: Offset value
        offset_unit: Unit ("mm" or "led")
        leds_per_meter: LED density
        max_offset_mm: Maximum allowed offset in mm
        max_offset_led: Maximum allowed offset in LEDs
    
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    try:
        offset_value = float(offset_value)
    except (ValueError, TypeError):
        return False, f"Invalid offset value: {offset_value}"
    
    offset_unit = offset_unit.lower().strip()
    
    if offset_unit == "mm":
        if abs(offset_value) > max_offset_mm:
            return False, (
                f"Offset {offset_value}mm exceeds maximum {max_offset_mm}mm. "
                f"This is likely too large for a solder joint."
            )
    elif offset_unit == "led":
        if abs(offset_value) > max_offset_led:
            return False, (
                f"Offset {offset_value} LEDs exceeds maximum {max_offset_led}. "
                f"Consider using mm units for better precision."
            )
    else:
        return False, f"Invalid offset_unit: {offset_unit}"
    
    return True, None


def get_joint_width_in_leds(width_mm: float, leds_per_meter: int) -> int:
    """
    Convert physical joint width to LED count for UI/visualization.
    
    Args:
        width_mm: Physical width of solder joint in mm
        leds_per_meter: LED density
    
    Returns:
        int: Number of LEDs the joint spans (minimum 1)
    """
    spacing = get_physical_spacing_mm(leds_per_meter)
    width_leds = round(width_mm / spacing)
    return max(1, width_leds)  # At minimum, occupies 1 LED


def get_joint_statistics(
    joints: Dict[int, Dict[str, Any]],
    leds_per_meter: int = 200
) -> Dict[str, Any]:
    """
    Calculate statistics for a set of soldering joints.
    
    Args:
        joints: Joint dict {led_index: {width_mm, offset_mm, ...}}
        leds_per_meter: LED density
    
    Returns:
        dict: Statistics including min/max/average offsets, total width, etc.
    """
    if not joints:
        return {
            'joint_count': 0,
            'total_width_mm': 0.0,
            'total_width_leds': 0,
            'average_offset_mm': 0.0,
            'average_offset_leds': 0,
            'min_offset_mm': 0.0,
            'max_offset_mm': 0.0,
            'min_offset_leds': 0,
            'max_offset_leds': 0,
            'led_indices': []
        }
    
    offsets_mm = [j.get('offset_mm', 0) for j in joints.values()]
    widths_mm = [j.get('width_mm', 0) for j in joints.values()]
    
    offsets_leds = [mm_to_leds(o, leds_per_meter) for o in offsets_mm]
    widths_leds = [get_joint_width_in_leds(w, leds_per_meter) for w in widths_mm]
    
    return {
        'joint_count': len(joints),
        'total_width_mm': round(sum(widths_mm), 2),
        'total_width_leds': sum(widths_leds),
        'average_offset_mm': round(sum(offsets_mm) / len(offsets_mm), 2) if offsets_mm else 0,
        'average_offset_leds': round(sum(offsets_leds) / len(offsets_leds)) if offsets_leds else 0,
        'min_offset_mm': round(min(offsets_mm), 2) if offsets_mm else 0,
        'max_offset_mm': round(max(offsets_mm), 2) if offsets_mm else 0,
        'min_offset_leds': min(offsets_leds) if offsets_leds else 0,
        'max_offset_leds': max(offsets_leds) if offsets_leds else 0,
        'led_indices': sorted(joints.keys())
    }


# Module-level docstring for reference
__doc__ = """
Soldering Joint Unit Conversion Utilities

This module provides functions to convert between physical measurements (mm) and
LED indices for LED strip soldering joints. All conversions are dynamic based on
the configured LED density (LEDs per meter).

Key Functions:
- mm_to_leds(): Convert millimeters to LED offset
- leds_to_mm(): Convert LED offset to millimeters
- normalize_offset(): Convert between units with full details
- validate_offset(): Check offset is within acceptable range
- get_physical_spacing_mm(): Get spacing for given density
- get_joint_statistics(): Calculate joint statistics

Usage Example:
    from backend.utils.soldering_joint_converter import mm_to_leds, normalize_offset
    
    # Convert 3.5mm offset to LEDs (at 200 LEDs/m)
    offset_leds = mm_to_leds(3.5, 200)  # Returns: 1
    
    # Get full conversion info
    info = normalize_offset(3.5, from_unit="mm", to_unit="led", leds_per_meter=200)
    print(info)  # Shows both units, spacing, conversion factor, etc.
"""
