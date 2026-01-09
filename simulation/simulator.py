import pandas as pd
from controller.safety_invariants import SafetyInvariants


class MicrogridSimulator:
    def __init__(self, solar, battery, generator, controller, forecaster=None):
        self.solar = solar
        self.battery = battery
        self.generator = generator
        self.controller = controller
        self.forecaster = forecaster
        self.history = []  # used for AI forecasting only


    def _get_value(self, profile, t):
        if isinstance(profile, pd.DataFrame):
            return profile.iloc[t, 0]
        elif isinstance(profile, pd.Series):
            return profile.iloc[t]
        else:
            return profile[t]


    def run(self, load_profile, solar_profile):
        results = []
        horizon = len(load_profile)

        for t in range(horizon):
            load_kw = self._get_value(load_profile, t)
            solar_kw = self._get_value(solar_profile, t)

            # --------------------------------------------------
            # STORE HISTORY FOR AI (PASSIVE, NO CONTROL)
            # --------------------------------------------------
            self.history.append({
                "timestamp": t,
                "load_kw": load_kw
            })

            # --------------------------------------------------
            # AI LOAD FORECAST (OPTIONAL)
            # --------------------------------------------------
            load_forecast = None
            if self.forecaster and len(self.history) >= 24:
                history_df = pd.DataFrame(self.history)
                load_forecast = self.forecaster.predict_next(
                    history_df,
                    hours_ahead=6
                )

            # --------------------------------------------------
            # 1. CONTROLLER DECISION (RULES + AI ADVICE)
            # --------------------------------------------------
            decision = self.controller.decide(
                solar_kw=solar_kw,
                load_kw=load_kw,
                battery=self.battery,
                load_forecast=load_forecast
            )

            # --------------------------------------------------
            # 2. APPLY GENERATOR COMMAND
            # --------------------------------------------------
            if decision["generator_cmd"] == "START":
                self.generator.start()
            elif decision["generator_cmd"] == "STOP":
                self.generator.stop()

            # --------------------------------------------------
            # 3. POWER BALANCE (HOSPITAL-GRADE LOGIC)
            # --------------------------------------------------
            gen_kw = self.generator.get_power()
            supply_kw = solar_kw + gen_kw

            # CRITICAL SAFETY RULE:
            # If generator is ON, battery MUST be protected
            discharged_kw = 0.0
            if decision["generator_cmd"] != "START":
                deficit_kw = load_kw - supply_kw
                if deficit_kw > 0 and self.battery.soc > 0.30:
                    discharged_kw = self.battery.discharge(deficit_kw)

            supply_kw += discharged_kw
            blackout = supply_kw < load_kw

            # --------------------------------------------------
            # 4. SAFETY INVARIANT CHECK (DO NOT TOUCH)
            # --------------------------------------------------
            SafetyInvariants.check(
                soc=self.battery.soc,
                generator_cmd=decision["generator_cmd"],
                generator_available=True,
                load_shed_level=0,
                safe_mode=False
            )

            # --------------------------------------------------
            # 5. LOG RESULTS
            # --------------------------------------------------
            results.append({
                "time": t,
                "load_kw": load_kw,
                "solar_kw": solar_kw,
                "generator_kw": gen_kw,
                "battery_soc": self.battery.soc,
                "generator_cmd": decision["generator_cmd"],
                "state": decision["state"],
                "blackout": blackout,
                "reason": decision["reason"]
            })

        return pd.DataFrame(results)
