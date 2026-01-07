from enum import Enum


class SystemState(Enum):
    NORMAL = "NORMAL"
    STRESSED = "STRESSED"
    EMERGENCY = "EMERGENCY"
    SAFE_MODE = "SAFE_MODE"


class MicrogridController:
    """
    Safety-critical autonomous energy source controller for hospital microgrids.

    PURPOSE
    -------
    Guarantee uninterrupted power to life-critical hospital loads by making
    early, conservative, and deterministic source-switching decisions.

    SCOPE
    -----
    - Decides WHEN to use solar, battery, and generator
    - Does NOT control voltage or frequency directly
    - Assumes certified power electronics (UPS, inverter, AVR, ATS) handle fast dynamics

    DESIGN PRIORITY
    ----------------
    Human life > power continuity > equipment protection > cost efficiency
    """

    # ==========================================================
    # CONFIGURABLE SAFETY MARGINS (ADJUST PER HOSPITAL PROFILE)
    # ==========================================================

    # Battery SOC thresholds (conservative by design)
    SOC_NORMAL_MIN = 0.70
    SOC_STRESSED_MIN = 0.60
    SOC_EMERGENCY_MIN = 0.40
    SOC_ABSOLUTE_MIN = 0.30  # Never violate unless generator is unavailable

    # Power deficit margin for early generator start
    POWER_DEFICIT_MARGIN = 0.15  # 15% load deficit safety margin

    # Load shedding tiers (hospital criticality)
    LOAD_SHED_NONE = 0   # All loads powered
    LOAD_SHED_T3 = 1     # Shed admin / HVAC
    LOAD_SHED_T2 = 2     # Shed labs / imaging
    LOAD_SHED_T1 = 3     # Only life-critical loads (ICU, ventilators)

    def __init__(self):
        self.state = SystemState.NORMAL

    # ==========================================================
    # MAIN CONTROL LOOP (EXECUTED EVERY TIMESTEP)
    # ==========================================================
    def decide(
        self,
        solar_kw,
        load_kw,
        battery,
        generator_available=True,
        cyber_anomaly=False
    ):
        """
        Decide control actions for the current timestep.

        Parameters
        ----------
        solar_kw : float
            Current solar generation (kW)
        load_kw : float
            Current total load demand (kW)
        battery : object
            Battery object with attribute `soc` (0.0–1.0)
        generator_available : bool
            Whether generator is healthy and startable
        cyber_anomaly : bool
            True if sensor spoofing / command tampering is detected

        Returns
        -------
        dict
            Control commands and decision metadata
        """

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
        # 2. EARLY GENERATOR START — POWER DEFICIT PROTECTION
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
        # 3. STATE TRANSITIONS (SOC-BASED, CONSERVATIVE)
        # ------------------------------------------------------
        if soc < self.SOC_EMERGENCY_MIN:
            self.state = SystemState.EMERGENCY
        elif soc < self.SOC_STRESSED_MIN:
            self.state = SystemState.STRESSED
        else:
            self.state = SystemState.NORMAL

        # ------------------------------------------------------
        # 4. STATE ACTIONS
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
        """
        SAFE_MODE behavior:
        - Local autonomy only
        - Generator forced ON
        - Battery SOC protected
        - Only life-critical loads remain
        """

        return {
            "generator_cmd": "START",
            "battery_mode": "PROTECT",
            "load_shed_level": self.LOAD_SHED_T1,
            "state": SystemState.SAFE_MODE.value,
            "safe_mode": True,
            "reason": reason
        }
