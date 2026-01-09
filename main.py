from components.solar import SolarPV
from components.battery import Battery
from components.generator import DieselGenerator
from controller.microgrid_controller import MicrogridController
from simulation.simulator import MicrogridSimulator
from scenarios.normal_day import load_profiles
from ai.forecaster import LoadForecaster

forecaster = LoadForecaster("ai/models/load_forecaster.pkl")


load, solar_profile = load_profiles()

# -------------------------------------------------------------------
# ASSET SIZING (SCALED UP TO MATCH HOSPITAL LOAD PROFILE)
# Your load profile is on the order of ~800–1000+ kW.
# The original assets (130 kW PV + 100 kW gen + 50 kW battery) were
# physically incapable of serving that demand.
# -------------------------------------------------------------------
SOLAR_PROFILE_SCALE = 6.0      # scales the *available* solar profile (represents more PV panels)
SOLAR_MAX_POWER_KW = 900       # PV inverter/nameplate cap
GENERATOR_MAX_POWER_KW = 2000  # must be >= peak load to prevent blackout
BATTERY_CAPACITY_KWH = 8000    # energy storage
BATTERY_MAX_DISCHARGE_KW = 800 # power capability
BATTERY_MAX_CHARGE_KW = 800

solar_profile = solar_profile * SOLAR_PROFILE_SCALE

# For fast runs while tuning sizing. Increase (or set to None) for full dataset.
RUN_HORIZON = 7 * 24  # one week
if RUN_HORIZON is not None:
	load = load[:RUN_HORIZON]
	solar_profile = solar_profile[:RUN_HORIZON]


def build_sim():
	solar = SolarPV(max_power_kw=SOLAR_MAX_POWER_KW)
	battery = Battery(
		capacity_kwh=BATTERY_CAPACITY_KWH,
		soc_init=0.5,
		max_charge_kw=BATTERY_MAX_CHARGE_KW,
		max_discharge_kw=BATTERY_MAX_DISCHARGE_KW,
	)
	generator = DieselGenerator(max_power_kw=GENERATOR_MAX_POWER_KW)
	controller = MicrogridController()
	return MicrogridSimulator(solar, battery, generator, controller, forecaster)

# Normal run
sim_normal = build_sim()
results_normal = sim_normal.run(load, solar_profile)
summary_normal = getattr(results_normal, "attrs", {}).get("summary", {})
print("NORMAL RUN SUMMARY:", summary_normal)
blackouts_normal = results_normal[results_normal["blackout"]]
if len(blackouts_normal) > 0:
	print("NORMAL RUN BLACKOUT TIMESTEPS:")
	blackouts_normal = blackouts_normal.copy()
	blackouts_normal["supply_calc_kw"] = (
		blackouts_normal["solar_kw"]
		+ blackouts_normal["generator_kw"]
		+ blackouts_normal["battery_kw"]
	)
	blackouts_normal["deficit_kw"] = (
		blackouts_normal["served_load_kw"] - blackouts_normal["supply_calc_kw"]
	)
	print(
		blackouts_normal[[
			"time",
			"load_kw",
			"served_load_kw",
			"solar_kw",
			"generator_kw",
			"battery_kw",
			"battery_soc",
			"supply_calc_kw",
			"deficit_kw",
			"generator_cmd",
			"state",
			"reason",
		]].to_string(index=False)
	)

# Simulated cyber attack run (SOC spoofing triggers SAFE_MODE)
# Use a realistic bounded spoof (0..1) and detect via secure-channel mismatch.
attack = {"type": "soc_spoof", "start": 36, "end": 72, "spoof_value": 0.95}
sim_attack = build_sim()
results_attack = sim_attack.run(load, solar_profile, attack=attack)
summary_attack = getattr(results_attack, "attrs", {}).get("summary", {})
print("ATTACK RUN SUMMARY:", summary_attack)

# Proof that AI is actively used
ai_triggers = int(summary_attack.get("ai_trigger_count", 0))
ai_forecasts = int(summary_attack.get("ai_forecast_count", 0))
print(f"AI STATUS: forecasts_generated={ai_forecasts}, ai_triggered_decisions={ai_triggers}")

# Proof that cyber detection is active
cyber_count = summary_attack.get("cyber_alert_count", 0)
cyber_first = summary_attack.get("cyber_first_timestep", None)
print(f"CYBER STATUS: cyber_alert_timesteps={cyber_count}, first_alert_timestep={cyber_first}")

try:
	with open("logs/cyber_events.txt", "r", encoding="utf-8") as f:
		last_line = ""
		for line in f:
			last_line = line
	if last_line.strip():
		print("LATEST CYBER EVENT:", last_line.strip())
except FileNotFoundError:
	print("LATEST CYBER EVENT: (no cyber_events.txt found)")

print(results_attack.tail(5))
