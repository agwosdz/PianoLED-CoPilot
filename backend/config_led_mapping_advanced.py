"""
Advanced LED-to-Key Mapping: Position-Based Allocation
This module provides per-key LED allocation based on physical positioning.

Key Insight:
- Piano has 88 keys total, but width determined by 52 white keys
- LED strip is physically limited (e.g., LEDs 4-249)
- Each white key gets a proportional share of the LED range

Algorithm:
1. Calculate physical width of piano (52 white keys × 23.5mm + gaps)
2. Calculate how many LEDs span this width (given led_spacing_mm)
3. Scale factor = led_coverage_mm / piano_width_mm
4. For each white key, calculate its position in piano_width
5. Scale that position to LED space using scale_factor
6. Assign LEDs to each key based on physical position
7. Result: Each key gets 3-9 LEDs depending on position (some get fewer at edges)

Returns mapping: white_key_index → [led_indices]
Example: Key 0 → [4, 5, 6, 7, 8, 9, 10] (7 LEDs at start)
         Key 1 → [8, 9, 10, 11, 12, 13, 14, 15] (8 LEDs typical)
         Key 48 → [247, 248, 249] (3 LEDs at end, hardware-limited)
"""

from typing import Dict, List, Tuple
from backend.config import (
    count_white_keys_for_piano,
    get_piano_width_mm,
    WHITE_KEY_WIDTH_MM,
    KEY_GAP_MM
)


def calculate_per_key_led_allocation(
    leds_per_meter: int,
    start_led: int,
    end_led: int,
    piano_size: str = "88-key",
    allow_led_sharing: bool = True
) -> Dict[str, any]:
    """
    Calculate LED allocation for EACH OF 88 KEYS based on physical positioning.
    
    CRITICAL INSIGHT:
    - Piano has 88 total keys (52 white + 36 black)
    - Piano width: 1273mm (determined by 52 white keys)
    - Each key gets physical space: 1273mm / 88 keys = 14.46mm per key
    
    At 200 LEDs/m: 5mm per LED
      14.46mm per key / 5mm per LED = 2.89 LEDs per key (on average)
    
    So allocation is: Each of 88 keys gets 2-3 LEDs
    - Some keys (especially edge cases) might get 3 LEDs
    - Most keys get 2-3 LEDs
    - NOT 7-9 LEDs like with just white keys
    
    Args:
        leds_per_meter: LED density (60, 72, 100, 120, 144, 160, 180, 200)
        start_led: First LED index
        end_led: Last LED index
        piano_size: Piano size (e.g., "88-key")
    
    Returns:
        {
            "error": None or error message,
            "success": bool,
            "key_led_mapping": {
                0: [4, 5],           # Key 0 (A0) gets LEDs 4-5 (2 total)
                1: [5, 6, 7],        # Key 1 (A#0) gets LEDs 5-7 (3 total)
                2: [7, 8],           # Key 2 (B0) gets LEDs 7-8 (2 total)
                ...
            },
            "led_allocation_stats": { ... detailed stats ... }
            "warnings": [],
            "improvements": []
        }
    """
    
    result = {
        "error": None,
        "success": False,
        "key_led_mapping": {},
        "led_key_mapping": {},
        "led_allocation_stats": {},
        "warnings": [],
        "improvements": []
    }
    
    # Validate inputs
    if leds_per_meter not in [60, 72, 100, 120, 144, 160, 180, 200]:
        result["error"] = f"Invalid leds_per_meter: {leds_per_meter}"
        return result
    
    if end_led < start_led:
        result["error"] = f"end_led ({end_led}) must be >= start_led ({start_led})"
        return result
    
    # Get piano specs
    piano_width_mm = get_piano_width_mm(piano_size)
    
    # For 88-key piano, there are 88 keys total
    total_keys = 88
    
    if piano_size != "88-key":
        result["error"] = f"Only 88-key piano supported, got {piano_size}"
        return result
    
    # Physical parameters
    led_spacing_mm = 1000.0 / leds_per_meter
    physical_led_range = end_led - start_led + 1
    led_coverage_mm = (physical_led_range - 1) * led_spacing_mm if physical_led_range > 1 else 0
    
    # Calculate scale factor (how much of piano is covered by LEDs)
    scale_factor = led_coverage_mm / piano_width_mm if piano_width_mm > 0 else 0
    
    if scale_factor <= 0:
        result["error"] = "LED coverage is insufficient to map to piano"
        result["warnings"].append(f"LED coverage ({led_coverage_mm:.1f}mm) vs piano width ({piano_width_mm:.1f}mm)")
        return result
    
    # Calculate physical width per key (ALL 88 keys span the piano width)
    key_width_mm = piano_width_mm / total_keys
    
    # Map each of 88 keys to LEDs
    # Key 0 (A0) is a WHITE key, so its center starts at white_key_width / 2
    # Each subsequent key center is offset by key_width_mm
    key_led_mapping = {}
    led_key_mapping = {}
    
    # First key center position (white key A0)
    white_key_width = 23.5  # Standard white key width
    first_key_center_mm = white_key_width / 2.0
    
    # For no-sharing mode, pre-allocate all LEDs to keys based on position
    # to ensure strict partitioning (no LED shared between keys)
    if not allow_led_sharing:
        # Calculate which LEDs belong to which key by assigning each LED to exactly one key
        # based on which key's range the LED falls into
        led_to_key = {}
        
        for key_idx in range(total_keys):
            # Calculate key center and span in piano coordinates
            key_center_mm = first_key_center_mm + (key_idx * key_width_mm)
            key_start_mm = key_center_mm - (key_width_mm / 2.0)
            key_end_mm = key_center_mm + (key_width_mm / 2.0)
            
            # Convert piano position to LED coordinate space using scale_factor
            # scale_factor = led_coverage_mm / piano_width_mm (ratio of LED coverage to piano width)
            # Piano positions (0-1273mm) map to LED space using this scale
            key_start_led_pos = key_start_mm * scale_factor if scale_factor > 0 else 0
            key_end_led_pos = key_end_mm * scale_factor if scale_factor > 0 else 0
            
            # Find LED indices that fall within this key's range
            # Using floor division to find first and last LEDs
            first_led_offset = int(key_start_led_pos / led_spacing_mm) if led_spacing_mm > 0 else 0
            last_led_offset = int(key_end_led_pos / led_spacing_mm) if led_spacing_mm > 0 else 0
            
            # Assign LEDs in this range to this key (only if not already assigned)
            for led_offset in range(first_led_offset, last_led_offset + 1):
                led_idx = start_led + led_offset
                if led_idx <= end_led and led_idx not in led_to_key:
                    led_to_key[led_idx] = key_idx
        
        # Now build the key_led_mapping from the led_to_key assignment
        for led_idx, key_idx in led_to_key.items():
            if key_idx not in key_led_mapping:
                key_led_mapping[key_idx] = []
            key_led_mapping[key_idx].append(led_idx)
            
            # Build reverse mapping
            if led_idx not in led_key_mapping:
                led_key_mapping[led_idx] = []
            led_key_mapping[led_idx].append(key_idx)
        
        # Sort LEDs for each key
        for key_idx in key_led_mapping:
            key_led_mapping[key_idx] = sorted(key_led_mapping[key_idx])
    
    else:
        # Mode 1: ALLOW LED SHARING - original logic with smooth transitions
        for key_idx in range(total_keys):
            # Calculate key center and span
            key_center_mm = first_key_center_mm + (key_idx * key_width_mm)
            key_start_mm = key_center_mm - (key_width_mm / 2.0)
            key_end_mm = key_center_mm + (key_width_mm / 2.0)
            
            # Convert piano position to LED coordinate space
            key_start_led_pos = key_start_mm * scale_factor if scale_factor > 0 else 0
            key_end_led_pos = key_end_mm * scale_factor if scale_factor > 0 else 0
            
            # Convert to LED indices
            first_led = int(key_start_led_pos / led_spacing_mm) if led_spacing_mm > 0 else 0
            last_led = int(key_end_led_pos / led_spacing_mm) if led_spacing_mm > 0 else 0
            
            # Allocate LEDs for this key - include neighbors for smooth transitions
            leds_for_this_key = []
            for led_offset in range(first_led - 1, last_led + 2):
                led_idx = start_led + led_offset
                if start_led <= led_idx <= end_led:
                    leds_for_this_key.append(led_idx)
            
            if leds_for_this_key:
                key_led_mapping[key_idx] = sorted(list(set(leds_for_this_key)))
                
                # Build reverse mapping
                for led_idx in key_led_mapping[key_idx]:
                    if led_idx not in led_key_mapping:
                        led_key_mapping[led_idx] = []
                    led_key_mapping[led_idx].append(key_idx)
    
    # Calculate statistics
    leds_per_key_values = [len(leds) for leds in key_led_mapping.values()]
    
    if leds_per_key_values:
        # Separate stats for white vs black keys
        white_key_leds = []
        black_key_leds = []
        
        for key_idx, leds in key_led_mapping.items():
            note_in_octave = key_idx % 12
            is_black_key = note_in_octave in [1, 3, 6, 8, 10]
            
            if is_black_key:
                black_key_leds.append(len(leds))
            else:
                white_key_leds.append(len(leds))
        
        stats = {
            "avg_leds_per_key": sum(leds_per_key_values) / len(leds_per_key_values),
            "min_leds_per_key": min(leds_per_key_values),
            "max_leds_per_key": max(leds_per_key_values),
            "total_key_count": len(key_led_mapping),
            "total_led_count": len(led_key_mapping),
            "white_keys_mapped": len(white_key_leds),
            "black_keys_mapped": len(black_key_leds),
            "avg_leds_white_keys": sum(white_key_leds) / len(white_key_leds) if white_key_leds else 0,
            "avg_leds_black_keys": sum(black_key_leds) / len(black_key_leds) if black_key_leds else 0,
            "leds_per_key_distribution": {},
            "scale_factor": scale_factor,
            "led_coverage_mm": led_coverage_mm,
            "piano_width_mm": piano_width_mm,
            "coverage_ratio": led_coverage_mm / piano_width_mm if piano_width_mm > 0 else 0,
            "key_width_mm": key_width_mm
        }
        
        # Build distribution histogram
        for led_count in leds_per_key_values:
            stats["leds_per_key_distribution"][led_count] = \
                stats["leds_per_key_distribution"].get(led_count, 0) + 1
        
        # Identify edge keys
        if key_led_mapping:
            first_key = min(key_led_mapping.keys())
            last_key = max(key_led_mapping.keys())
            stats["edge_keys"] = {
                "first_key_index": first_key,
                "first_key_leds": len(key_led_mapping.get(first_key, [])),
                "last_key_index": last_key,
                "last_key_leds": len(key_led_mapping.get(last_key, []))
            }
        
        result["led_allocation_stats"] = stats
    else:
        result["error"] = "No LED-to-key mapping could be created"
        return result
    
    # Generate warnings
    warnings = []
    improvements = []
    
    if stats["min_leds_per_key"] < 1:
        warnings.append(f"Some keys have NO LED assigned!")
        improvements.append("Extend LED range or use denser LED strip")
    elif stats["min_leds_per_key"] < 2:
        warnings.append(f"Some keys have only 1 LED - may be insufficient")
    
    if stats["coverage_ratio"] < 0.95:
        warnings.append(f"LED range covers only {stats['coverage_ratio']*100:.1f}% of piano width")
    elif stats["coverage_ratio"] > 1.1:
        improvements.append(f"LED range exceeds piano by {(stats['coverage_ratio']-1)*100:.1f}% - could optimize")
    
    # Check for keys with no LEDs
    unassigned_keys = set(range(total_keys)) - set(key_led_mapping.keys())
    if unassigned_keys:
        warnings.append(f"{len(unassigned_keys)} of 88 keys have no LED assigned")
    
    result["error"] = None
    result["success"] = True
    result["key_led_mapping"] = key_led_mapping
    result["led_key_mapping"] = led_key_mapping
    result["warnings"] = warnings
    result["improvements"] = improvements
    result["allow_led_sharing"] = allow_led_sharing
    
    return result


def _calculate_white_key_positions(piano_size: str) -> List[Tuple[float, float]]:
    """
    Calculate the physical position (start_mm, end_mm) of each white key.
    
    CORRECTED: Piano width is determined by 52 white keys across the full range.
    Each white key gets an equal portion of the piano width, regardless of
    the traditional piano key grouping (C-E, F-B).
    
    Args:
        piano_size: Piano size (e.g., "88-key")
    
    Returns:
        List of tuples: [(key0_start, key0_end), (key1_start, key1_end), ...]
    """
    
    white_key_count = count_white_keys_for_piano(piano_size)
    piano_width_mm = get_piano_width_mm(piano_size)
    
    if white_key_count == 0 or piano_width_mm == 0:
        return []
    
    # Each white key spans equally across the entire piano width
    # This is the correct approach: piano_width / num_white_keys per key
    key_width_mm = piano_width_mm / white_key_count
    
    white_keys = []
    for key_idx in range(white_key_count):
        key_start = key_idx * key_width_mm
        key_end = (key_idx + 1) * key_width_mm
        white_keys.append((key_start, key_end))
    
    return white_keys
