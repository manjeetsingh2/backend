import os
import ssl
import datetime
import ipaddress
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.x509.extensions import ExtensionNotFound


CERT_DIR = Path("certs")
CERT_FILE = CERT_DIR / "cert.pem"
KEY_FILE = CERT_DIR / "key.pem"


def print_san_entries(cert_path):
    """
    Load a certificate and print its Subject Alternative Names (SAN) entries.
    """
    with open(cert_path, "rb") as cert_file:
        cert_data = cert_file.read()
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    try:
        san_extension = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        san_values = san_extension.value
        print("🔍 Subject Alternative Names (SAN) in certificate:")
        for entry in san_values:
            print(f" - {entry}")
    except ExtensionNotFound:
        print("⚠️ No SAN extension found in certificate.")


def ensure_ssl_certificates():
    """
    Auto-generate a local-development TLS certificate and key if missing.
    SAN includes: localhost, 127.0.0.1, ::1
    Returns absolute paths to cert and key.
    """
    cert_file = CERT_FILE.resolve()
    key_file = KEY_FILE.resolve()

    # Already present
    if cert_file.exists() and key_file.exists():
        print("✅ SSL certificates found")
        print_san_entries(cert_file)  # Print SAN info for existing cert
        return str(cert_file), str(key_file)

    print("🔄 Generating SSL certificates...")
    CERT_DIR.mkdir(parents=True, exist_ok=True)

    # Private key
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    # Subject / Issuer (self-signed)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Development"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"Local"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Crop Target API"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
        ]
    )

    now = datetime.datetime.utcnow()
    # Start 5 minutes in the past to avoid clock skew issues
    not_before = now - datetime.timedelta(minutes=5)
    not_after = now + datetime.timedelta(days=365)

    san = x509.SubjectAlternativeName(
        [
            x509.DNSName(u"localhost"),
            x509.DNSName(u"127.0.0.1"),
            x509.IPAddress(ipaddress.IPv4Address(u"127.0.0.1")),
            x509.IPAddress(ipaddress.IPv6Address(u"::1")),
        ]
    )

    # Key usage extensions for a TLS server cert
    key_usage = x509.KeyUsage(
        digital_signature=True,
        content_commitment=False,
        key_encipherment=True,
        data_encipherment=False,
        key_agreement=True,
        key_cert_sign=False,
        crl_sign=False,
        encipher_only=False,
        decipher_only=False,
    )
    ext_key_usage = x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(san, critical=False)
        .add_extension(key_usage, critical=True)
        .add_extension(ext_key_usage, critical=False)
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    # Write key
    with open(key_file, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # Write cert
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print("✅ SSL certificates generated successfully")
    print(f"   📄 Certificate: {cert_file}")
    print(f"   🔑 Private key: {key_file}")

    print_san_entries(cert_file)  # Print SAN info for newly generated cert

    return str(cert_file), str(key_file)


def create_ssl_context():
    """
    Create an SSL context for HTTPS servers.
    Returns an ssl.SSLContext configured for a server, or None on failure.
    """
    try:
        cert_file, key_file = ensure_ssl_certificates()
        # Use modern server-side TLS protocol selector
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        # Restrict to strong ciphers if desired (optional):
        # context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:!aNULL:!eNULL:!MD5:!DSS")
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        return context
    except Exception as e:
        print(f"❌ Failed to create SSL context: {e}")
        return None
