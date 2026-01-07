class SafetyViolation(Exception):
    """
    Raised when a non-negotiable safety invariant is violated.
    """
    pass


class SafetyInvariants:
    """
    Formal safety rules for hospital-grade microgrid operation.

    These invariants must NEVER be violated.
    If any invariant fails, the system is considered unsafe.
    """

    @staticmethod
    def check(
        soc,
        generator_cmd,
        generator_available,
        load_shed_level,
        safe_mode
    ):
        """
        Validate all safety invariants for a single timestep.
        """

        # --------------------------------------------------
        # INVARIANT 1 — LIFE-CRITICAL LOADS MUST SURVIVE
        # --------------------------------------------------
        if load_shed_level > 3:
            raise SafetyViolation(
                "Invalid load shedding level detected"
            )

        # Tier-0 and Tier-1 loads must remain if any energy exists
        if soc > 0.0 and load_shed_level == 3 and not safe_mode:
            # Allowed only in SAFE_MODE
            raise SafetyViolation(
                "Critical loads shed outside SAFE_MODE"
            )

        # --------------------------------------------------
        # INVARIANT 2 — BATTERY MUST NOT BE SACRIFICED
        # --------------------------------------------------
        if soc < 0.30 and generator_available:
            raise SafetyViolation(
                "Battery SOC dropped below absolute minimum "
                "while generator was available"
            )

        # --------------------------------------------------
        # INVARIANT 3 — GENERATOR MUST START BEFORE CRISIS
        # --------------------------------------------------
        if soc < 0.40 and generator_available and generator_cmd != "START":
            raise SafetyViolation(
                "Generator not started during emergency SOC condition"
            )

        # --------------------------------------------------
        # INVARIANT 4 — SAFE_MODE IS ABSOLUTE
        # --------------------------------------------------
        if safe_mode and generator_cmd != "START":
            raise SafetyViolation(
                "SAFE_MODE active but generator not forced ON"
            )

        # --------------------------------------------------
        # INVARIANT 5 — NO SILENT FAILURE
        # --------------------------------------------------
        if generator_cmd not in ["START", "STOP", "HOLD"]:
            raise SafetyViolation(
                "Unknown generator command issued"
            )
