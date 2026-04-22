import socket
import ssl
import json
import getpass

# Server connection details
HOST = '172.16.7.166'  
   # Localhost (client connects to same machine)
PORT = 5000          # Must match server port


def recv_line(sock, bufsize=4096) -> str:
    """Receive a complete server response, decode and clean it."""
    # Receives raw bytes and converts them into readable string
    data = sock.recv(bufsize)
    return data.decode(errors="replace").strip()


def start_client():
    # Create SSL context for secure communication
    context = ssl.create_default_context()

    # Disable hostname check & certificate verification (only for lab/testing)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # self-signed cert accepted

    # Create TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Wrap socket with SSL (secure connection)
        client = context.wrap_socket(sock, server_hostname=HOST)

        # Connect to server
        client.connect((HOST, PORT))

    except ConnectionRefusedError:
        print("[!] Cannot connect — is the server running?")
        return

    except ssl.SSLError as e:
        print(f"[!] SSL error: {e}")
        return

    try:
        # ── AUTHENTICATION ───────────────────────────────────────────────────
        # Receive username prompt from server
        prompt = recv_line(client)          # "USERNAME: "
        print(prompt, end=" ", flush=True)
        username = input()
        client.send(username.encode())     # send username

        # Receive password prompt
        prompt = recv_line(client)          # "PASSWORD: "
        print(prompt, end=" ", flush=True)

        # getpass hides password input (security feature)
        password = getpass.getpass("")
        client.send(password.encode())     # send password

        # Receive authentication result separately
        result = recv_line(client)
        print(f"\n[AUTH]: {result}")

        # Stop if authentication failed
        if "AUTH SUCCESS" not in result:
            return

        # ── COMMAND LOOP ─────────────────────────────────────────────────────
        print("\nType 'help' to list commands. Type 'exit' to quit.\n")

        while True:
            try:
                # Take command input from user
                command = input("cmd> ").strip()

            except EOFError:
                break

            # Ignore empty commands
            if not command:
                continue

            # Create JSON request for server
            request = {"type": "command", "data": command}

            try:
                # Send request to server
                client.send(json.dumps(request).encode())

                # Receive server response
                response = client.recv(4096)

                if not response:
                    print("[!] Server closed connection")
                    break

                # Display server output
                print(f"[SERVER]:\n{response.decode(errors='replace')}\n")

            except ssl.SSLError as e:
                print(f"[!] SSL error: {e}")
                break

            except ConnectionResetError:
                print("[!] Connection reset by server")
                break

            except Exception as e:
                print(f"[!] Error: {e}")
                break

            # Exit command terminates session
            if command.lower() == "exit":
                break

    finally:
        # Always close connection properly
        try:
            client.close()
        except Exception:
            pass

        print("[*] Disconnected.")


# Entry point of client program
if __name__ == "__main__":
    start_client()
