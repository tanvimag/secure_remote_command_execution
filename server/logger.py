from datetime import datetime
import os
import threading

# ── Resolve log directory relative to this file ──────────────────────────────
# This ensures logs are always saved correctly regardless of where the program is run
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR  = os.path.join(BASE_DIR, "..", "logs")

# Lock to ensure thread-safe file writing (important in multi-threaded server)
_log_lock = threading.Lock()


def _ensure_dir():
    # Create logs directory if it doesn't exist
    # 'exist_ok=True' prevents error if folder already exists
    os.makedirs(LOG_DIR, exist_ok=True)


def log_event(ip: str, username: str, action: str):
    """Append a structured event to server.log (thread-safe)."""
    _ensure_dir()

    # Generate timestamp for each log entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Structured log format → useful for debugging and auditing
    line = f"{timestamp} | {ip} | {username} | {action}\n"

    # Path for main server log file
    log_path = os.path.join(LOG_DIR, "server.log")

    # Lock ensures multiple threads don’t write simultaneously (avoids corruption)
    with _log_lock:
        with open(log_path, "a") as f:  # 'a' → append mode
            f.write(line)


def log_command_history(username: str, command: str):
    """Append command to per-user history file (thread-safe)."""
    _ensure_dir()

    # Sanitize username to prevent invalid or unsafe file names
    # Only allow letters, numbers, '_' and '-'
    safe_name = "".join(c for c in username if c.isalnum() or c in ("_", "-"))

    # Each user gets a separate history log file
    file_path = os.path.join(LOG_DIR, f"{safe_name}_history.log")

    # Timestamp for each command
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Thread-safe writing of command history
    with _log_lock:
        with open(file_path, "a") as f:
            f.write(f"{timestamp} | {command}\n")
