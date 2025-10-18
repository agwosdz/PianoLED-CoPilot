#!/usr/bin/env python3
import sys
import math

# --- Define THEORETICAL LED Strip Constants ---
THEORETICAL_LED_DENSITY = 200
THEORETICAL_LED_SPACING = 1000 / THEORETICAL_LED_DENSITY

# --- Define Default Physical Item Constants ---
DEFAULT_LED_PHYSICAL_WIDTH = 2.0 
DEFAULT_LED_STRIP_OFFSET = DEFAULT_LED_PHYSICAL_WIDTH / 2
DEFAULT_LED_OVERHANG_THRESHOLD = 1.0 

# --- Define Solder Joint Constants ---
LED_JOINT_ADDAGE = 1.0
SOLDER_JOINT_POSITIONS = {53, 154} 

# --- Define Calibrated Physical Piano Constants ---
WHITE_KEY_WIDTH = 22.0
BLACK_KEY_WIDTH = 12.0
WHITE_KEY_GAP = 0.976 
WHITE_KEY_PITCH = WHITE_KEY_WIDTH + WHITE_KEY_GAP
cut_A, cut_B, cut_C = 2.2, BLACK_KEY_WIDTH - 2.2, BLACK_KEY_WIDTH / 2
WHITE_KEY_CUTS = {
    'C': [None, 'B'], 'D': ['A', 'A'], 'E': ['B', None],
    'F': [None, 'B'], 'G': ['A', 'C'], 'A': ['C', 'A'], 'B': ['B', None]
}
CUT_VALUES = {'A': cut_A, 'B': cut_B, 'C': cut_C}

# --- Data Maps for the 88-Key Piano ---
KEY_MAP = [
    {'name': 'A0', 'type': 'W'}, {'name': 'A#0', 'type': 'B'}, {'name': 'B0', 'type': 'W'},
    {'name': 'C1', 'type': 'W'}, {'name': 'C#1', 'type': 'B'}, {'name': 'D1', 'type': 'W'},
    {'name': 'D#1', 'type': 'B'}, {'name': 'E1', 'type': 'W'}, {'name': 'F1', 'type': 'W'},
    {'name': 'F#1', 'type': 'B'}, {'name': 'G1', 'type': 'W'}, {'name': 'G#1', 'type': 'B'},
    {'name': 'A1', 'type': 'W'}, {'name': 'A#1', 'type': 'B'}, {'name': 'B1', 'type': 'W'},
    {'name': 'C2', 'type': 'W'}, {'name': 'C#2', 'type': 'B'}, {'name': 'D2', 'type': 'W'},
    {'name': 'D#2', 'type': 'B'}, {'name': 'E2', 'type': 'W'}, {'name': 'F2', 'type': 'W'},
    {'name': 'F#2', 'type': 'B'}, {'name': 'G2', 'type': 'W'}, {'name': 'G#2', 'type': 'B'},
    {'name': 'A2', 'type': 'W'}, {'name': 'A#2', 'type': 'B'}, {'name': 'B2', 'type': 'W'},
    {'name': 'C3', 'type': 'W'}, {'name': 'C#3', 'type': 'B'}, {'name': 'D3', 'type': 'W'},
    {'name': 'D#3', 'type': 'B'}, {'name': 'E3', 'type': 'W'}, {'name': 'F3', 'type': 'W'},
    {'name': 'F#3', 'type': 'B'}, {'name': 'G3', 'type': 'W'}, {'name': 'G#3', 'type': 'B'},
    {'name': 'A3', 'type': 'W'}, {'name': 'A#3', 'type': 'B'}, {'name': 'B3', 'type': 'W'},
    {'name': 'C4', 'type': 'W'}, {'name': 'C#4', 'type': 'B'}, {'name': 'D4', 'type': 'W'},
    {'name': 'D#4', 'type': 'B'}, {'name': 'E4', 'type': 'W'}, {'name': 'F4', 'type': 'W'},
    {'name': 'F#4', 'type': 'B'}, {'name': 'G4', 'type': 'W'}, {'name': 'G#4', 'type': 'B'},
    {'name': 'A4', 'type': 'W'}, {'name': 'A#4', 'type': 'B'}, {'name': 'B4', 'type': 'W'},
    {'name': 'C5', 'type': 'W'}, {'name': 'C#5', 'type': 'B'}, {'name': 'D5', 'type': 'W'},
    {'name': 'D#5', 'type': 'B'}, {'name': 'E5', 'type': 'W'}, {'name': 'F5', 'type': 'W'},
    {'name': 'F#5', 'type': 'B'}, {'name': 'G5', 'type': 'W'}, {'name': 'G#5', 'type': 'B'},
    {'name': 'A5', 'type': 'W'}, {'name': 'A#5', 'type': 'B'}, {'name': 'B5', 'type': 'W'},
    {'name': 'C6', 'type': 'W'}, {'name': 'C#6', 'type': 'B'}, {'name': 'D6', 'type': 'W'},
    {'name': 'D#6', 'type': 'B'}, {'name': 'E6', 'type': 'W'}, {'name': 'F6', 'type': 'W'},
    {'name': 'F#6', 'type': 'B'}, {'name': 'G6', 'type': 'W'}, {'name': 'G#6', 'type': 'B'},
    {'name': 'A6', 'type': 'W'}, {'name': 'A#6', 'type': 'B'}, {'name': 'B6', 'type': 'W'},
    {'name': 'C7', 'type': 'W'}, {'name': 'C#7', 'type': 'B'}, {'name': 'D7', 'type': 'W'},
    {'name': 'D#7', 'type': 'B'}, {'name': 'E7', 'type': 'W'}, {'name': 'F7', 'type': 'W'},
    {'name': 'F#7', 'type': 'B'}, {'name': 'G7', 'type': 'W'}, {'name': 'G#7', 'type': 'B'},
    {'name': 'A7', 'type': 'W'}, {'name': 'A#7', 'type': 'B'}, {'name': 'B7', 'type': 'W'},
    {'name': 'C8', 'type': 'W'}
]

def get_led_center_position(led_index: int, led_offset: float, led_spacing: float) -> float:
    base_pos = (led_index * led_spacing) + led_offset
    num_joints_before = sum(1 for joint_pos in SOLDER_JOINT_POSITIONS if led_index > joint_pos)
    return base_pos + (num_joints_before * LED_JOINT_ADDAGE)

def calculate_all_key_geometries():
    geometries = [{} for _ in range(88)]
    current_pos = 0.0
    for i, key_info in enumerate(KEY_MAP):
        if key_info['type'] == 'W':
            geometries[i]['base_start'] = current_pos
            geometries[i]['base_end'] = current_pos + WHITE_KEY_WIDTH
            current_pos += WHITE_KEY_PITCH
    for i, key_info in enumerate(KEY_MAP):
        if key_info['type'] == 'W':
            geo = geometries[i]
            geo['exposed_start'], geo['exposed_end'] = geo['base_start'], geo['base_end']
            note_name = key_info['name'][0]
            if i > 0 and KEY_MAP[i-1]['type'] == 'B':
                geo['exposed_start'] = geo['base_start'] + CUT_VALUES[WHITE_KEY_CUTS[note_name][0]]
            if i < 87 and KEY_MAP[i+1]['type'] == 'B':
                geo['exposed_end'] = geo['base_end'] - CUT_VALUES[WHITE_KEY_CUTS[note_name][1]]
    for i, key_info in enumerate(KEY_MAP):
        if key_info['type'] == 'B':
            geometries[i]['exposed_start'] = geometries[i-1]['exposed_end']
            geometries[i]['exposed_end'] = geometries[i+1]['exposed_start']
    final_geometries = []
    for i, key_info in enumerate(KEY_MAP):
        geo = geometries[i]
        final_geometries.append({
            "key_number": i + 1, "name": key_info['name'],
            "type": "White" if key_info['type'] == 'W' else "Black",
            "start_mm": round(geo.get('base_start', geo.get('exposed_start')), 2),
            "end_mm": round(geo.get('base_end', geo.get('exposed_end')), 2),
            "exposed_start_mm": round(geo['exposed_start'], 2),
            "exposed_end_mm": round(geo['exposed_end'], 2)
        })
    return final_geometries

def analyze_led_placement_on_top(key_data: dict, led_width: float, led_offset: float, threshold: float, led_spacing: float) -> list:
    key_start_mm, key_end_mm = key_data['exposed_start_mm'], key_data['exposed_end_mm']
    if key_start_mm >= key_end_mm: return []
    leds_on_key = []
    estimated_linear_start_pos = key_start_mm - led_offset
    led_index = math.floor(estimated_linear_start_pos / led_spacing) - 2
    if led_index < 0: led_index = 0
    while True:
        led_center_pos = get_led_center_position(led_index, led_offset, led_spacing)
        led_start_mm, led_end_mm = led_center_pos - (led_width / 2), led_center_pos + (led_width / 2)
        if led_start_mm > key_end_mm + threshold: break
        has_overlap = (led_start_mm < key_end_mm and led_end_mm > key_start_mm)
        within_bounds = (led_start_mm >= key_start_mm - threshold and led_end_mm <= key_end_mm + threshold)
        if has_overlap and within_bounds:
            leds_on_key.append({"led_index": led_index, "center_pos": round(led_center_pos, 2)})
        led_index += 1
    return leds_on_key

def perform_symmetry_analysis(key_data: dict, led_analysis: list) -> dict:
    if not led_analysis: return {"classification": "No LEDs to analyze", "details": ""}
    key_exposed_center = (key_data['exposed_start_mm'] + key_data['exposed_end_mm']) / 2
    min_center_dist = min(abs(led['center_pos'] - key_exposed_center) for led in led_analysis)
    left_edge_dist = abs(led_analysis[0]['center_pos'] - key_data['exposed_start_mm'])
    right_edge_dist = abs(key_data['exposed_end_mm'] - led_analysis[-1]['center_pos'])
    classification = "Asymmetrical"
    if min_center_dist < 0.8: classification = "Excellent Center Alignment"
    elif abs(left_edge_dist - right_edge_dist) < 0.8: classification = "Symmetrical Edge Placement"
    elif min_center_dist < left_edge_dist and min_center_dist < right_edge_dist: classification = "Centered Placement"
    details = (f"  - Dist to key center: {min_center_dist:.2f} mm\n"
               f"  - Dist from left edge: {left_edge_dist:.2f} mm\n"
               f"  - Dist from right edge: {right_edge_dist:.2f} mm")
    return {"classification": classification, "details": details}

def run_single_key_analysis(all_geometries: list, key_number: int, led_width: float, led_offset: float, threshold: float, led_spacing: float, mode_string: str):
    if not 1 <= key_number <= 88:
        print(f"Error: Key number '{key_number}' is invalid.")
        return
    target_key_data = all_geometries[key_number - 1]
    target_leds = analyze_led_placement_on_top(target_key_data, led_width, led_offset, threshold, led_spacing)
    target_led_indices = {led['led_index'] for led in target_leds}
    prev_key_data, next_key_data = None, None
    if key_number > 1: prev_key_data = all_geometries[key_number - 2]
    if key_number < 88: next_key_data = all_geometries[key_number]
        
    print("\n--- Piano Key Position Analysis ---")
    print(f"  MODE: {mode_string} (Using pitch: {led_spacing:.4f} mm)")
    print(f"  Using LED physical width:     {led_width} mm")
    print(f"  Using LED strip offset:       {led_offset} mm")
    print(f"  Using LED overhang threshold: {threshold} mm")
    print(f"  Accounting for solder joints (+{LED_JOINT_ADDAGE}mm) after LEDs: {sorted(list(SOLDER_JOINT_POSITIONS))}")
    print(f"\n  Key Number: {target_key_data['key_number']} ({target_key_data['name']})")
    print(f"  Exposed Top Range for LEDs: {target_key_data['exposed_start_mm']} mm to {target_key_data['exposed_end_mm']} mm")
    print(f"  Exposed Top Midpoint: {(target_key_data['exposed_start_mm'] + target_key_data['exposed_end_mm']) / 2:.2f} mm")
    
    print("\n--- Valid LED Placement Analysis (Top) ---")
    if not target_leds:
        print("  No valid LED placements found for this key.")
    else:
        print(f"  Found {len(target_leds)} valid LED placement(s) for this key:")
        last_led_end = None
        for led in target_leds:
            led_start, led_end = led['center_pos'] - (led_width / 2), led['center_pos'] + (led_width / 2)
            print(f"  > LED #{led['led_index']} | Center: {led['center_pos']:.2f} mm | Physical: {led_start:.2f} to {led_end:.2f} mm")
            if last_led_end is not None: print(f"    (Gap from previous LED: {led_start - last_led_end:.2f} mm)")
            last_led_end = led_end
        print("\n--- Symmetry Analysis ---")
        symmetry_result = perform_symmetry_analysis(target_key_data, target_leds)
        print(f"  Classification: {symmetry_result['classification']}")
        print(symmetry_result['details'])
    
    print("\n--- Neighbor Interaction Analysis ---")
    if prev_key_data:
        prev_leds = analyze_led_placement_on_top(prev_key_data, led_width, led_offset, threshold, led_spacing)
        prev_led_indices = {led['led_index'] for led in prev_leds}
        print(f"Analysis with Previous Key (#{prev_key_data['key_number']} - {prev_key_data['name']}):")
        shared_with_prev = target_led_indices.intersection(prev_led_indices)
        print(f"  Shared LEDs: {', '.join(f'#{i}' for i in sorted(list(shared_with_prev))) or ['None']}")
        if target_leds and prev_leds and min(target_led_indices) == max(prev_led_indices) + 1:
            print(f"  Consecutive Coverage: YES (Prev ends on #{max(prev_led_indices)}, this starts on #{min(target_led_indices)})")
        else: print("  Consecutive Coverage: NO or N/A")
    else: print("No previous key to analyze.")
    print("")
    if next_key_data:
        next_leds = analyze_led_placement_on_top(next_key_data, led_width, led_offset, threshold, led_spacing)
        next_led_indices = {led['led_index'] for led in next_leds}
        print(f"Analysis with Next Key (#{next_key_data['key_number']} - {next_key_data['name']}):")
        shared_with_next = target_led_indices.intersection(next_led_indices)
        print(f"  Shared LEDs: {', '.join(f'#{i}' for i in sorted(list(shared_with_next))) or ['None']}")
        if target_leds and next_leds and max(target_led_indices) + 1 == min(next_led_indices):
            print(f"  Consecutive Coverage: YES (This ends on #{max(target_led_indices)}, next starts on #{min(next_led_indices)})")
        else: print("  Consecutive Coverage: NO or N/A")
    else: print("No next key to analyze.")
    print("----------------------------------------\n")

def calculate_total_leds(all_geometries, led_width, led_offset, threshold, led_spacing):
    """A silent utility to calculate the total required LEDs."""
    highest_led_index_used = -1
    for key_data in all_geometries:
        led_analysis = analyze_led_placement_on_top(key_data, led_width, led_offset, threshold, led_spacing)
        if led_analysis:
            highest_led_index_used = max(highest_led_index_used, led_analysis[-1]['led_index'])
    return highest_led_index_used + 1 if highest_led_index_used > -1 else 0

def run_full_strip_analysis(all_geometries: list, led_width: float, led_offset: float, threshold: float, led_spacing: float, mode_string: str):
    print("\n=======================================================")
    print("      FULL PIANO STRIP LED COVERAGE REPORT (TOP VIEW)")
    print("=======================================================")
    print(f"  MODE: {mode_string} (Using pitch: {led_spacing:.4f} mm)")
    print(f"Analyzing with LED width: {led_width} mm, offset: {led_offset} mm, threshold: {threshold} mm")
    print(f"Accounting for solder joints (+{LED_JOINT_ADDAGE}mm) after LEDs: {sorted(list(SOLDER_JOINT_POSITIONS))}\n")
    
    highest_led_index_used = -1
    for key_data in all_geometries:
        print(f"--- Key {key_data['key_number']} ({key_data['name']}) | Top Exposed: {key_data['exposed_start_mm']} to {key_data['exposed_end_mm']} mm ---")
        led_analysis = analyze_led_placement_on_top(key_data, led_width, led_offset, threshold, led_spacing)
        if not led_analysis:
            print("    Valid LEDs: None")
        else:
            highest_led_index_used = max(highest_led_index_used, led_analysis[-1]['led_index'])
            led_info = [f"#{led['led_index']}" for led in led_analysis]
            print(f"    Valid LEDs ({len(led_analysis)}): {', '.join(led_info)}")
    
    total_leds_required = highest_led_index_used + 1 if highest_led_index_used > -1 else 0
    print("\n=======================================================")
    print("                    REPORT SUMMARY")
    print("-------------------------------------------------------")
    print(f"  Highest LED index required: {highest_led_index_used}")
    print(f"  Total number of LEDs for the entire strip: {total_leds_required}")
    print("=======================================================\n")

def main():
    all_key_geometries = calculate_all_key_geometries()
    target_key = None
    led_width, led_offset, threshold = DEFAULT_LED_PHYSICAL_WIDTH, DEFAULT_LED_STRIP_OFFSET, DEFAULT_LED_OVERHANG_THRESHOLD
    led_spacing, mode_string = THEORETICAL_LED_SPACING, "THEORETICAL"

    try:
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            if command == 'calibrate':
                if len(sys.argv) == 4:
                    total_leds, total_length = int(sys.argv[2]), float(sys.argv[3])
                    led_spacing = total_length / (total_leds - 1)
                    mode_string, target_key = f"CALIBRATED (from length)", 'all'
                    print(f"--- CALIBRATION MODE ACTIVATED ---")
                    print(f"Derived real-world average LED spacing: {led_spacing:.4f} mm")
                else: raise ValueError("Calibration mode requires <total_leds> and <total_length_mm>.")
            
            elif command == 'scale':
                if len(sys.argv) >= 3:
                    expected_leds = int(sys.argv[2])
                    base_pitch = float(sys.argv[3]) if len(sys.argv) > 3 else THEORETICAL_LED_SPACING
                    print(f"--- SCALING MODE ACTIVATED ---")
                    print(f"Attempting to scale to fit {expected_leds} LEDs, starting from a base pitch of {base_pitch:.4f} mm.")
                    
                    calculated_leds = calculate_total_leds(all_key_geometries, led_width, led_offset, threshold, base_pitch)
                    
                    if calculated_leds == expected_leds:
                        print("Base pitch already produces the correct number of LEDs. No scaling needed.")
                        led_spacing = base_pitch
                        mode_string = f"SCALED (from count, no change)"
                    else:
                        scaling_factor = (calculated_leds - 1) / (expected_leds - 1)
                        led_spacing = base_pitch * scaling_factor
                        mode_string = f"SCALED (from count)"
                        print(f"Dry run calculated {calculated_leds} LEDs. A scaling factor of {scaling_factor:.6f} will be applied.")
                        print(f"New adjusted LED spacing: {led_spacing:.4f} mm")
                    target_key = 'all'
                else: raise ValueError("Scale mode requires <expected_leds> and an optional [base_pitch].")

            elif command != 'all':
                target_key = int(command)
        
        # Standard parameter parsing (only for non-calibration/scaling modes)
        if mode_string == "THEORETICAL":
            if len(sys.argv) > 2: led_width = float(sys.argv[2])
            if len(sys.argv) > 3: led_offset = float(sys.argv[3])
            if len(sys.argv) > 4: threshold = float(sys.argv[4])

    except (ValueError, IndexError) as e:
        print(f"Error: Invalid arguments. {e}")
        print("Usage:")
        print("  For single key: python piano.py [key] [width] [offset] [threshold]")
        print("  For full report: python piano.py all [width] [offset] [threshold]")
        print("  For calibration: python piano.py calibrate <total_leds> <total_length_mm>")
        print("  For scaling:     python piano.py scale <expected_leds> [base_pitch]")
        sys.exit(1)
        
    if target_key == 'all':
        run_full_strip_analysis(all_key_geometries, led_width, led_offset, threshold, led_spacing, mode_string)
    elif target_key is not None:
        run_single_key_analysis(all_key_geometries, target_key, led_width, led_offset, threshold, led_spacing, mode_string)
    else: # Default behavior: full report
        run_full_strip_analysis(all_key_geometries, led_width, led_offset, threshold, led_spacing, mode_string)

if __name__ == "__main__":
    main()