try:
    import mido
    MIDO_AVAILABLE = True
    print("✓ mido library available")
except ImportError as e:
    print(f"✗ mido library not available: {e}")
    print("Install with: pip3 install mido python-rtmidi")
    exit(1)

print('Backend details:')
backend = mido.backend
print('Name:', backend.name)
print('API:', getattr(backend, 'api', 'Unknown'))
print('Available ports:')
try:
    print('Inputs:', backend.get_input_names())
    print('Outputs:', backend.get_output_names())
except Exception as e:
    print('Error:', e)

print('\nMido version:', getattr(mido, '__version__', 'Unknown'))
print('Available backends:', mido.available_backends())