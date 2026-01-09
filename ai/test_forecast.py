import joblib
import pandas as pd

model = joblib.load("ai/models/load_forecaster.pkl")

# Example future conditions
test_data = pd.DataFrame({
    "solar_kw": [0, 20, 80],
    "hour": [2, 12, 18],
    "dayofweek": [1, 1, 1]
})

pred = model.predict(test_data)
print(pred)
