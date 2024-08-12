from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate RSA key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)

# Extract public key in PEM format
public_key = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Extract private key in PEM format
private_key_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)

# Convert bytes to string
public_key_str = public_key.decode('utf-8')
private_key_str = private_key_pem.decode('utf-8')

# Set environment variables
print("PUBLIC KEY:")
print("-----------")
print(public_key_str)

print("\nPRIVATE KEY:")
print("------------")
print(private_key_str)
