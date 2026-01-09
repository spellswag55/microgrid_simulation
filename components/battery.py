class Battery:
    def __init__(self, capacity_kwh, soc_init=0.5, max_charge_kw=50, max_discharge_kw=50):
        self.capacity = capacity_kwh
        self.soc = soc_init  # 0–1
        self.max_charge_kw = max_charge_kw
        self.max_discharge_kw = max_discharge_kw

    def charge(self, power_kw, dt=1):
        energy = min(power_kw, self.max_charge_kw) * dt
        self.soc = min(1.0, self.soc + energy / self.capacity)
        return energy

    def discharge(self, power_kw, dt=1, min_soc=0.0):
        energy = min(power_kw, self.max_discharge_kw) * dt

        min_soc = max(0.0, min(1.0, float(min_soc)))
        available_total = self.soc * self.capacity
        reserve = min_soc * self.capacity
        available = max(0.0, available_total - reserve)

        actual = min(energy, available)
        self.soc = max(min_soc, self.soc - actual / self.capacity)
        return actual
