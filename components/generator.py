class DieselGenerator:
    def __init__(self, max_power_kw):
        self.max_power_kw = max_power_kw
        self.is_on = False

    def start(self):
        self.is_on = True

    def stop(self):
        self.is_on = False

    def get_power(self):
        return self.max_power_kw if self.is_on else 0
