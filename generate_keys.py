"""
Genera le chiavi VAPID per le notifiche push.
Esegui una volta sola: python generate_keys.py
Poi aggiungi le chiavi su Render come variabili d'ambiente.
"""
from py_vapid import Vapid

v = Vapid()
v.generate_keys()

print("=" * 60)
print("  CHIAVI VAPID GENERATE — copia su Render!")
print("=" * 60)
print()
print(f"VAPID_PUBLIC_KEY  = {v.public_key.public_bytes_compressed().hex()}")
print()
# Export in formato base64 URL-safe per il browser
import base64
pub_bytes = v.public_key.public_bytes(
    encoding=__import__('cryptography').hazmat.primitives.serialization.Encoding.X962,
    format=__import__('cryptography').hazmat.primitives.serialization.PublicFormat.UncompressedPoint
)
pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b'=').decode()

priv_bytes = v.private_key.private_bytes(
    encoding=__import__('cryptography').hazmat.primitives.serialization.Encoding.PEM,
    format=__import__('cryptography').hazmat.primitives.serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=__import__('cryptography').hazmat.primitives.serialization.NoEncryption()
)

print(f"VAPID_PUBLIC_KEY  = {pub_b64}")
print(f"VAPID_PRIVATE_KEY = {priv_bytes.decode().strip()}")
print(f"VAPID_EMAIL       = mailto:tuaemail@esempio.com")
print()
print("Aggiungi queste 3 variabili su Render → Environment!")
print("=" * 60)
