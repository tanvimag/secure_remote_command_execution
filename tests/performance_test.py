import socket
import ssl
import time
import threading
import json
import statistics
import sys
import os

# Server configuration for testing
HOST       = '127.0.0.1'
PORT       = 5000
NUM_CLIENTS = 10          # number of concurrent clients (load level)
USERNAME   = "admin"
PASSWORD   = "admin123"
COMMAND    = "whoami"

# Shared result storage (VERY IMPORTANT for multithreading)
# Each thread stores its result here safely using a lock
results      = []
results_lock = threading.Lock()


def client_task(client_id: int):
    """
    Each thread simulates one client:
    1. Connects securely using SSL
    2. Authenticates
    3. Sends command and measures response time
    4. Stores result in shared list
    """

    # SSL context setup (secure connection)
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode    = ssl.CERT_NONE

    # Measure connection start time
    connect_start = time.perf_counter()

    try:
        sock   = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client = context.wrap_socket(sock, server_hostname=HOST)

        client.settimeout(15)  # avoid hanging
        client.connect((HOST, PORT))

        # Measure connection time
        connect_end = time.perf_counter()
        connect_time = connect_end - connect_start

        # ── AUTHENTICATION ───────────────────────────────────────────────────
        client.recv(1024)
        client.send(USERNAME.encode())

        client.recv(1024)
        client.send(PASSWORD.encode())

        auth_response = client.recv(1024).decode().strip()

        # If authentication fails, store result and exit
        if "AUTH SUCCESS" not in auth_response:
            print(f"[Client {client_id}] Auth failed: {auth_response}")
            with results_lock:
                results.append({
                    "client_id":    client_id,
                    "status":       "AUTH_FAILED",
                    "response_ms":  None,
                    "connect_ms":   round(connect_time * 1000, 3)
                })
            return

        # ── COMMAND EXECUTION + TIMING ───────────────────────────────────────
        request = json.dumps({"type": "command", "data": COMMAND}).encode()

        # Measure round-trip time (send → receive)
        t_send = time.perf_counter()
        client.send(request)
        response = client.recv(4096)
        t_recv = time.perf_counter()

        if not response:
            raise RuntimeError("Empty response from server")

        # Convert timing to milliseconds
        response_ms = round((t_recv - t_send) * 1000, 3)
        connect_ms  = round(connect_time * 1000, 3)

        print(f"[Client {client_id:02d}] ✓  Response: {response_ms:7.3f} ms  |  Connect: {connect_ms:7.3f} ms")

        # Store successful result (thread-safe)
        with results_lock:
            results.append({
                "client_id":   client_id,
                "status":      "OK",
                "response_ms": response_ms,
                "connect_ms":  connect_ms
            })

        # Graceful exit from server
        client.send(json.dumps({"type": "command", "data": "exit"}).encode())
        client.recv(1024)

    # ── Error handling (IMPORTANT FIX: no silent errors) ─────────────────────
    except socket.timeout:
        print(f"[Client {client_id}] TIMEOUT")
        with results_lock:
            results.append({"client_id": client_id, "status": "TIMEOUT", "response_ms": None, "connect_ms": None})

    except ConnectionRefusedError:
        print(f"[Client {client_id}] CONNECTION REFUSED — is server running?")
        with results_lock:
            results.append({"client_id": client_id, "status": "REFUSED", "response_ms": None, "connect_ms": None})

    except Exception as e:
        # Explicit error logging (important improvement over silent failure)
        print(f"[Client {client_id}] ERROR: {type(e).__name__}: {e}")
        with results_lock:
            results.append({"client_id": client_id, "status": f"ERROR:{type(e).__name__}", "response_ms": None, "connect_ms": None})

    finally:
        try:
            client.close()
        except Exception:
            pass


def print_stats(response_times: list):
    """Print performance summary statistics."""

    # If no successful responses
    if not response_times:
        print("\n[!] No successful measurements to analyse.")
        return

    # Key performance metrics
    print("\n" + "═" * 55)
    print("  PERFORMANCE RESULTS")
    print("═" * 55)
    print(f"  Clients tested      : {NUM_CLIENTS}")
    print(f"  Successful          : {len(response_times)}")
    print(f"  Min latency         : {min(response_times):.3f} ms")
    print(f"  Max latency         : {max(response_times):.3f} ms")
    print(f"  Mean latency        : {statistics.mean(response_times):.3f} ms")
    print(f"  Median latency      : {statistics.median(response_times):.3f} ms")

    # Standard deviation shows variability in performance
    if len(response_times) > 1:
        print(f"  Std deviation       : {statistics.stdev(response_times):.3f} ms")

    print("═" * 55)


def save_graph(response_times: list, total_elapsed: float):
    """Generate and save performance graph."""
    try:
        import matplotlib
        matplotlib.use("Agg")   # allows graph generation without display
        import matplotlib.pyplot as plt
        import numpy as np

        # Create two graphs: bar chart + histogram
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        fig.suptitle(f"Secure Remote Command — Performance ({NUM_CLIENTS} clients)", fontsize=13, fontweight="bold")

        # ── Bar chart: response time per client ──────────────────────────────
        client_ids = list(range(1, len(response_times) + 1))
        axes[0].bar(client_ids, response_times)
        axes[0].set_xlabel("Client ID")
        axes[0].set_ylabel("Response Time (ms)")
        axes[0].set_title("Per-Client Response Time")

        # ── Histogram: latency distribution ──────────────────────────────────
        axes[1].hist(response_times, bins=max(3, len(response_times) // 2))
        axes[1].set_xlabel("Response Time (ms)")
        axes[1].set_ylabel("Frequency")
        axes[1].set_title("Latency Distribution")

        # Save graph to file
        out_dir  = os.path.dirname(os.path.abspath(__file__))
        out_path = os.path.join(out_dir, "perf_results.png")
        plt.savefig(out_path)
        plt.close()

        print(f"\n[✓] Graph saved → {out_path}")

    except ImportError:
        print("\n[!] matplotlib not installed.")

    except Exception as e:
        print(f"\n[!] Graph generation failed: {e}")


# ── MAIN EXECUTION ───────────────────────────────────────────────────────────
if __name__ == "__main__":

    print(f"[*] Launching {NUM_CLIENTS} concurrent clients → {HOST}:{PORT}")

    threads     = []
    wall_start  = time.perf_counter()  # start total execution time

    # Create multiple client threads
    for i in range(1, NUM_CLIENTS + 1):
        t = threading.Thread(target=client_task, args=(i,), daemon=True)
        t.start()
        threads.append(t)

    # Wait for all threads to finish
    for t in threads:
        t.join()

    wall_end      = time.perf_counter()
    total_elapsed = wall_end - wall_start

    # Extract only successful response times
    successful     = [r for r in results if r["status"] == "OK" and r["response_ms"] is not None]
    response_times = [r["response_ms"] for r in successful]

    print(f"\n[*] All threads finished. Total time: {total_elapsed:.4f} sec")

    # Print performance summary
    print_stats(response_times)

    # Throughput = requests per second
    if successful:
        throughput = len(successful) / total_elapsed
        print(f"  Throughput          : {throughput:.2f} requests/sec")

    # Generate graph
    save_graph(response_times, total_elapsed)
