import subprocess
import time
import signal
import sys

# List to hold the subprocesses
processes = []


def signal_handler(sig, frame):
    print("Main thread received interrupt signal. Terminating subprocesses...")
    for proc in processes:
        proc.terminate()  # Send SIGTERM
        try:
            proc.wait(timeout=5)  # Wait for the process to terminate
        except subprocess.TimeoutExpired:
            proc.kill()  # Force kill if not terminated
    sys.exit(0)


if __name__ == "__main__":
    import sys

    num_clients = int(sys.argv[1])
    if not num_clients:
        num_clients = 10

    # Register the signal handler for KeyboardInterrupt (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Start 10 long-running subprocesses
        for i in range(num_clients):
            proc = subprocess.Popen(
                ["python", "-m", "cowboy.task_client.runtest_client", "hearbeat.txt", "1"],
                stdout=None,
                stderr=None,
            )
            processes.append(proc)
            print(f"Started subprocess {i} with PID {proc.pid}")

        # Keep the main thread running to maintain the relationship
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        signal_handler(None, None)
