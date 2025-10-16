#!/usr/bin/env python3
"""
Test script to verify single USBMIDIInputService instance
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_single_instance():
    """Verify that only one USBMIDIInputService instance is created."""
    print("=" * 60)
    print("Testing: Single USBMIDIInputService Instance")
    print("=" * 60)
    
    # Track instances created
    created_instances = []
    original_init = None
    
    try:
        from backend.usb_midi_service import USBMIDIInputService
        
        # Monkey-patch to track instance creation
        original_init = USBMIDIInputService.__init__
        
        def tracked_init(self, *args, **kwargs):
            created_instances.append(self)
            print(f"✓ USBMIDIInputService instance created (count: {len(created_instances)})")
            return original_init(self, *args, **kwargs)
        
        USBMIDIInputService.__init__ = tracked_init
        
        # Now import app which should create exactly ONE instance
        print("\n[1] Importing app.py...")
        from backend import app
        
        # Check global usb_midi_service
        print(f"\n[2] Global usb_midi_service exists: {app.usb_midi_service is not None}")
        
        # Check midi_input_manager's internal _usb_service
        if app.midi_input_manager:
            print(f"[3] midi_input_manager._usb_service exists: {app.midi_input_manager._usb_service is not None}")
            
            # Check if they're the SAME instance
            if app.usb_midi_service and app.midi_input_manager._usb_service:
                same_instance = app.usb_midi_service is app.midi_input_manager._usb_service
                print(f"[4] CRITICAL: Are they the SAME instance? {same_instance}")
                
                if same_instance:
                    print("\n✅ SUCCESS: Single shared USBMIDIInputService instance in use!")
                    print(f"   - Total instances created: {len(created_instances)}")
                    print("   - app.py has: usb_midi_service")
                    print("   - midi_input_manager has: _usb_service (same reference)")
                    return True
                else:
                    print("\n❌ FAILURE: TWO DIFFERENT instances detected!")
                    print(f"   - app.usb_midi_service id: {id(app.usb_midi_service)}")
                    print(f"   - midi_input_manager._usb_service id: {id(app.midi_input_manager._usb_service)}")
                    return False
    
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore original
        if original_init:
            try:
                USBMIDIInputService.__init__ = original_init
            except:
                pass
    
    return False

if __name__ == '__main__':
    success = test_single_instance()
    sys.exit(0 if success else 1)
