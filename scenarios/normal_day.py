import pandas as pd

def load_profiles():
    load = pd.read_csv("data/load_profile.csv")
    solar = pd.read_csv("data/solar_profile.csv")
    return load, solar
