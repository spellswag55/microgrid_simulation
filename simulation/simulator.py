import pandas as pd

class MicrogridSimulator:
    def __init__(self, solar, battery, generator, controller):
        self.solar = solar
        self.battery = battery
        self.generator = generator
        self.controller = controller

    def run(self, load_profile, solar_profile):
        results = []

        for hour in range(24):
            load_kw = load_profile.loc[hour, "load_kw"]
            solar_kw = self.solar.get_power(
                solar_profile.loc[hour, "solar_kw"]
            )

            decision = self.controller.decide(
                solar_kw, load_kw, self.battery
            )

            if decision["generator"]:
                self.generator.start()
            else:
                self.generator.stop()

            gen_kw = self.generator.get_power()

            supply = solar_kw + gen_kw
            deficit = load_kw - supply

            if deficit > 0:
                discharged = self.battery.discharge(deficit)
                supply += discharged

            blackout = supply < load_kw

            results.append({
                "hour": hour,
                "load_kw": load_kw,
                "solar_kw": solar_kw,
                "generator_kw": gen_kw,
                "battery_soc": round(self.battery.soc, 2),
                "blackout": blackout
            })

        return pd.DataFrame(results)
