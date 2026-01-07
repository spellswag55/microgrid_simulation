class SolarPV:
    def __init__(self, max_power_kw):
        self.max_power_kw = max_power_kw

    def get_power(self, available_power_kw):
        return min(self.max_power_kw, available_power_kw)
