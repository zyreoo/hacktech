import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import time

# simulation parameters
queues_open = 3
max_queues = 6
processing_rate = 5

# passengers waiting in each queue
queues = [0 for _ in range(max_queues)]

plt.ion()
fig, ax = plt.subplots()

for step in range(100):

    # simulate flights
    flights = np.random.poisson(2)

    # passengers arriving
    passengers = flights * np.random.randint(20,40)

    # distribute passengers to queues
    for _ in range(passengers):
        idx = np.argmin(queues[:queues_open])
        queues[idx] += 1

    # process passengers
    for i in range(queues_open):
        queues[i] = max(queues[i] - processing_rate, 0)

    # open more queues if congestion
    total_queue = sum(queues[:queues_open])

    if total_queue > 200 and queues_open < max_queues:
        queues_open += 1

    if total_queue < 50 and queues_open > 2:
        queues_open -= 1

    # visualization
    ax.clear()

    for i in range(queues_open):

        for j in range(queues[i]):

            rect = patches.Rectangle(
                (i, j),
                0.8,
                0.8,
                color="skyblue"
            )

            ax.add_patch(rect)

    ax.set_xlim(0, max_queues)
    ax.set_ylim(0, 100)

    ax.set_title(
        f"Flights: {flights} | Passengers arriving: {passengers} | Open queues: {queues_open}"
    )

    ax.set_xlabel("Security lanes")
    ax.set_ylabel("Passengers waiting")

    plt.pause(0.4)
    time.sleep(0.2)