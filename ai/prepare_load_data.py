import pandas as pd

INPUT_FILE = "data/raw/openei/hospital_load.csv"
OUTPUT_FILE = "data/load_history.csv"

# Read hospital load file
df = pd.read_csv(INPUT_FILE)

# Parse timestamp
df["timestamp"] = pd.to_datetime(
    "2004 " + df["Date/Time"].str.strip(),
    format="%Y %m/%d %H:%M:%S",
    errors="coerce"
)

# Use TOTAL facility electricity (kW)
df["load_kw"] = df["Electricity:Facility [kW](Hourly)"]


# Keep only required columns
df = df[["timestamp", "load_kw"]]

# Clean
df["load_kw"] = df["load_kw"].clip(lower=0)
df = df.dropna()

# Save
df.to_csv(OUTPUT_FILE, index=False)

print("load_history.csv created successfully")
