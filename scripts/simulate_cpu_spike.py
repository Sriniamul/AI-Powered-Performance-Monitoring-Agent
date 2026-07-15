import time

print("Starting CPU spike simulator. Press Ctrl+C to stop.")
while True:
    end = time.time() + 1
    while time.time() < end:
        _ = 12345 * 67890
