import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib

load_df = pd.read_csv("data/load_history.csv", parse_dates=["timestamp"])
solar_df = pd.read_csv("data/solar_history.csv", parse_dates=["timestamp"])

# Force hourly alignment (CRITICAL FIX)
load_df["timestamp"] = load_df["timestamp"].dt.floor("H")
solar_df["timestamp"] = solar_df["timestamp"].dt.floor("H")

# Merge after alignment
df = pd.merge(load_df, solar_df, on="timestamp", how="inner")

print("Merged samples:", len(df))


# Feature engineering (safe + minimal)
df["hour"] = df["timestamp"].dt.hour
df["dayofweek"] = df["timestamp"].dt.dayofweek

X = df[["solar_kw", "hour", "dayofweek"]]
y = df["load_kw"]

# Train / test split (time-safe)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, shuffle=False, test_size=0.2
)

# Train LightGBM
model = lgb.LGBMRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=6,
    random_state=42
)

model.fit(X_train, y_train)

# Evaluate
pred = model.predict(X_test)
mae = mean_absolute_error(y_test, pred)
print("MAE (kW):", round(mae, 2))

# Save model
joblib.dump(model, "ai/models/load_forecaster.pkl")
print("Model saved to ai/models/load_forecaster.pkl")


