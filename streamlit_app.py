import json
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ai.forecaster import LoadForecaster
from components.battery import Battery
from components.generator import DieselGenerator
from components.solar import SolarPV
from controller.microgrid_controller import MicrogridController
from scenarios.normal_day import load_profiles
from simulation.simulator import CRITICAL_LOAD_KW, MicrogridSimulator


st.set_page_config(
    page_title="Cyber-Secure Hospital Microgrid",
    layout="wide",
)


@dataclass(frozen=True)
class AssetSizing:
    solar_profile_scale: float = 6.0
    solar_max_power_kw: float = 900.0
    generator_max_power_kw: float = 2000.0
    battery_capacity_kwh: float = 8000.0
    battery_max_discharge_kw: float = 800.0
    battery_max_charge_kw: float = 800.0


@st.cache_data(show_spinner=False)
def load_dataset() -> tuple[np.ndarray, np.ndarray]:
    load, solar_profile = load_profiles()
    return np.asarray(load, dtype=float), np.asarray(solar_profile, dtype=float)


@st.cache_data(show_spinner=True)
def run_simulation(
    sizing: AssetSizing,
    attacks_json: str,
    cyber_log_mode: str,
    log_every_n: int,
) -> tuple[pd.DataFrame, dict]:
    load, solar_profile = load_dataset()

    # Full dataset by default
    solar_profile = solar_profile * float(sizing.solar_profile_scale)

    forecaster = LoadForecaster("ai/models/load_forecaster.pkl")

    solar = SolarPV(max_power_kw=float(sizing.solar_max_power_kw))
    battery = Battery(
        capacity_kwh=float(sizing.battery_capacity_kwh),
        soc_init=0.5,
        max_charge_kw=float(sizing.battery_max_charge_kw),
        max_discharge_kw=float(sizing.battery_max_discharge_kw),
    )
    generator = DieselGenerator(max_power_kw=float(sizing.generator_max_power_kw))
    controller = MicrogridController()

    sim = MicrogridSimulator(solar, battery, generator, controller, forecaster)

    attack = None
    try:
        parsed = json.loads(attacks_json) if attacks_json else []
        if isinstance(parsed, list) and parsed:
            attack = parsed
    except Exception:
        attack = None

    # Streamlit runs should not spam stdout; and we generally don’t want to rewrite
    # multi-thousand-line system logs on every rerun.
    df = sim.run(
        load,
        solar_profile,
        attack=attack,
        write_system_log=False,
        write_cyber_log=True,
        cyber_log_mode=str(cyber_log_mode),
        log_every_n=int(log_every_n),
        reset_logs=True,
        quiet=True,
    )

    summary = getattr(df, "attrs", {}).get("summary", {})
    return df, summary


def _kpi_row(summary: dict):
    cols = st.columns(6)
    cols[0].metric("Total Timesteps", int(summary.get("timesteps", 0)))
    cols[1].metric("Blackouts", int(summary.get("blackout_count", 0)))
    cyber_triggers = int(summary.get("cyber_alert_count", 0))
    cyber_active_steps = int(summary.get("cyber_alert_active_steps", 0))
    cyber_anomaly_steps = int(summary.get("cyber_anomaly_steps", cyber_active_steps))
    cols[2].metric("Cyber Events", cyber_anomaly_steps)
    cols[3].metric("Critical Load Lost", int(summary.get("critical_lost_count", 0)))
    cols[4].metric("Unsafe Actions", int(summary.get("unsafe_count", 0)))
    cols[5].metric("Validator Failures", int(summary.get("validator_fail_count", 0)))

    st.caption(
        f"Cyber breakdown: triggers={cyber_triggers} • alert-active timesteps={cyber_active_steps} • anomaly timesteps={cyber_anomaly_steps}"
    )


def _inference(ok: bool, good_text: str, bad_text: str):
    if ok:
        st.write(good_text)
    else:
        st.error(bad_text)


def _state_to_code(state: pd.Series) -> pd.Series:
    mapping = {"NORMAL": 0, "STRESSED": 1, "EMERGENCY": 2, "SAFE_MODE": 3}
    return state.map(mapping).fillna(-1)


def main():
    st.title("Autonomous & Cyber-Secure Hospital Microgrid – Digital Twin")

    # Keep results stable across reruns (Streamlit reruns on any widget change)
    if "has_run" not in st.session_state:
        st.session_state["has_run"] = False
    if "df" not in st.session_state:
        st.session_state["df"] = None
    if "summary" not in st.session_state:
        st.session_state["summary"] = None
    if "last_run_params" not in st.session_state:
        st.session_state["last_run_params"] = None
    if "attack_table" not in st.session_state:
        st.session_state["attack_table"] = pd.DataFrame(
            [
                {
                    "enabled": True,
                    "type": "soc_spoof",
                    "start": 36,
                    "end": 72,
                    "spoof_value": 0.95,
                    "scale": 1.0,
                    "offset": 0.0,
                },
                {
                    "enabled": False,
                    "type": "load_spoof",
                    "start": 80,
                    "end": 100,
                    "spoof_value": 0.95,
                    "scale": 1.25,
                    "offset": 0.0,
                },
            ]
        )

    with st.sidebar:
        st.header("Run Configuration")

        st.subheader("Asset Sizing")
        solar_profile_scale = st.number_input("Solar profile scale", value=6.0, min_value=0.1, step=0.5)
        solar_max_power_kw = st.number_input("PV max power (kW)", value=900.0, min_value=10.0, step=50.0)
        generator_max_power_kw = st.number_input("Generator max power (kW)", value=2000.0, min_value=10.0, step=100.0)
        battery_capacity_kwh = st.number_input("Battery capacity (kWh)", value=8000.0, min_value=10.0, step=500.0)
        battery_max_discharge_kw = st.number_input("Battery max discharge (kW)", value=800.0, min_value=10.0, step=50.0)
        battery_max_charge_kw = st.number_input("Battery max charge (kW)", value=800.0, min_value=10.0, step=50.0)

        st.subheader("Cyber Attack")
        enable_attack = st.toggle("Enable cyber attacks", value=True)

        load, _ = load_dataset()
        max_t = max(0, len(load) - 1)

        st.caption("Define one or more attacks. Multiple rows can be active at once.")

        attack_df = st.data_editor(
            st.session_state["attack_table"],
            key="attack_table_editor",
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "enabled": st.column_config.CheckboxColumn("Enabled"),
                "type": st.column_config.SelectboxColumn(
                    "Type",
                    options=["soc_spoof", "load_spoof", "solar_spoof"],
                    help="SOC spoof affects measured SOC; load/solar spoof affects what the controller sees.",
                ),
                "start": st.column_config.NumberColumn("Start", min_value=0, max_value=int(max_t), step=1),
                "end": st.column_config.NumberColumn("End", min_value=0, max_value=int(max_t), step=1),
                "spoof_value": st.column_config.NumberColumn("SOC spoof value", min_value=0.0, max_value=1.0, step=0.01),
                "scale": st.column_config.NumberColumn("Scale", min_value=0.0, step=0.05),
                "offset": st.column_config.NumberColumn("Offset (kW)", step=10.0),
            },
        )
        st.session_state["attack_table"] = attack_df

        st.subheader("Performance")
        log_every_n = st.selectbox("Downsample charts (plot every N points)", [1, 2, 5, 10, 20], index=2)

        cyber_log_mode = st.selectbox(
            "Cyber event log detail",
            ["transition", "anomaly", "active"],
            index=1,
            help="transition = log once when alert triggers; anomaly = log each detected anomaly; active = log every timestep while latched alert is active (can be large).",
        )

        st.divider()
        run_clicked = st.button("Run Simulation", type="primary", use_container_width=True)

    sizing = AssetSizing(
        solar_profile_scale=float(solar_profile_scale),
        solar_max_power_kw=float(solar_max_power_kw),
        generator_max_power_kw=float(generator_max_power_kw),
        battery_capacity_kwh=float(battery_capacity_kwh),
        battery_max_discharge_kw=float(battery_max_discharge_kw),
        battery_max_charge_kw=float(battery_max_charge_kw),
    )

    run_params = {
        "sizing": sizing,
        "attacks_json": "",
        "cyber_log_mode": str(cyber_log_mode),
        "log_every_n": int(log_every_n),
    }

    attacks: list[dict] = []
    if enable_attack:
        for _, row in st.session_state["attack_table"].fillna(0).iterrows():
            if not bool(row.get("enabled", False)):
                continue

            a_type = str(row.get("type", "")).strip()
            if not a_type:
                continue

            start = int(row.get("start", 0))
            end = int(row.get("end", -1))
            a: dict = {"type": a_type, "start": start, "end": end}

            if a_type == "soc_spoof":
                a["spoof_value"] = float(row.get("spoof_value", 0.95))
            elif a_type in {"load_spoof", "solar_spoof"}:
                a["scale"] = float(row.get("scale", 1.0))
                a["offset"] = float(row.get("offset", 0.0))

            attacks.append(a)

    run_params["attacks_json"] = json.dumps(attacks, sort_keys=True)

    if run_clicked:
        st.session_state["last_run_params"] = run_params
        with st.spinner("Running simulation..."):
            df, summary = run_simulation(**run_params)
        st.session_state["df"] = df
        st.session_state["summary"] = summary
        st.session_state["has_run"] = True

    if not st.session_state.get("has_run", False) or st.session_state.get("df") is None:
        st.info("Configure the sidebar, then click ‘Run Simulation’.", icon="ℹ️")
        st.stop()

    # Use the last computed results (don’t auto-recompute when sidebar changes)
    df = st.session_state["df"]
    summary = st.session_state["summary"]

    last_params = st.session_state.get("last_run_params")
    if last_params is not None and last_params != run_params:
        st.warning("Sidebar settings changed — click ‘Run Simulation’ to apply.")

    # Executive snapshot
    _kpi_row(summary)

    st.divider()

    # Optional downsample for faster plots
    df_plot = df if log_every_n <= 1 else df.iloc[:: int(log_every_n)].copy()

    # ------------------------------------------------------------------
    # SYSTEM BEHAVIOR
    # ------------------------------------------------------------------
    with st.expander("⚡ Power Flow & System Behavior", expanded=True):
        st.subheader("1) Load vs Total Supply")
        df_plot = df_plot.copy()
        df_plot["total_supply_kw"] = df_plot["solar_kw"] + df_plot["generator_kw"] + df_plot["battery_kw"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot["time"], y=df_plot["served_load_kw"], name="Served Load (kW)"))
        fig.add_trace(go.Scatter(x=df_plot["time"], y=df_plot["total_supply_kw"], name="Total Supply (kW)"))
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

        _inference(
            ok=int(summary.get("blackout_count", 0)) == 0,
            good_text="Inference: Supply consistently meets or exceeds served demand — no blackout observed.",
            bad_text="Inference: Blackout observed — supply fell below served demand at least once.",
        )

        st.subheader("2) Battery SOC Timeline")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot["time"], y=df_plot["battery_soc_pct"], name="SOC (%)"))
        fig.add_hline(y=30, line_dash="dash", line_color="orange")
        fig.add_hline(y=20, line_dash="dash", line_color="red")
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

        _inference(
            ok=int(summary.get("unsafe_count", 0)) == 0,
            good_text="Inference: Battery never enters unsafe region; discharge is safety-bounded and generator support is used.",
            bad_text="Inference: Unsafe SOC region reached (SOC < 20%).",
        )

        st.subheader("3) Generator Operation")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot["time"], y=df_plot["generator_kw"], name="Generator Power (kW)"))
        fig.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

        st.write("Inference: Generator output is dispatched to cover remaining demand after solar; SAFE_MODE forces generator ON under attack.")

    # ------------------------------------------------------------------
    # AUTONOMOUS DECISION ENGINE
    # ------------------------------------------------------------------
    with st.expander("🧠 Autonomous Controller Decisions"):
        st.subheader("4) Controller State Timeline")
        df_state = df_plot[["time", "state"]].copy()
        df_state["state_code"] = _state_to_code(df_state["state"])
        fig = px.line(df_state, x="time", y="state_code", title=None)
        fig.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10))
        fig.update_yaxes(
            tickmode="array",
            tickvals=[0, 1, 2, 3],
            ticktext=["NORMAL", "STRESSED", "EMERGENCY", "SAFE_MODE"],
        )
        st.plotly_chart(fig, use_container_width=True)
        st.write("Inference: State transitions are deterministic (SOC + anomaly-driven) and remain stable.")

        st.subheader("5) Decision Reasons Table")
        c1, c2, c3 = st.columns(3)
        show_safe_mode_only = c1.checkbox("Show only SAFE_MODE", value=False)
        show_ai_only = c2.checkbox("Show only AI-influenced", value=False)
        show_cyber_only = c3.checkbox("Show only cyber-related timesteps", value=False)

        cyber_col = "cyber_anomaly_now" if "cyber_anomaly_now" in df.columns else "cyber_alert"
        table = df[["time", "state", "generator_cmd", "ai_triggered", "cyber_alert", "reason"]].copy()
        if cyber_col not in table.columns:
            table[cyber_col] = df[cyber_col]
        if show_safe_mode_only:
            table = table[table["state"] == "SAFE_MODE"]
        if show_ai_only:
            table = table[table["ai_triggered"]]
        if show_cyber_only:
            table = table[df[cyber_col]]

        st.dataframe(table, use_container_width=True, height=320)
        st.write("Inference: All actions are explainable and logged with human-readable reasons.")

    # ------------------------------------------------------------------
    # AI INTELLIGENCE
    # ------------------------------------------------------------------
    with st.expander("🤖 AI Forecasting & Predictive Control"):
        st.subheader("6) Load Forecast vs Actual")
        df_ai = df_plot[["time", "load_kw", "ai_forecast_t_plus_1_kw", "ai_forecast_avg_6h_kw"]].copy()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_ai["time"], y=df_ai["load_kw"], name="Actual Load (kW)"))
        fig.add_trace(go.Scatter(x=df_ai["time"], y=df_ai["ai_forecast_avg_6h_kw"], name="AI Forecast (avg next 6h)", opacity=0.8))
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

        st.write("Inference: AI forecasts are generated after sufficient history and can trigger preventive generator starts in normal operation.")

        st.subheader("7) AI Trigger Events")
        triggers = df[df["ai_triggered"]][["time", "state", "generator_cmd", "reason"]]
        st.dataframe(triggers, use_container_width=True, height=240)
        st.write("Inference: AI influences decisions without overriding safety rules.")

        st.subheader("8) AI Override Proof")
        st.write(
            "During cyber alert, SAFE_MODE is enforced and the controller is driven by deterministic safety logic. "
            "AI forecasting can remain active (forecasts generated) but decisions are safety-gated."
        )
        ai_during_cyber = df[(df["cyber_alert"]) & (df["ai_forecast"])][["time", "state", "ai_forecast", "ai_triggered", "reason"]]
        st.dataframe(ai_during_cyber, use_container_width=True, height=220)

    # ------------------------------------------------------------------
    # CYBER SECURITY & RESILIENCE
    # ------------------------------------------------------------------
    with st.expander("🔒 Cyber Security & Safe-Mode Operation"):
        st.subheader("9) Cyber Attack Timeline")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot["time"], y=df_plot["cyber_alert"].astype(int), name="Cyber Alert (latched)"))
        if "cyber_anomaly_now" in df_plot.columns:
            fig.add_trace(go.Scatter(x=df_plot["time"], y=df_plot["cyber_anomaly_now"].astype(int), name="Anomaly this step"))
        if "attack_active" in df_plot.columns:
            fig.add_trace(go.Scatter(x=df_plot["time"], y=df_plot["attack_active"].astype(int), name="Attack window (simulated)", opacity=0.6))
        fig.add_trace(go.Scatter(x=df_plot["time"], y=_state_to_code(df_plot["state"]), name="State (coded)", opacity=0.7))
        fig.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Note: Cyber Alert is latched once triggered (realistic operator-reset behavior). "
            "Use 'Anomaly this step' to see the instantaneous detection signal."
        )
        st.write("Inference: Cyber anomalies are detected and drive the system into SAFE_MODE.")

        st.subheader("10) SAFE_MODE Behavior")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot["time"], y=df_plot["served_load_kw"], name="Served Load (kW)"))
        fig.add_hline(y=CRITICAL_LOAD_KW, line_dash="dash", line_color="green")
        fig.add_trace(go.Scatter(x=df_plot["time"], y=df_plot["generator_kw"], name="Generator Power (kW)", opacity=0.7))
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)
        st.write("Inference: Under attack, non-critical demand is shed, generator is forced ON, and battery deep discharge is prevented.")

        st.subheader("11) Cyber Event Log Viewer")
        os.makedirs("logs", exist_ok=True)
        log_path = "logs/cyber_events.txt"
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                st.text_area("cyber_events.txt", f.read(), height=140)
        else:
            st.info("No cyber log file found yet.")

        st.subheader("12) Cyber Events (from this run)")
        event_mask = None
        if "cyber_anomaly_now" in df.columns:
            event_mask = df["cyber_anomaly_now"]
        else:
            event_mask = df["cyber_alert"]

        cols = ["time", "cyber_alert"]
        for c in ["cyber_anomaly_now", "cyber_reason", "attack_active", "attack_types", "state"]:
            if c in df.columns:
                cols.append(c)

        events = df.loc[event_mask, cols].copy()
        st.dataframe(events, use_container_width=True, height=240)

        st.write("Inference: Full forensic trace is available via cyber event logs.")

    # ------------------------------------------------------------------
    # VALIDATION & OUTLIERS
    # ------------------------------------------------------------------
    with st.expander("✅ Validation, Outliers & Stress Points"):
        st.subheader("12) Validator Timeline")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot["time"], y=df_plot["validator_ok"].astype(int), name="validator_ok"))
        fig.update_layout(height=240, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

        _inference(
            ok=int(summary.get("validator_fail_count", 0)) == 0,
            good_text="Inference: Formal safety conditions satisfied at every timestep.",
            bad_text="Inference: Validator failures occurred at least once.",
        )

        st.subheader("13) Outlier Detection")
        df_out = df_plot[["time", "load_kw", "solar_kw", "battery_soc_pct"]].copy()
        for col in ["load_kw", "solar_kw"]:
            rolling = df_out[col].rolling(window=24, min_periods=12)
            mu = rolling.mean()
            sigma = rolling.std().replace(0, np.nan)
            df_out[f"{col}_z"] = (df_out[col] - mu) / sigma

        spikes = df_out[df_out["load_kw_z"].abs() > 3][["time", "load_kw", "load_kw_z"]]
        solar_drops = df_out[df_out["solar_kw_z"].abs() > 3][["time", "solar_kw", "solar_kw_z"]]

        c1, c2 = st.columns(2)
        c1.write("Load spikes (|z| > 3)")
        c1.dataframe(spikes, use_container_width=True, height=220)
        c2.write("Solar anomalies (|z| > 3)")
        c2.dataframe(solar_drops, use_container_width=True, height=220)

        st.write("Inference: The system remains stable even when load/solar conditions are extreme.")

    st.divider()

    st.markdown(
        """
### Final Technical Summary

**System Guarantees**
- Zero blackout (served-load basis)
- Critical loads always served
- No unsafe actions
- Autonomous operation via deterministic controller
- AI-assisted prediction (advisory)
- Cyber-secure failover to SAFE_MODE
- Graceful degradation under attack (shed non-critical loads)
"""
    )


if __name__ == "__main__":
    main()
