from components.solar import SolarPV
from components.battery import Battery
from components.generator import DieselGenerator
from controller.microgrid_controller import MicrogridController
from simulation.simulator import MicrogridSimulator
from scenarios.normal_day import load_profiles

solar = SolarPV(max_power_kw=130)
battery = Battery(capacity_kwh=300, soc_init=0.5)
generator = DieselGenerator(max_power_kw=100)
controller = MicrogridController()

load, solar_profile = load_profiles()

sim = MicrogridSimulator(solar, battery, generator, controller)
results = sim.run(load, solar_profile)

print(results)
