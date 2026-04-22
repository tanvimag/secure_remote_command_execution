import socket
import ssl
import json
import threading
import traceback
import os

from auth import authenticate
from command_handler import execute_command
from logger import log_event, log_command_history

# Server configuration
HOST = '0.0.0.0'   # Listen on all available network interfaces
PORT = 5000        # Port number for incoming connections
BUFFER_SIZE = 4096 # Max size of data received per request
MAX_ATTEMPTS = 3   # Max login attempts before blocking IP

# Dictionary to track failed login attempts per IP
failed_attempts = {}

# Lock to ensure thread-safe access to shared data (failed_attempts)
lock = threading.Lock()

# Paths for SSL certificate and private key
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CERT_FILE  = os.path.join(BASE_DIR, "..", "certs", "server.crt")
KEY_FILE   = os.path.join(BASE_DIR, "..", "certs", "server.key")


def send_all(sock, data: bytes):
    """Reliably send all bytes — avoids partial sends on large payloads."""
    total = 0
    # Loop until all bytes are sent (important for large responses)
    while total < len(data):
        sent = sock.send(data[total:])
        if sent == 0:
            # If nothing is sent, connection is broken
            raise RuntimeError("Socket connection broken")
        total += sent


def handle_client(client_socket, addr):
    # Extract client IP and initialize user info
    ip       = addr[0]
    username = "unknown"
    role     = None

    print(f"[+] Connected: {addr}")

    try:
        # Set timeout to avoid hanging connections
        client_socket.settimeout(30)

        # ── BLOCK CHECK ───────────────────────────────────────────────────────
        # Prevent brute-force login attempts by blocking IP after max failures
        with lock:
            if failed_attempts.get(ip, 0) >= MAX_ATTEMPTS:
                send_all(client_socket, b"BLOCKED: Too many failed attempts\n")
                log_event(ip, "unknown", "BLOCKED")
                print(f"[!] Blocked IP: {ip}")
                return

        # ── AUTHENTICATION ───────────────────────────────────────────────────
        # Ask client for username and password
        send_all(client_socket, b"USERNAME: ")
        username = client_socket.recv(1024).decode().strip()

        send_all(client_socket, b"PASSWORD: ")
        password = client_socket.recv(1024).decode().strip()

        # Initialize attempt counter for this IP
        with lock:
            failed_attempts.setdefault(ip, 0)

        # Validate credentials using external auth module
        auth_success, role = authenticate(username, password)

        if not auth_success:
            # Increment failed attempts safely
            with lock:
                failed_attempts[ip] += 1
                attempts = failed_attempts[ip]

            # Block user if attempts exceed limit
            if attempts >= MAX_ATTEMPTS:
                send_all(client_socket, b"BLOCKED: Too many failed attempts\n")
                log_event(ip, "unknown", "BLOCKED")
                print(f"[!] {ip} blocked after {attempts} attempts")
            else:
                send_all(client_socket, b"AUTH FAILED\n")
                log_event(ip, username, "LOGIN FAILED")
            return

        # ── LOGIN SUCCESS ─────────────────────────────────────────────────────
        # Reset failed attempts after successful login
        with lock:
            failed_attempts[ip] = 0

        send_all(client_socket, b"AUTH SUCCESS\n")
        log_event(ip, username, "LOGIN SUCCESS")
        print(f"[+] {username} logged in as [{role}]")

        # ── COMMAND LOOP ──────────────────────────────────────────────────────
        # Continuously receive and process client commands
        while True:
            data = client_socket.recv(BUFFER_SIZE)

            # If no data received → client disconnected
            if not data:
                break

            try:
                # Expecting JSON request from client
                request = json.loads(data.decode())

                # Validate request structure
                if request.get("type") != "command":
                    raise ValueError("Bad type")

                command = request.get("data", "").strip()
                if not command or not isinstance(command, str):
                    raise ValueError("Empty command")

            except (json.JSONDecodeError, ValueError) as e:
                # Handle malformed requests safely
                send_all(client_socket, f"ERROR: Invalid request — {e}\n".encode())
                continue

            # Log command execution
            print(f"[{username}@{ip}] CMD: {command}")
            log_event(ip, username, f"COMMAND: {command}")
            log_command_history(username, command)

            # Exit condition for client session
            if command.lower() == "exit":
                send_all(client_socket, b"Session closed\n")
                break

            # Execute command based on user role
            output = execute_command(command, role)

            # Handle empty output
            if not output:
                output = "[No Output]"

            # Send command result back to client
            send_all(client_socket, output.encode())

    except socket.timeout:
        # Handle idle clients
        print(f"[!] Timeout: {addr}")
        try:
            send_all(client_socket, b"ERROR: Session timed out\n")
        except Exception:
            pass

    except ssl.SSLError as e:
        # Handle SSL-specific errors
        print(f"[!] SSL error from {addr}: {e}")

    except Exception:
        # Catch unexpected errors for debugging
        traceback.print_exc()

    finally:
        # Always log disconnection and clean up socket
        log_event(ip, username, "DISCONNECTED")
        try:
            client_socket.close()
        except Exception:
            pass
        print(f"[-] Closed: {addr}")


def start_server():
    # Create SSL context for secure communication (TLS)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT_FILE, KEY_FILE)

    # Enforce minimum TLS version (security best practice)
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    # Create TCP socket
    raw_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Allow reuse of address (avoids "address already in use" error)
    raw_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind server to host and port
    raw_server.bind((HOST, PORT))

    # Start listening for incoming connections (max 10 queued clients)
    raw_server.listen(10)

    print(f"[+] Secure server running on {HOST}:{PORT}")
    print(f"[+] TLS cert : {os.path.abspath(CERT_FILE)}")

    # Main server loop
    while True:
        try:
            # Accept incoming client connection
            client_socket, addr = raw_server.accept()
        except KeyboardInterrupt:
            print("\n[!] Server shutting down")
            break

        try:
            # Wrap socket with SSL for secure communication
            secure_socket = context.wrap_socket(client_socket, server_side=True)
        except ssl.SSLError as e:
            print(f"[!] SSL handshake failed from {addr}: {e}")
            client_socket.close()
            continue

        # Handle each client in a separate thread (concurrent handling)
        thread = threading.Thread(
            target=handle_client,
            args=(secure_socket, addr),
            daemon=True
        )
        thread.start()

        # Show active client threads (excluding main thread)
        print(f"[~] Active threads: {threading.active_count() - 1}")


# Entry point of the program
if __name__ == "__main__":
    start_server()
