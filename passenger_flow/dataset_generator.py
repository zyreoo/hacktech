import pandas as pd
import numpy as np

np.random.seed(42)

times = pd.date_range("2026-03-06 06:00", periods=120, freq="5min")

data = pd.DataFrame({
    "time": times,
    "flights_departing": np.random.randint(0, 5, size=len(times)),
    "security_lanes_open": np.random.randint(2, 5, size=len(times))
})

# estimate passengers arriving (approx 80–180 per flight)
data["passengers_arriving"] = data["flights_departing"] * np.random.randint(80, 180, size=len(times))

data["capacity"] = data["security_lanes_open"] * 50
data["queue_time"] = (data["passengers_arriving"] / data["capacity"]) * 5

print(data.head())

data.to_csv("airport_flow_data.csv", index=False)