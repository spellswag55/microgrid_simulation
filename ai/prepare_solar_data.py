import pandas as pd

PV_CAPACITY_KW = 150
PANEL_EFFICIENCY = 0.20
SYSTEM_LOSS = 0.15

INPUT_FILE = "data/raw/solar_nsrdb.csv"
OUTPUT_FILE = "data/solar_history.csv"

# Read NSRDB file (skip metadata rows)
df = pd.read_csv(
    INPUT_FILE,
    skiprows=2
)

# Build timestamp from actual columns
df["timestamp"] = pd.to_datetime(
    df[["Year", "Month", "Day", "Hour", "Minute"]]
)

df["timestamp"] = df["timestamp"].apply(lambda t: t.replace(year=2004))


# Convert GHI (W/m^2) to solar power (kW)
df["solar_kw"] = (
    df["GHI"] * PANEL_EFFICIENCY * (1 - SYSTEM_LOSS) * PV_CAPACITY_KW / 1000
)

# Clean values
df["solar_kw"] = df["solar_kw"].clip(lower=0)

# Keep only required columns
df[["timestamp", "solar_kw"]].to_csv(OUTPUT_FILE, index=False)

print("solar_history.csv created successfully")
