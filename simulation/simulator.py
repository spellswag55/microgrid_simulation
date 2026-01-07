import pandas as pd
from controller.safety_invariants import SafetyInvariants

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
            # ==============================
            # SAFETY INVARIANT CHECK (PHASE 2 FINAL)
            # ==============================
            SafetyInvariants.check(
                soc=self.battery.soc,
                generator_cmd="START" if decision["generator"] else "STOP",
                generator_available=True,   # generator faults not modeled yet
                load_shed_level=0,          # load shedding not wired yet
                safe_mode=False             # SAFE_MODE not wired yet
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
