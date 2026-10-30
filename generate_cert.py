"""
Self-signed SSL Certificate Generator for Local / Mobile LAN Development
Generates cert.pem and key.pem with localhost and local LAN IP in Subject Alternative Name (SAN).
"""
import os
import socket
import datetime
import ipaddress
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def generate_self_signed_cert(cert_path='cert.pem', key_path='key.pem'):
    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"[OK] SSL certificate files already exist ({cert_path}, {key_path}).")
        return cert_path, key_path

    print("[*] Generating self-signed SSL certificate for local HTTPS...")
    local_ip = get_local_ip()

    # Generate RSA private key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Smart Document Manager Dev"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost")
    ])

    san_list = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))
    ]
    if local_ip != '127.0.0.1':
        try:
            san_list.append(x509.IPAddress(ipaddress.IPv4Address(local_ip)))
        except Exception:
            pass

    san = x509.SubjectAlternativeName(san_list)

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(san, critical=False)
        .sign(key, hashes.SHA256())
    )

    # Write private key
    with open(key_path, 'wb') as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Write cert
    with open(cert_path, 'wb') as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"[SUCCESS] Generated SSL certificate: {cert_path} and private key: {key_path}")
    print(f"[*] Configured SAN for: localhost, 127.0.0.1, {local_ip}")
    return cert_path, key_path


if __name__ == '__main__':
    generate_self_signed_cert()
