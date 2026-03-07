import pandas as pd
import time
import os
import random

# --- PARAMETRI ---
max_queues = 10           # maxim cozi
min_queues = 2            # minim cozi deschise
current_queues = 3
processing_rate = 5        # pasageri procesați per coadă per pas
OPEN_DELAY = 5             # delay simulare deschidere coadă
CLOSE_DELAY = 5            # delay simulare închidere coadă
queues = [0 for _ in range(max_queues)]
pending_openings = []
pending_closings = []

# --- CITIRE CSV ---
data = pd.read_csv("airport_flow_data.csv")

# convertim coloana 'time' în datetime
data['time'] = pd.to_datetime(data['time'])

# creăm coloana integer time_step (minute de la început)
data['time_step'] = ((data['time'] - data['time'].iloc[0]).dt.total_seconds() // 60).astype(int)

# --- SIMULARE ---
for _, row in data.iterrows():

    time_step = row['time_step']           # integer minutes
    flights = row['flights_departing']
    passengers = row['passengers_arriving']

    # adăugăm variație random pentru realism
    passengers += random.randint(-5, 5)
    passengers = max(passengers, 0)

    # --- distribuim pasagerii la coada cu cei mai puțini oameni ---
    for _ in range(passengers):
        idx_shortest = min(range(current_queues), key=lambda i: queues[i])
        queues[idx_shortest] += 1

    # --- procesăm pasagerii ---
    for i in range(current_queues):
        queues[i] = max(queues[i] - processing_rate, 0)

    total_queue = sum(queues[:current_queues])

    # --- AI recomandare ---
    if total_queue > 150:
        suggested_queues = min(max_queues, current_queues + 1)
    elif total_queue < 50:
        suggested_queues = max(min_queues, current_queues - 1)
    else:
        suggested_queues = current_queues

    # --- schedule openings ---
    if suggested_queues > current_queues and current_queues < max_queues:
        if len(pending_openings) == 0:
            pending_openings.append(time_step + OPEN_DELAY)

    # --- schedule closings ---
    if suggested_queues < current_queues and current_queues > min_queues:
        if len(pending_closings) == 0:
            pending_closings.append(time_step + CLOSE_DELAY)

    # --- execute openings ---
    for open_time in pending_openings[:]:
        if time_step >= open_time and current_queues < max_queues:
            current_queues += 1
            pending_openings.remove(open_time)

    # --- execute closings ---
    for close_time in pending_closings[:]:
        if time_step >= close_time and current_queues > min_queues:
            current_queues -= 1
            pending_closings.remove(close_time)

    # --- curățăm terminalul ---
    os.system('cls' if os.name == 'nt' else 'clear')

    # --- afișare simulare ---
    print("AIRPORT SECURITY FLOW SIMULATION\n")
    print(f"Time step: {time_step}")
    print(f"Flights arriving: {flights}")
    print(f"Passengers arriving: {passengers}\n")

    print(f"Current queues open: {current_queues}")
    print(f"Suggested queues: {suggested_queues}")

    if pending_openings:
        print(f"Queue opening in: {pending_openings[0] - time_step} steps")
    if pending_closings:
        print(f"Queue closing in: {pending_closings[0] - time_step} steps")
    if not pending_openings and not pending_closings:
        print("No pending changes\n")

    print("\nSECURITY QUEUES\n")
    for i in range(max_queues):
        if i < current_queues:
            blocks = "🟦" * (queues[i] // 5)
            print(f"Lane {i+1}: {blocks}")
        else:
            print(f"Lane {i+1}: (closed)")

    # simulare timp real pentru demo
    time.sleep(1)