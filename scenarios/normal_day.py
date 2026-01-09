import pandas as pd

def load_profiles():
    load = pd.read_csv("data/load_history.csv")
    solar = pd.read_csv("data/solar_history.csv")

    # Return as time series (kW)
    return load["load_kw"].values, solar["solar_kw"].values
