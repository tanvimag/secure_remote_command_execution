import hashlib

# In production systems, credentials should be stored securely in a database
# or environment-based configuration. Here, users are hardcoded for simplicity.
# Passwords are NOT stored in plain text — they are hashed using SHA-256.
USERS = {
    "admin": {
        "password": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin"
    },
    "user": {
        "password": hashlib.sha256("user123".encode()).hexdigest(),
        "role": "user"
    }
}


def hash_password(password: str) -> str:
    # Convert password into a secure hash (one-way function)
    # Important: original password cannot be retrieved from hash
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(username: str, password: str):
    """
    Returns (True, role) on success, (False, None) on failure.
    Uses constant-time comparison to prevent timing attacks.
    """
    import hmac

    # Fetch user details from USERS dictionary
    user = USERS.get(username)

    # If username not found → authentication fails
    if not user:
        return False, None

    # Stored hashed password
    expected = user["password"]

    # Hash the entered password for comparison
    provided = hash_password(password)

    # Use secure comparison to avoid timing attacks
    # (prevents attackers from guessing passwords based on response time)
    if hmac.compare_digest(expected, provided):
        return True, user["role"]

    # Password mismatch
    return False, None
