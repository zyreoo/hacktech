import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor

# 1️⃣ Load dataset
data = pd.read_csv("airport_flow_data.csv")

# 2️⃣ Estimate security capacity
# assume 1 lane processes 50 passengers every 5 minutes
data["capacity"] = data["security_lanes_open"] * 50

# 3️⃣ Compute current queue time (minutes)
data["queue_time"] = (data["passengers_arriving"] / data["capacity"]) * 5

# 4️⃣ Prepare ML dataset
features = ["flights_departing", "passengers_arriving", "security_lanes_open"]
target = "queue_time"

X = data[features]
y = data[target]

# 5️⃣ Train Random Forest model
model = RandomForestRegressor(n_estimators=100)
model.fit(X, y)

# 6️⃣ Predict queue times
data["predicted_queue"] = model.predict(X)

# 7️⃣ Generate recommendations
def recommend(queue):
    if queue > 30:
        return "Open 2 more lanes"
    elif queue > 20:
        return "Open 1 more lane"
    else:
        return "No action"

data["recommendation"] = data["predicted_queue"].apply(recommend)

# 8️⃣ Print some results
print(data[["time","predicted_queue","recommendation"]].head(15))

# 9️⃣ Plot results (nice for demo)
plt.figure(figsize=(12,5))
plt.plot(data["queue_time"], label="Actual Queue")
plt.plot(data["predicted_queue"], label="Predicted Queue", linestyle="--")
plt.xlabel("Time index")
plt.ylabel("Queue time (minutes)")
plt.title("Airport Security Queue Prediction")
plt.legend()
plt.show()