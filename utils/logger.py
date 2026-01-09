import os


def log_system(
    t,
    state,
    soc,
    supply,
    load,
    served_load=None,
    blackout=False,
    critical_served=None,
    cyber_alert=None,
    unsafe=None,
    validator_ok=None,
    ai_forecast=None,
    ai_triggered=None,
    reason="",
):
    os.makedirs("logs", exist_ok=True)
    with open("logs/system_log.txt", "a", encoding="utf-8") as f:
        parts = [
            f"time={t}",
            f"state={state}",
            f"soc={soc:.3f}",
            f"supply={supply:.3f}",
            f"load={load:.3f}",
        ]

        if served_load is not None:
            parts.append(f"served_load={served_load:.3f}")

        parts.append(f"blackout={bool(blackout)}")

        if critical_served is not None:
            parts.append(f"critical_served={bool(critical_served)}")
        if cyber_alert is not None:
            parts.append(f"cyber_alert={bool(cyber_alert)}")
        if unsafe is not None:
            parts.append(f"unsafe={bool(unsafe)}")
        if validator_ok is not None:
            parts.append(f"validator_ok={bool(validator_ok)}")
        if ai_forecast is not None:
            parts.append(f"ai_forecast={bool(ai_forecast)}")
        if ai_triggered is not None:
            parts.append(f"ai_triggered={bool(ai_triggered)}")

        if reason:
            parts.append(f"reason={reason}")

        f.write(", ".join(parts) + "\n")
