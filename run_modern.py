#!/usr/bin/env python
"""Entry point for running the modern modular Flask application."""
import os
import sys
from app import create_app
from config import Config

# Create the application
app = create_app(Config)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'

    print(f"\n{'='*60}")
    print(" Starting Smart Document Manager - Modular Version")
    print(f"{'='*60}")
    print(f" * URL: http://localhost:{port}")
    print(f" * Debug: {debug}")
    print(f"{'='*60}")

    app.run(host='0.0.0.0', port=port, debug=debug)