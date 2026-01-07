class MicrogridController:
    def decide(self, solar_kw, load_kw, battery):
        """
        Phase 1: no intelligence
        Generator is manually forced ON if battery < 20%
        """
        if battery.soc < 0.2:
            return {"generator": True}
        return {"generator": False}
