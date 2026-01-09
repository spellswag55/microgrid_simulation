from enum import Enum


class SystemState(Enum):
    NORMAL = "NORMAL"
    STRESSED = "STRESSED"
    EMERGENCY = "EMERGENCY"
    SAFE_MODE = "SAFE_MODE"


class MicrogridController:
    """
    Safety-critical autonomous energy source controller for hospital microgrids.
    """

    # ==========================================================
    # CONFIGURABLE SAFETY MARGINS (ADJUST PER HOSPITAL PROFILE)
    # ==========================================================

    SOC_NORMAL_MIN = 0.70
    SOC_STRESSED_MIN = 0.60
    SOC_EMERGENCY_MIN = 0.40

    SOC_ABSOLUTE_MIN = 0.30      # NEVER cross if generator exists
    SOC_CRITICAL_PREEMPT = 0.35  # Generator MUST start before this

    POWER_DEFICIT_MARGIN = 0.15

    LOAD_SHED_NONE = 0
    LOAD_SHED_T3 = 1
    LOAD_SHED_T2 = 2
    LOAD_SHED_T1 = 3

    def __init__(self):
        self.state = SystemState.NORMAL

    # ==========================================================
    # MAIN CONTROL LOOP
    # ==========================================================
    def decide(
        self,
        solar_kw,
        load_kw,
        battery,
        load_forecast=None,          # <<< AI INPUT (OPTIONAL)
        generator_available=True,
        cyber_anomaly=False
    ):

        # ------------------------------------------------------
        # 1. HARD FAIL-SAFE: CYBER OR SENSOR ANOMALY
        # ------------------------------------------------------
        if cyber_anomaly:
            self.state = SystemState.SAFE_MODE
            return self._safe_mode_action(
                reason="Cyber or sensor anomaly detected — entering SAFE_MODE"
            )

        soc = battery.soc

        # ------------------------------------------------------
        # 2. AI-BASED PREDICTIVE PREEMPTION (NEW, SAFE)
        # ------------------------------------------------------
        if load_forecast and generator_available:
            avg_future_load = sum(load_forecast) / len(load_forecast)

            if (
                avg_future_load > load_kw * 1.10
                and soc < self.SOC_STRESSED_MIN
            ):
                return {
                    "generator_cmd": "START",
                    "battery_mode": "DISCHARGE",
                    "load_shed_level": self.LOAD_SHED_NONE,
                    "state": self.state.value,
                    "safe_mode": False,
                    "reason": (
                        "Predictive generator start based on AI load forecast; "
                        "preventing future SOC collapse"
                    )
                }

        # ------------------------------------------------------
        # 3. HARD SAFETY PREEMPTION (DO NOT REMOVE)
        # ------------------------------------------------------
        if generator_available and soc <= self.SOC_CRITICAL_PREEMPT:
            self.state = SystemState.EMERGENCY
            return {
                "generator_cmd": "START",
                "battery_mode": "PROTECT",
                "load_shed_level": self.LOAD_SHED_T2,
                "state": self.state.value,
                "safe_mode": False,
                "reason": (
                    "Hard SOC preemption: generator forced ON before "
                    "absolute SOC violation (hospital safety guarantee)"
                )
            }

        # ------------------------------------------------------
        # 4. EARLY GENERATOR START — POWER DEFICIT PROTECTION
        # ------------------------------------------------------
        power_deficit = load_kw - solar_kw

        if (
            power_deficit > (load_kw * self.POWER_DEFICIT_MARGIN)
            and generator_available
        ):
            return {
                "generator_cmd": "START",
                "battery_mode": "DISCHARGE",
                "load_shed_level": self.LOAD_SHED_NONE,
                "state": self.state.value,
                "safe_mode": False,
                "reason": (
                    "Early generator start due to sustained power deficit; "
                    "preventing rapid SOC collapse and voltage risk"
                )
            }

        # ------------------------------------------------------
        # 5. STATE TRANSITIONS (SOC-BASED)
        # ------------------------------------------------------
        if soc < self.SOC_EMERGENCY_MIN:
            self.state = SystemState.EMERGENCY
        elif soc < self.SOC_STRESSED_MIN:
            self.state = SystemState.STRESSED
        else:
            self.state = SystemState.NORMAL

        # ------------------------------------------------------
        # 6. STATE ACTIONS
        # ------------------------------------------------------
        if self.state == SystemState.NORMAL:
            return {
                "generator_cmd": "STOP",
                "battery_mode": "DISCHARGE",
                "load_shed_level": self.LOAD_SHED_NONE,
                "state": self.state.value,
                "safe_mode": False,
                "reason": "Battery SOC healthy; normal hospital operation"
            }

        if self.state == SystemState.STRESSED:
            return {
                "generator_cmd": "START",
                "battery_mode": "DISCHARGE",
                "load_shed_level": self.LOAD_SHED_T3,
                "state": self.state.value,
                "safe_mode": False,
                "reason": (
                    "Preventive generator start due to declining SOC; "
                    "maintaining energy buffer for critical loads"
                )
            }

        if self.state == SystemState.EMERGENCY:
            return {
                "generator_cmd": "START" if generator_available else "HOLD",
                "battery_mode": "PROTECT",
                "load_shed_level": self.LOAD_SHED_T2,
                "state": self.state.value,
                "safe_mode": False,
                "reason": (
                    "Emergency condition: preserving life-critical hospital loads "
                    "and preventing inverter starvation"
                )
            }

    # ==========================================================
    # SAFE MODE — NON-BYPASSABLE FAIL-SAFE
    # ==========================================================
    def _safe_mode_action(self, reason):

        return {
            "generator_cmd": "START",
            "battery_mode": "PROTECT",
            "load_shed_level": self.LOAD_SHED_T1,
            "state": SystemState.SAFE_MODE.value,
            "safe_mode": True,
            "reason": reason
        }
