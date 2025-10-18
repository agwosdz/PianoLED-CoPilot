#!/usr/bin/env python3
import sys
import math

# --- Define LED Strip Constants ---
LED_DENSITY = 200
LED_SPACING = 1000 / LED_DENSITY
DEFAULT_LED_PHYSICAL_WIDTH = 3.5 #3.5 Defaiult physical width of WS2812B LED in mm
DEFAULT_LED_STRIP_OFFSET = DEFAULT_LED_PHYSICAL_WIDTH / 2
DEFAULT_LED_OVERHANG_THRESHOLD = 1.5 # 1.5 mm default overhang threshold

# --- Define Physical Constants ---
WHITE_KEY_WIDTH = 22.0 #23.5 mm width of a standard white piano key
WHITE_KEY_GAP = 1.0 #1.0 mm gap between white keys
WHITE_KEY_PITCH = WHITE_KEY_WIDTH + WHITE_KEY_GAP
BLACK_KEY_WIDTH = 12.0 #13.7 mm width of a standard black piano key
cut_A = 2.2
cut_B = BLACK_KEY_WIDTH - cut_A
cut_C = BLACK_KEY_WIDTH / 2
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
            geo['exposed_start'] = geo['base_start']
            geo['exposed_end'] = geo['base_end']
            note_name = key_info['name'][0]
            if i > 0 and KEY_MAP[i-1]['type'] == 'B':
                cut_type = WHITE_KEY_CUTS[note_name][0]
                geo['exposed_start'] = geo['base_start'] + CUT_VALUES[cut_type]
            if i < 87 and KEY_MAP[i+1]['type'] == 'B':
                cut_type = WHITE_KEY_CUTS[note_name][1]
                geo['exposed_end'] = geo['base_end'] - CUT_VALUES[cut_type]
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

def analyze_led_placement_on_top(key_data: dict, led_width: float, led_offset: float, threshold: float) -> list:
    key_start_mm = key_data['exposed_start_mm']
    key_end_mm = key_data['exposed_end_mm']
    if key_start_mm >= key_end_mm: return []
    leds_on_key = []
    search_start_pos = key_start_mm - led_offset
    led_index = math.floor(search_start_pos / LED_SPACING) - 2
    if led_index < 0: led_index = 0
    while True:
        led_center_pos = (led_index * LED_SPACING) + led_offset
        led_start_mm = led_center_pos - (led_width / 2)
        led_end_mm = led_center_pos + (led_width / 2)
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

def run_single_key_analysis(all_geometries: list, key_number: int, led_width: float, led_offset: float, threshold: float):
    if not 1 <= key_number <= 88:
        print(f"Error: Key number '{key_number}' is invalid.")
        return
    target_key_data = all_geometries[key_number - 1]
    target_leds = analyze_led_placement_on_top(target_key_data, led_width, led_offset, threshold)
    target_led_indices = {led['led_index'] for led in target_leds}
    prev_key_data, prev_leds, prev_led_indices = None, [], set()
    if key_number > 1:
        prev_key_data = all_geometries[key_number - 2]
        prev_leds = analyze_led_placement_on_top(prev_key_data, led_width, led_offset, threshold)
        prev_led_indices = {led['led_index'] for led in prev_leds}
    next_key_data, next_leds, next_led_indices = None, [], set()
    if key_number < 88:
        next_key_data = all_geometries[key_number]
        next_leds = analyze_led_placement_on_top(next_key_data, led_width, led_offset, threshold)
        next_led_indices = {led['led_index'] for led in next_leds}
    exposed_midpoint = (target_key_data['exposed_start_mm'] + target_key_data['exposed_end_mm']) / 2
    print("\n--- Piano Key Position Analysis ---")
    print(f"  Using LED physical width:     {led_width} mm")
    print(f"  Using LED strip offset:       {led_offset} mm")
    print(f"  Using LED overhang threshold: {threshold} mm")
    print(f"\n  Key Number: {target_key_data['key_number']} ({target_key_data['name']})")
    print(f"  Physical Front Range: {target_key_data['start_mm']} mm to {target_key_data['end_mm']} mm")
    print(f"  Exposed Top Range for LEDs: {target_key_data['exposed_start_mm']} mm to {target_key_data['exposed_end_mm']} mm")
    print(f"  Exposed Top Midpoint: {exposed_midpoint:.2f} mm")
    print("\n--- Valid LED Placement Analysis (Top) ---")
    if not target_leds:
        print("  No valid LED placements found for this key.")
    else:
        print(f"  Found {len(target_leds)} valid LED placement(s) for this key:")
        last_led_end = None
        for led in target_leds:
            led_start = led['center_pos'] - (led_width / 2)
            led_end = led['center_pos'] + (led_width / 2)
            print(f"  > LED #{led['led_index']} | Center: {led['center_pos']:.2f} mm | Physical: {led_start:.2f} to {led_end:.2f} mm")
            if last_led_end is not None:
                gap = led_start - last_led_end
                print(f"    (Gap from previous LED: {gap:.2f} mm)")
            last_led_end = led_end
        print("\n--- Symmetry Analysis ---")
        symmetry_result = perform_symmetry_analysis(target_key_data, target_leds)
        print(f"  Classification: {symmetry_result['classification']}")
        print(symmetry_result['details'])
    print("\n--- Neighbor Interaction Analysis ---")
    if prev_key_data:
        print(f"Analysis with Previous Key (#{prev_key_data['key_number']} - {prev_key_data['name']}):")
        shared_with_prev = target_led_indices.intersection(prev_led_indices)
        if shared_with_prev: print(f"  Shared LEDs: {', '.join(f'#{i}' for i in sorted(list(shared_with_prev)))}")
        else: print("  Shared LEDs: None")
        if target_led_indices and prev_led_indices:
            if min(target_led_indices) == max(prev_led_indices) + 1:
                print(f"  Consecutive Coverage: YES (Prev key ends on #{max(prev_led_indices)}, this key starts on #{min(target_led_indices)})")
            else: print("  Consecutive Coverage: NO (Gap exists between keys)")
        else: print("  Consecutive Coverage: N/A (One or both keys have no LEDs)")
    else: print("No previous key to analyze.")
    print("")
    if next_key_data:
        print(f"Analysis with Next Key (#{next_key_data['key_number']} - {next_key_data['name']}):")
        shared_with_next = target_led_indices.intersection(next_led_indices)
        if shared_with_next: print(f"  Shared LEDs: {', '.join(f'#{i}' for i in sorted(list(shared_with_next)))}")
        else: print("  Shared LEDs: None")
        if target_led_indices and next_led_indices:
            if max(target_led_indices) + 1 == min(next_led_indices):
                print(f"  Consecutive Coverage: YES (This key ends on #{max(target_led_indices)}, next key starts on #{min(next_led_indices)})")
            else: print("  Consecutive Coverage: NO (Gap exists between keys)")
        else: print("  Consecutive Coverage: N/A (One or both keys have no LEDs)")
    else: print("No next key to analyze.")
    print("----------------------------------------\n")

def run_full_strip_analysis(all_geometries: list, led_width: float, led_offset: float, threshold: float):
    print("\n=======================================================")
    print("      FULL PIANO STRIP LED COVERAGE REPORT (TOP VIEW)")
    print("=======================================================")
    print(f"Analyzing with LED width: {led_width} mm, offset: {led_offset} mm, threshold: {threshold} mm\n")
    highest_led_index_used = -1
    for key_data in all_geometries:
        print(f"--- Key {key_data['key_number']} ({key_data['name']}) | Top Exposed: {key_data['exposed_start_mm']} to {key_data['exposed_end_mm']} mm ---")
        led_analysis = analyze_led_placement_on_top(key_data, led_width, led_offset, threshold)
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
    led_width = DEFAULT_LED_PHYSICAL_WIDTH
    led_offset = DEFAULT_LED_STRIP_OFFSET
    threshold = DEFAULT_LED_OVERHANG_THRESHOLD
    try:
        if len(sys.argv) > 1 and sys.argv[1].lower() != 'all':
            target_key = int(sys.argv[1])
        if len(sys.argv) > 2:
            led_width = float(sys.argv[2])
        if len(sys.argv) > 3:
            led_offset = float(sys.argv[3])
        if len(sys.argv) > 4:
            threshold = float(sys.argv[4])
    except (ValueError, IndexError):
        print("Error: Invalid arguments.")
        print("Usage: python piano_led_locator.py [key_number|all] [width] [offset] [threshold]")
        print(f"  - key_number: 1-88 (optional, default: full report)")
        print(f"  - width:      Physical LED width in mm (optional, default: {DEFAULT_LED_PHYSICAL_WIDTH})")
        print(f"  - offset:     Global LED strip offset in mm (optional, default: {DEFAULT_LED_STRIP_OFFSET:.2f})")
        print(f"  - threshold:  Max allowed LED overhang in mm (optional, default: {DEFAULT_LED_OVERHANG_THRESHOLD})")
        sys.exit(1)
        
    # *** CORRECTED LINES ***
    if target_key is not None:
        run_single_key_analysis(all_key_geometries, target_key, led_width, led_offset, threshold)
    else:
        run_full_strip_analysis(all_key_geometries, led_width, led_offset, threshold)

if __name__ == "__main__":
    main()