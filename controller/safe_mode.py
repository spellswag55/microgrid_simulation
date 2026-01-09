def enforce_safe_mode(sensors):
    """
    Hard safety logic — cannot be overridden.
    """
    actions = {
        "use_battery": True,
        "use_generator": True,
        "load_shed_level": 3
    }

    if sensors["soc"] < 0.30:
        actions["use_battery"] = False
        actions["use_generator"] = True

    return actions
