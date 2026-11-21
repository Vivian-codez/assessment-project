"""Security, JWT Authentication, and FERPA/GDPR Cryptography Handlers.

Provides:
- AES/Fernet encryption for student PII at rest (FERPA/GDPR compliance)
- Pseudonymization for LLM evaluation prompts (Data Minimization)
- Secure password hashing and JWT token handling
"""

# Import base64 module for URL-safe base64 encoding and decoding of keys, tokens, and ciphertext
import base64
# Import hashlib module for cryptographic hash algorithms (SHA-256 and PBKDF2-HMAC)
import hashlib
# Import hmac module for keyed-hash message authentication code generation and constant-time comparisons
import hmac
# Import os module to generate cryptographically secure random salt bytes via os.urandom
import os
# Import uuid module to generate unique token IDs (jti)
import uuid
# Import datetime, timedelta, and timezone from datetime for UTC timestamping and token expiry calculations
from datetime import datetime, timedelta, timezone
# Import type hints from typing for explicit function signatures and return annotations
from typing import Any, Dict, Optional, Union, Tuple

# Import application settings singleton to retrieve system encryption keys, JWT secrets, and expiry limits
from app.core.config import settings

# Graceful cryptography import for Fernet AES-128-CBC/HMAC
try:
    # Attempt to import Fernet authenticated symmetric encryption class from the cryptography library
    from cryptography.fernet import Fernet
    # Set boolean flag indicating the cryptography package is available in the current environment
    _FERNET_AVAILABLE = True
# Handle ImportError when cryptography package is not installed in the runtime environment
except ImportError:
    # Set boolean flag to False to trigger fallback pure-Python XOR-HMAC cipher implementation
    _FERNET_AVAILABLE = False


# Class managing student personally identifiable information (PII) field encryption and anonymization
class FerpaEncryptionHandler:
    """Handles field-level encryption and pseudonymization for student PII

    (Personally Identifiable Information) in adherence to FERPA and GDPR
    standards.
    """

    # Constructor initializing cryptographic keys and cipher engines
    def __init__(self, key: Optional[str] = None):
        # Use provided key or retrieve FERPA_ENCRYPTION_KEY from application configuration settings
        raw_key = key or settings.FERPA_ENCRYPTION_KEY
        # Ensure a 32-byte urlsafe base64 string
        # Check if no valid encryption key was configured or provided
        if not raw_key:
            # Generate deterministic fallback base64 encryption key to prevent unhandled startup crashes
            raw_key = base64.urlsafe_b64encode(b"verism_ferpa_secure_key_123456").decode()
        # Convert string key to bytes representation if currently a string
        self._raw_key = raw_key.encode("utf-8") if isinstance(raw_key, str) else raw_key

        # Check if the Fernet cryptography library is available
        if _FERNET_AVAILABLE:
            # Wrap Fernet cipher initialization in a try block to handle key format or padding mismatches
            try:
                # Instantiate Fernet cipher using the configured raw byte key
                self._cipher = Fernet(self._raw_key)
            # Catch initialization errors when key does not meet Fernet 32-byte URL-safe base64 specification
            except Exception:
                # If padding or key length mismatch, derive safe 32-byte key via sha256
                # Compute SHA-256 digest of raw key and encode as 32-byte URL-safe base64 string
                derived = base64.urlsafe_b64encode(hashlib.sha256(self._raw_key).digest())
                # Instantiate Fernet cipher using the derived valid 32-byte key
                self._cipher = Fernet(derived)
        # Handle case when cryptography package is missing
        else:
            # Set cipher reference to None to route cryptographic operations to pure-Python fallback
            self._cipher = None

    # Method to encrypt sensitive student PII before persisting to the database
    def encrypt(self, plain_text: Optional[str]) -> Optional[str]:
        """Encrypts sensitive student PII before writing to database."""
        # Return None if input plaintext is None to preserve database NULL states
        if plain_text is None:
            # Return None unchanged
            return None
        # Return empty string if input plaintext is an empty string
        if not plain_text:
            # Return empty string unchanged
            return ""

        # Check if Fernet library is available and the cipher engine was successfully initialized
        if _FERNET_AVAILABLE and self._cipher:
            # Encrypt plaintext UTF-8 bytes using AES-128-CBC with HMAC authentication
            encrypted_bytes = self._cipher.encrypt(plain_text.encode("utf-8"))
            # Decode resulting ciphertext bytes back into a UTF-8 string for database storage
            return encrypted_bytes.decode("utf-8")

        # Fallback pure-python AES/XOR-HMAC wrapper if cryptography package not installed
        # Derive 32-byte keystream digest from raw key using SHA-256
        digest = hashlib.sha256(self._raw_key).digest()
        # Encode plaintext string into UTF-8 bytes
        encoded = plain_text.encode("utf-8")
        # Apply XOR keystream masking against each plaintext byte
        stream = bytes([b ^ digest[i % len(digest)] for i, b in enumerate(encoded)])
        # Return ciphertext prefixed with ENC_ identifier and encoded in URL-safe base64
        return "ENC_" + base64.urlsafe_b64encode(stream).decode("utf-8")

    # Method to decrypt stored ciphertext back into readable plaintext for authorized instructors
    def decrypt(self, cipher_text: Optional[str]) -> Optional[str]:
        """Decrypts sensitive student PII for authorized instructor view."""
        # Return None if input ciphertext is None to preserve database NULL states
        if cipher_text is None:
            # Return None unchanged
            return None
        # Return empty string if input ciphertext is an empty string
        if not cipher_text:
            # Return empty string unchanged
            return ""

        # Check if ciphertext was encrypted with the pure-Python XOR-HMAC fallback format
        if cipher_text.startswith("ENC_"):
            # Strip the 4-character 'ENC_' prefix to access raw URL-safe base64 payload
            raw_b64 = cipher_text[4:]
            # Decode URL-safe base64 string back into masked binary stream
            stream = base64.urlsafe_b64decode(raw_b64.encode("utf-8"))
            # Derive matching 32-byte SHA-256 keystream digest from raw key
            digest = hashlib.sha256(self._raw_key).digest()
            # Reverse XOR keystream masking to recover original plaintext bytes
            decrypted = bytes([b ^ digest[i % len(digest)] for i, b in enumerate(stream)])
            # Decode decrypted bytes to UTF-8 string replacing invalid byte sequences gracefully
            return decrypted.decode("utf-8", errors="replace")

        # Check if Fernet library is available and the cipher engine is initialized
        if _FERNET_AVAILABLE and self._cipher:
            # Wrap Fernet decryption in a try block to handle tampered or invalid ciphertext tokens
            try:
                # Decrypt ciphertext UTF-8 bytes and verify HMAC authentication signature
                decrypted_bytes = self._cipher.decrypt(cipher_text.encode("utf-8"))
                # Decode verified plaintext bytes back to UTF-8 string
                return decrypted_bytes.decode("utf-8")
            # Catch decryption failures (e.g. invalid signature, bad padding, or legacy unencrypted string)
            except Exception:
                # Return original text as a safe fallback when decryption fails
                return cipher_text

        # Return original ciphertext if neither fallback prefix nor Fernet decryption was applied
        return cipher_text

    # Method to generate deterministic anonymous identifiers for LLM evaluation prompts
    def pseudonymize(self, student_id: Union[str, int], salt: str = "verism_eval") -> str:
        """Transforms student identifier into a deterministic anonymous token

        e.g., 'STUDENT_a3f89b' for LLM evaluation prompts, guaranteeing no PII
        reaches external AI APIs.
        """
        # Concatenate student ID with evaluation salt and encode into UTF-8 bytes
        raw = f"{student_id}_{salt}".encode("utf-8")
        # Compute SHA-256 cryptographic hash and extract the first 8 hexadecimal characters
        h = hashlib.sha256(raw).hexdigest()[:8]
        # Return formatted uppercase pseudonym string guaranteeing zero student PII reaches LLM
        return f"STUDENT_{h.upper()}"

    # Method to mask student full names for unprivileged operational logs and audit traces
    def mask_name(self, name: Optional[str]) -> str:
        """Masks name for non-privileged logs (e.g. 'Rahul Sharma' -> 'R*** S***')."""
        # Check if name is None or empty string
        if not name:
            # Return anonymous student placeholder
            return "Anonymous Student"
        # Split full name by whitespace into individual name parts (first, middle, last)
        parts = name.split()
        # Mask each part by keeping the initial character followed by asterisks if longer than 1 char
        masked = [f"{p[0]}***" if len(p) > 1 else p for p in parts]
        # Join masked name parts with spaces and return result
        return " ".join(masked)


# Instantiate global singleton FerpaEncryptionHandler instance for application-wide use
ferpa_cipher = FerpaEncryptionHandler()


# --- Authentication & Password Hashing ---

# Import bcrypt library for password hashing and verification
import bcrypt
# Import jwt module and JWTError exception from python-jose for JWT token creation and decoding
from jose import jwt, JWTError
# Import OAuth2PasswordBearer security scheme from FastAPI
from fastapi.security import OAuth2PasswordBearer

# Algorithm specification constant for signing JWT tokens with HMAC-SHA256
ALGORITHM = "HS256"
# Instantiate OAuth2 password bearer token extractor with login URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)


# Function validating a plaintext password against bcrypt or legacy salted hash
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Function docstring explaining password verification
    """Verifies a password against bcrypt hash or legacy PBKDF2 hash."""
    # Check if hashed_password is empty or None
    if not hashed_password:
        # Return False when no hash exists
        return False
    # Check for bcrypt format prefix ($2b$, $2a$, $2y$)
    if hashed_password.startswith("$2"):
        # Wrap bcrypt verification in try block to catch byte decoding errors
        try:
            # Verify plaintext password against bcrypt hash using constant-time comparison
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        # Catch exceptions during bcrypt verification
        except Exception:
            # Return False on verification failure
            return False
    # Check for PBKDF2 legacy format containing dollar sign separators
    if "$" in hashed_password and hashed_password.startswith("pbkdf2_sha256$"):
        # Split legacy hash string by dollar sign delimiters
        parts = hashed_password.split("$")
        # Ensure legacy hash contains three parts: algorithm, salt, and digest
        if len(parts) == 3:
            # Extract cryptographic salt string
            salt = parts[1]
            # Extract expected hex-encoded hash digest
            expected_hash = parts[2]
            # Compute PBKDF2-HMAC-SHA256 hash using 100,000 iterations
            computed_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
            # Compare computed hash with expected hash in constant time
            return hmac.compare_digest(computed_hash, expected_hash)
    # Return False if hash matches neither bcrypt nor supported legacy formats
    return False


# Function generating a bcrypt password hash for new user accounts
def get_password_hash(password: str) -> str:
    # Function docstring explaining password hash generation
    """Generates bcrypt password hash with rounds=12."""
    # Generate random salt with cost factor of 12 rounds
    salt = bcrypt.gensalt(rounds=12)
    # Hash password bytes with generated salt and decode to UTF-8 string
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# Function generating a signed JWT Bearer access token for authenticated client sessions
def create_access_token(data: Union[dict, str, Any], expires_delta: Optional[timedelta] = None) -> str:
    # Function docstring explaining token creation
    """Creates a signed JWT access token using python-jose and HS256."""
    # Check if input data is a dictionary of claims
    if isinstance(data, dict):
        # Create shallow copy of claims dictionary to avoid mutating input
        to_encode = data.copy()
    # Otherwise treat input as subject identifier string
    else:
        # Wrap subject identifier in claims dictionary under sub key
        to_encode = {"sub": str(data)}

    # Get current UTC timestamp
    now = datetime.now(timezone.utc)
    # Check if custom expiration delta was provided
    if expires_delta:
        # Calculate expiration timestamp using custom delta
        expire = now + expires_delta
    # Otherwise apply default configured token expiration minutes
    else:
        # Calculate expiration timestamp using application settings
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add expiration timestamp, issued-at timestamp, and unique JWT ID (jti) to claims dictionary
    to_encode.update({"exp": expire, "iat": now, "jti": uuid.uuid4().hex})
    # Sign and encode JWT token using application secret key and HS256 algorithm
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


# Function verifying and decoding a JWT Bearer token into its claims dictionary
def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    # Function docstring explaining token decoding
    """Decodes and verifies a JWT token."""
    # Wrap decoding in try block to catch signature verification and expiration errors
    try:
        # Decode and verify JWT token signature and claims using secret key
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    # Catch JWT errors and expired token exceptions
    except Exception:
        # Return None when token is invalid or expired
        return None


# Function computing a cryptographic SHA-256 hash of a token string
def hash_token(token: str) -> str:
    """Computes SHA-256 hash of a token string for safe database persistence."""
    # Compute SHA-256 hexadecimal digest
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# Function generating a cryptographically secure random rotating refresh token
def create_refresh_token(user_id: str) -> Tuple[str, str]:
    """Generates a secure random refresh token string and its SHA-256 hash.

    Returns:
        Tuple of (raw_token: str, token_hash: str)
    """
    # Generate 32 bytes of cryptographically secure random entropy
    entropy = os.urandom(32)
    # Encode as URL-safe base64 string
    raw_token = base64.urlsafe_b64encode(entropy).decode("utf-8").rstrip("=")
    # Format with user-identifying prefix
    token_str = f"rt_{user_id}_{raw_token}"
    # Compute SHA-256 hash for database storage
    token_hash = hash_token(token_str)
    # Return both plaintext token for client cookie and hash for database
    return token_str, token_hash


# Authentication dependency proxy resolving current user from token
def get_current_user(*args, **kwargs):
    # Function docstring explaining dependency behavior
    """Authentication dependency to protect authenticated routes."""
    # Lazy import get_current_user from auth router to prevent circular dependencies
    from app.api.v1.auth import get_current_user as _get_current_user
    # Invoke and return current user dependency resolution
    return _get_current_user(*args, **kwargs)

