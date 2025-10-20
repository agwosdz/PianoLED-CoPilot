import os
import json
from flask import Blueprint, request, jsonify, current_app
from pathlib import Path

play_bp = Blueprint('play', __name__)


@play_bp.route('/uploaded-midi-files', methods=['GET'])
def get_uploaded_files():
    """Get list of uploaded MIDI files."""
    try:
        midi_dir = Path(current_app.config.get('UPLOADED_MIDI_DIR', './uploaded_midi'))
        
        if not midi_dir.exists():
            return jsonify([])
        
        files = []
        for file_path in midi_dir.glob('*.mid'):
            files.append({
                'filename': file_path.name,
                'path': str(file_path),
                'size': file_path.stat().st_size
            })
        
        # Sort by name
        files.sort(key=lambda x: x['filename'])
        return jsonify(files)
    except Exception as e:
        current_app.logger.error(f"Error listing MIDI files: {e}")
        return jsonify({'error': str(e)}), 500


@play_bp.route('/midi-notes', methods=['GET'])
def get_midi_notes():
    """Get MIDI notes from a file for visualization."""
    try:
        filename = request.args.get('filename')
        if not filename:
            return jsonify({'error': 'filename required'}), 400
        
        # Security: prevent path traversal
        filename = Path(filename).name
        # Use the same UPLOAD_FOLDER as the main app for consistency
        upload_folder = current_app.config.get('UPLOAD_FOLDER', './backend/uploads')
        file_path = Path(upload_folder) / filename
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        # Use MIDI parser to extract notes
        from backend.midi_parser import MIDIParser
        
        # Get settings service from app config
        settings_service = current_app.config.get('settings_service')
        
        parser = MIDIParser(settings_service=settings_service)
        parsed_data = parser.parse_file(str(file_path))
        
        if not parsed_data:
            return jsonify({'error': 'Failed to parse MIDI file'}), 400
        
        # Convert MIDI events (on/off pairs) to note visualization format
        # The parser returns events with 'type' of 'on' or 'off'
        notes = []
        note_on_map = {}  # Maps note number to (start_time, velocity)
        
        for event in parsed_data.get('events', []):
            note_num = event['note']
            event_time = event['time']
            
            if event['type'] == 'on':
                # Store note_on event
                note_on_map[note_num] = (event_time, event['velocity'])
            elif event['type'] == 'off' and note_num in note_on_map:
                # Match with note_on and create a complete note
                start_time, velocity = note_on_map[note_num]
                duration = event_time - start_time
                
                notes.append({
                    'note': note_num,
                    'startTime': start_time / 1000.0,  # Convert ms to seconds
                    'duration': duration / 1000.0,
                    'velocity': velocity
                })
                del note_on_map[note_num]
        
        # Sort notes by start time
        notes.sort(key=lambda x: x['startTime'])
        
        return jsonify({
            'notes': notes,
            'tempo': 120,  # Default tempo if not specified
            'total_duration': parsed_data.get('duration', 0) / 1000.0  # Convert ms to seconds
        })
    except Exception as e:
        current_app.logger.error(f"Error extracting MIDI notes: {e}")
        return jsonify({'error': str(e)}), 500


@play_bp.route('/playback-status', methods=['GET'])
def get_playback_status():
    """Get current playback status."""
    try:
        playback_service = current_app.config.get('playback_service')
        
        if not playback_service:
            return jsonify({
                'state': 'idle',
                'current_time': 0,
                'total_duration': 0,
                'filename': None,
                'progress_percentage': 0,
                'error_message': 'Playback service not available'
            }), 500
        
        return jsonify({
            'state': playback_service.state.value if hasattr(playback_service.state, 'value') else str(playback_service.state),
            'current_time': playback_service.current_time,
            'total_duration': playback_service.total_duration,
            'filename': playback_service.filename,
            'progress_percentage': (playback_service.current_time / playback_service.total_duration * 100) if playback_service.total_duration > 0 else 0,
            'error_message': None
        })
    except Exception as e:
        current_app.logger.error(f"Error getting playback status: {e}")
        return jsonify({'error': str(e)}), 500


@play_bp.route('/play', methods=['POST'])
def play():
    """Start playback of a MIDI file."""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'error': 'filename required'}), 400
        
        # Security: prevent path traversal
        filename = Path(filename).name
        # Use the same UPLOAD_FOLDER as the main app for consistency
        upload_folder = current_app.config.get('UPLOAD_FOLDER', './backend/uploads')
        file_path = Path(upload_folder) / filename
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        playback_service = current_app.config.get('playback_service')
        if not playback_service:
            return jsonify({'error': 'Playback service not available'}), 500
        
        # Load the file first
        if not playback_service.load_midi_file(str(file_path)):
            return jsonify({'error': 'Failed to load MIDI file'}), 400
        
        # Then start playback
        if not playback_service.start_playback():
            return jsonify({'error': 'Failed to start playback'}), 400
        
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Error starting playback: {e}")
        return jsonify({'error': str(e)}), 500


@play_bp.route('/pause', methods=['POST'])
def pause():
    """Pause or resume playback."""
    try:
        playback_service = current_app.config.get('playback_service')
        
        if not playback_service:
            return jsonify({'error': 'Playback service not available'}), 500
        
        # Toggle pause/resume
        playback_service.pause_playback()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Error pausing playback: {e}")
        return jsonify({'error': str(e)}), 500


@play_bp.route('/stop', methods=['POST'])
def stop():
    """Stop playback."""
    try:
        playback_service = current_app.config.get('playback_service')
        
        if not playback_service:
            return jsonify({'error': 'Playback service not available'}), 500
        
        playback_service.stop_playback()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Error stopping playback: {e}")
        return jsonify({'error': str(e)}), 500
