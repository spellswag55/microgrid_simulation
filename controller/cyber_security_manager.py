import os


class CyberSecurityManager:
    """
    Detects cyber attacks such as sensor spoofing or command injection.
    """

    def __init__(self):
        self.alert_active = False
        self.anomaly_now = False
        self.reason = None
        self._last_soc = None
        self._last_load = None
        self._last_solar = None

        # Detection thresholds (tunable)
        self.max_soc_jump_per_step = 0.08  # 8% SOC jump in 1 timestep is suspicious
        self.redundant_soc_mismatch = 0.05  # 5% mismatch vs secure redundant channel

        # Additional sensor spoof detection (secure-channel mismatch)
        self.redundant_load_mismatch_frac = 0.10  # 10% mismatch vs secure load meter
        self.redundant_solar_mismatch_frac = 0.15  # 15% mismatch vs secure PV telemetry

        # Conservative jump checks (mostly for gross anomalies)
        self.max_load_jump_kw = 500.0
        self.max_solar_jump_kw = 800.0

    def evaluate(self, sensor_data):
        """
        Simple rule-based cyber detection.
        """
        soc = sensor_data.get("soc")
        soc_secure = sensor_data.get("soc_secure")
        load_kw = sensor_data.get("load_kw")
        load_kw_secure = sensor_data.get("load_kw_secure")
        solar_kw = sensor_data.get("solar_kw")
        solar_kw_secure = sensor_data.get("solar_kw_secure")

        anomaly = False
        reason = None

        # Impossible SOC values → spoofing
        if soc is not None and (soc < 0 or soc > 1):
            anomaly = True
            reason = "SOC sensor spoofing detected (out-of-range)"

        # Redundant secure channel mismatch → spoofing (realistic bounded spoof)
        if (
            not anomaly
            and soc is not None
            and soc_secure is not None
            and abs(float(soc) - float(soc_secure)) > self.redundant_soc_mismatch
        ):
            anomaly = True
            reason = "SOC sensor spoofing detected (mismatch vs secure channel)"

        # Implausible SOC jump → spoofing/anomaly
        if (
            not anomaly
            and soc is not None
            and self._last_soc is not None
            and abs(float(soc) - float(self._last_soc)) > self.max_soc_jump_per_step
        ):
            anomaly = True
            reason = "SOC anomaly detected (implausible step change)"

        if soc is not None:
            self._last_soc = float(soc)

        # --------------------------------------------------
        # LOAD SENSOR SPOOFING
        # --------------------------------------------------
        if not anomaly and load_kw is not None and float(load_kw) < 0:
            anomaly = True
            reason = "Load sensor spoofing detected (negative)"

        if (
            not anomaly
            and load_kw is not None
            and load_kw_secure is not None
        ):
            secure = float(load_kw_secure)
            denom = max(1.0, abs(secure))
            if abs(float(load_kw) - secure) / denom > self.redundant_load_mismatch_frac:
                anomaly = True
                reason = "Load sensor spoofing detected (mismatch vs secure channel)"

        if (
            not anomaly
            and load_kw is not None
            and self._last_load is not None
            and abs(float(load_kw) - float(self._last_load)) > self.max_load_jump_kw
        ):
            anomaly = True
            reason = "Load anomaly detected (implausible step change)"

        if load_kw is not None:
            self._last_load = float(load_kw)

        # --------------------------------------------------
        # SOLAR SENSOR SPOOFING
        # --------------------------------------------------
        if not anomaly and solar_kw is not None and float(solar_kw) < 0:
            anomaly = True
            reason = "Solar sensor spoofing detected (negative)"

        if (
            not anomaly
            and solar_kw is not None
            and solar_kw_secure is not None
        ):
            secure = float(solar_kw_secure)
            denom = max(1.0, abs(secure))
            if abs(float(solar_kw) - secure) / denom > self.redundant_solar_mismatch_frac:
                anomaly = True
                reason = "Solar sensor spoofing detected (mismatch vs secure channel)"

        if (
            not anomaly
            and solar_kw is not None
            and self._last_solar is not None
            and abs(float(solar_kw) - float(self._last_solar)) > self.max_solar_jump_kw
        ):
            anomaly = True
            reason = "Solar anomaly detected (implausible step change)"

        if solar_kw is not None:
            self._last_solar = float(solar_kw)

        # Expose the instantaneous anomaly (useful for dashboards and debugging)
        self.anomaly_now = anomaly

        # Latch alert once detected (requires reset / operator action in real systems)
        if anomaly:
            self.alert_active = True
            self.reason = reason

        return self.alert_active

    def raise_alert(self, time_step):
        self.log_event(time_step, f"CYBER ALERT: {self.reason}")

    def log_event(self, time_step, message: str):
        os.makedirs("logs", exist_ok=True)
        with open("logs/cyber_events.txt", "a", encoding="utf-8") as f:
            f.write(f"time={time_step} {message}\n")
