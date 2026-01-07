class Battery:
    def __init__(self, capacity_kwh, soc_init=0.5):
        self.capacity = capacity_kwh
        self.soc = soc_init  # 0–1
        self.max_charge_kw = 50
        self.max_discharge_kw = 50

    def charge(self, power_kw, dt=1):
        energy = min(power_kw, self.max_charge_kw) * dt
        self.soc = min(1.0, self.soc + energy / self.capacity)
        return energy

    def discharge(self, power_kw, dt=1):
        energy = min(power_kw, self.max_discharge_kw) * dt
        available = self.soc * self.capacity
        actual = min(energy, available)
        self.soc -= actual / self.capacity
        return actual
