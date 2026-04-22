import subprocess
import sys

# ── Platform-aware command handling ──────────────────────────────────────────
# Detect OS to adjust commands (Windows vs Linux/Unix)
IS_WINDOWS = sys.platform.startswith("win")

# Command configuration dictionary
# Each command defines:
# - actual system command to execute
# - allowed roles (None = all users)
# - description (used in help)
COMMAND_MAP = {
    "whoami": {
        "cmd": ["whoami"],
        "roles": None,          # accessible to all users
        "description": "Show current OS user"
    },
    "date": {
        # Platform-specific command selection
        "cmd": ["cmd", "/c", "date /t"] if IS_WINDOWS else ["date"],
        "roles": None,
        "description": "Show current date"
    },
    "dir": {
        # Windows uses 'dir', Linux uses 'ls -la'
        "cmd": ["cmd", "/c", "dir"] if IS_WINDOWS else ["ls", "-la"],
        "roles": ["admin"],     # restricted to admin users
        "description": "List directory (admin only)"
    },
    "uptime": {
        "cmd": ["cmd", "/c", "net statistics workstation"] if IS_WINDOWS else ["uptime"],
        "roles": ["admin"],
        "description": "Show system uptime (admin only)"
    },
    "ipconfig": {
        "cmd": ["ipconfig"] if IS_WINDOWS else ["ip", "addr"],
        "roles": ["admin"],
        "description": "Show network info (admin only)"
    },
}


def execute_command(command: str, role: str) -> str:
    # Normalize command input (remove spaces, case-insensitive)
    command = command.strip().lower()

    # ── Built-in HELP command ────────────────────────────────────────────────
    if command == "help":
        lines = ["Available commands:"]

        # Show only commands allowed for the current role
        for name, info in COMMAND_MAP.items():
            allowed = info["roles"] or ["admin", "user"]
            if role in allowed or info["roles"] is None:
                lines.append(f"  {name:<12} — {info['description']}")

        lines.append("  exit         — Close session")
        return "\n".join(lines)

    # ── Command lookup ───────────────────────────────────────────────────────
    entry = COMMAND_MAP.get(command)

    # If command not found in predefined list
    if entry is None:
        return f"ERROR: Unknown command '{command}'. Type 'help' for list."

    # ── Role-based access control ────────────────────────────────────────────
    allowed_roles = entry["roles"]

    # If command is restricted and user role not allowed
    if allowed_roles is not None and role not in allowed_roles:
        return f"ERROR: Command '{command}' requires role: {allowed_roles}. Your role: {role}"

    # ── Execute system command safely ────────────────────────────────────────
    try:
        # subprocess executes system-level commands
        result = subprocess.check_output(
            entry["cmd"],
            stderr=subprocess.STDOUT,   # capture error output
            text=True,                  # return string instead of bytes
            timeout=10                  # prevent hanging commands
        )

        # Return clean output
        return result.strip() if result.strip() else "[No Output]"

    # ── Error handling ───────────────────────────────────────────────────────
    except subprocess.TimeoutExpired:
        # If command takes too long
        return "ERROR: Command timed out"

    except subprocess.CalledProcessError as e:
        # If command execution fails
        return f"ERROR: {e.output.strip()}"

    except FileNotFoundError:
        # If command not available on system
        return f"ERROR: Command binary not found on this system"

    except Exception as e:
        # Catch-all for unexpected errors
        return f"ERROR: {str(e)}"