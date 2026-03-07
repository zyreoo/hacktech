import random
import time
import os

queues_open = 3
max_queues = 6
processing_rate = 5

queues = [0] * max_queues
time_step = 0

while True:

    time_step += 1

    # simulate flights
    flights = random.randint(0,3)

    # simulate passengers arriving
    passengers = flights * random.randint(20,40)

    # distribute passengers
    for _ in range(passengers):
        idx = min(range(queues_open), key=lambda i: queues[i])
        queues[idx] += 1

    # process passengers
    for i in range(queues_open):
        queues[i] = max(queues[i] - processing_rate, 0)

    total_queue = sum(queues[:queues_open])

    # queue management
    if total_queue > 120 and queues_open < max_queues:
        queues_open += 1

    if total_queue < 40 and queues_open > 2:
        queues_open -= 1

    # clear screen
    os.system('cls' if os.name == 'nt' else 'clear')

    # header info
    print("AIRPORT SECURITY SIMULATION\n")
    print(f"Time step: {time_step}")
    print(f"Flights arriving: {flights}")
    print(f"Passengers arriving: {passengers}")
    print(f"Queues open: {queues_open}\n")

    print("SECURITY QUEUES:\n")

    # draw queues
    for i in range(queues_open):

        blocks = "🟦" * (queues[i] // 5)

        print(f"Lane {i+1}: {blocks}")

    time.sleep(1)