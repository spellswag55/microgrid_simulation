def validate_phase5(blackout, critical_served, soc):
    if blackout:
        return False
    if not critical_served:
        return False
    if soc < 0.20:
        return False
    return True


# Backwards compatibility
def validator(blackout, critical_served, soc):
    return validate_phase5(
        blackout=blackout,
        critical_served=critical_served,
        soc=soc
    )
