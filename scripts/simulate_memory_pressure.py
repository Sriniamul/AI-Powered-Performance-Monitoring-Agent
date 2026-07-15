import time

payload = []
print("Starting memory pressure simulator. Press Ctrl+C to stop.")
while True:
    payload.append(bytearray(5 * 1024 * 1024))
    print(f"Allocated chunks: {len(payload)}")
    time.sleep(1)
