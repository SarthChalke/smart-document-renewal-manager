"""
Secure HTTPS Development Server for Smart Document & Financial Manager
Allows device camera access on mobile phones across local Wi-Fi / LAN.
"""
import os
import sys
from generate_cert import generate_self_signed_cert, get_local_ip
from app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    cert_path, key_path = generate_self_signed_cert('cert.pem', 'key.pem')
    local_ip = get_local_ip()

    print("=" * 70)
    print(" SMART DOCUMENT & FINANCIAL MANAGER — SECURE HTTPS DEV SERVER")
    print("=" * 70)
    print(f" * Local Laptop Access : https://localhost:{port}")
    print(f" * Mobile Phone Access : https://{local_ip}:{port}")
    print("=" * 70)
    print(" * Note: When opening https:// on your phone for the first time,")
    print("   tap 'Advanced' -> 'Proceed to site' to accept the self-signed dev cert.")
    print("   Live webcam and device camera streaming will now be fully authorized!")
    print("=" * 70)

    app.run(host='0.0.0.0', port=port, ssl_context=(cert_path, key_path), debug=False)
