"""
LED Pitch Auto-Calibration

Simple automatic pitch adjustment when actual LED coverage doesn't match
theoretical calculations. Integrated into the mapping process.
"""

from typing import Dict, Tuple


def auto_calibrate_pitch(
    theoretical_pitch_mm: float,
    piano_start_mm: float,
    piano_end_mm: float,
    start_led: int,
    actual_end_led: int,
) -> Tuple[float, bool, Dict]:
    """
    Auto-calibrate LED pitch based on actual end LED provided.
    
    Calculates what pitch would be needed to reach the actual_end_led
    given the piano dimensions. If different from theoretical, adjusts automatically.
    
    Args:
        theoretical_pitch_mm: Nominal pitch (e.g., 5.0 mm from 200 LEDs/meter)
        piano_start_mm: Start of piano in physical space (always 0)
        piano_end_mm: End of piano in physical space (e.g., 1273 mm for full piano)
        start_led: First LED index (e.g., 4)
        actual_end_led: Last LED index provided (e.g., 250)
    
    Returns:
        Tuple of:
        - calibrated_pitch_mm: Pitch to use (same as input if no adjustment needed)
        - was_adjusted: Boolean indicating if pitch was changed
        - adjustment_info: Dict with details about the adjustment
    """
    
    piano_width_mm = piano_end_mm - piano_start_mm
    total_leds_in_range = (actual_end_led - start_led) + 1
    
    # Theoretical: how many mm per LED at this pitch?
    # At 5mm pitch, 247 LEDs would span: (247-1) * 5 = 1230 mm
    theoretical_span_mm = (total_leds_in_range - 1) * theoretical_pitch_mm
    
    # Actual: what pitch is needed to span piano_width with this many LEDs?
    # If piano is 1235mm and we have 247 LEDs: pitch = 1235 / 246 = 5.02mm
    if total_leds_in_range > 1:
        required_pitch_mm = piano_width_mm / (total_leds_in_range - 1)
    else:
        required_pitch_mm = theoretical_pitch_mm
    
    # If pitches differ significantly, auto-calibrate
    adjustment_needed = abs(required_pitch_mm - theoretical_pitch_mm) > 0.001
    
    if adjustment_needed:
        calibrated_pitch = required_pitch_mm
        adjustment_info = {
            'was_adjusted': True,
            'theoretical_pitch_mm': theoretical_pitch_mm,
            'calibrated_pitch_mm': calibrated_pitch,
            'difference_mm': calibrated_pitch - theoretical_pitch_mm,
            'difference_percent': ((calibrated_pitch - theoretical_pitch_mm) / theoretical_pitch_mm) * 100,
            'reason': f'Actual LED range ({total_leds_in_range} LEDs) spans {piano_width_mm:.1f}mm, requiring pitch adjustment',
            'theoretical_span_mm': theoretical_span_mm,
            'actual_span_mm': piano_width_mm,
        }
    else:
        calibrated_pitch = theoretical_pitch_mm
        adjustment_info = {
            'was_adjusted': False,
            'theoretical_pitch_mm': theoretical_pitch_mm,
            'calibrated_pitch_mm': calibrated_pitch,
            'difference_mm': 0.0,
            'difference_percent': 0.0,
            'reason': 'Pitch matches theoretical perfectly',
            'theoretical_span_mm': theoretical_span_mm,
            'actual_span_mm': piano_width_mm,
        }
    
    return calibrated_pitch, adjustment_info['was_adjusted'], adjustment_info


# Integration point example:
#
# In mapping generation:
#
# 1. Calculate piano dimensions
#    piano_width = piano_end_mm - piano_start_mm
#
# 2. Auto-calibrate pitch
#    pitch, was_adjusted, info = auto_calibrate_pitch(
#        theoretical_pitch_mm=1000/led_density,
#        piano_start_mm=0,
#        piano_end_mm=piano_width,
#        start_led=start_led,
#        actual_end_led=end_led
#    )
#
# 3. Use calibrated pitch for all LED calculations
#    led_spacing_mm = pitch
#
# 4. Report to user in response
#    if was_adjusted:
#        response['pitch_adjustment'] = {
#            'original_pitch_mm': info['theoretical_pitch_mm'],
#            'adjusted_pitch_mm': info['calibrated_pitch_mm'],
#            'adjustment_percent': info['difference_percent'],
#            'reason': info['reason']
#        }
