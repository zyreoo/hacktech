import random
import time
import os

# simulation parameters
current_queues = 3
max_queues = 10
processing_rate = 5

queues = [0 for _ in range(max_queues)]

time_step = 0

# queue opening delay system
pending_openings = []
OPEN_DELAY = 5   # simulated delay (represents ~30 min)

while True:

    time_step += 1

    # --- simulate flights ---
    flights = random.randint(0,3)

    # simulate passengers arriving
    passengers = flights * random.randint(20,40)

    # distribute passengers to shortest queue
    for _ in range(passengers):
        idx = min(range(current_queues), key=lambda i: queues[i])
        queues[idx] += 1

    # --- process passengers ---
    for i in range(current_queues):
        queues[i] = max(queues[i] - processing_rate, 0)

    total_queue = sum(queues[:current_queues])

    # --- AI recommendation logic ---
    if total_queue > 150:
        suggested_queues = min(max_queues, current_queues + 1)

    elif total_queue < 50:
        suggested_queues = max(2, current_queues - 1)

    else:
        suggested_queues = current_queues

    # --- schedule queue opening (avoid duplicates) ---
    if suggested_queues > current_queues and current_queues < max_queues:

        if len(pending_openings) == 0:
            pending_openings.append(time_step + OPEN_DELAY)

    # --- open queues when delay passes ---
    for open_time in pending_openings[:]:

        if time_step >= open_time and current_queues < max_queues:
            current_queues += 1
            pending_openings.remove(open_time)

    # --- clear terminal ---
    os.system('cls' if os.name == 'nt' else 'clear')

    print("AIRPORT SECURITY FLOW SIMULATION\n")

    print(f"Time step: {time_step}")
    print(f"Flights arriving: {flights}")
    print(f"Passengers arriving: {passengers}")

    print(f"\nCurrent queues open: {current_queues}")
    print(f"Suggested queues: {suggested_queues}")

    if pending_openings:
        print(f"Queue opening in: {pending_openings[0] - time_step} steps")
    else:
        print("No pending queue openings")

    print("\nSECURITY QUEUES\n")

    # --- draw queues ---
    for i in range(current_queues):

        blocks = "🟦" * (queues[i] // 5)

        print(f"Lane {i+1}: {blocks}")

    time.sleep(1)