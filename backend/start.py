#!/usr/bin/env python3
"""
Startup script for Piano LED Visualizer Backend
Handles environment setup and application startup
"""

import os
import sys
from pathlib import Path

# Add the parent directory to Python path so 'backend' can be imported as a package
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))

# Set default environment variables
os.environ.setdefault('FLASK_DEBUG', 'False')  # Disabled for production stability
os.environ.setdefault('FLASK_HOST', '0.0.0.0')
os.environ.setdefault('FLASK_PORT', '5001')

if __name__ == '__main__':
    try:
        from backend.app import app, socketio
        print("="*50)
        print("Piano LED Visualizer Backend Starting...")
        print("="*50)
        print(f"Environment: {'Development' if app.config['DEBUG'] else 'Production'}")
        print(f"Server: http://{app.config['HOST']}:{app.config['PORT']}")
        print(f"Health Check: http://{app.config['HOST']}:{app.config['PORT']}/health")
        print("="*50)
        
        # Use standard Flask run for now to test basic functionality
        app.run(
            host=app.config['HOST'],
            port=int(app.config['PORT']),
            debug=bool(app.config['DEBUG']),
            use_reloader=False  # Disable reloader for systemd
        )
    except ImportError as e:
        print(f"Error importing Flask app: {e}")
        print("Please ensure Flask is installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)