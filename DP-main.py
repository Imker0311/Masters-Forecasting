import os
import importlib.util

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_module(name, filename):
    # plain `import` can't reference these - hyphens aren't valid in module names
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_cstr_data = _load_module("DP_cstr_data", "DP-cstr_data.py")
_chronos2_forecaster = _load_module("DP_chronos2_forecaster", "DP-chronos2_forecaster.py")
_ekf = _load_module("DP_EKF", "DP-EKF.py")

load_cstr_data, STATE_COLUMNS, EXOG_COLUMNS = (
    _cstr_data.load_cstr_data, _cstr_data.STATE_COLUMNS, _cstr_data.EXOG_COLUMNS,
)
Chronos2Forecaster = _chronos2_forecaster.Chronos2Forecaster
StateFilter = _ekf.StateFilter

# --- Config ------------------------------------------------------------------
DOWNSAMPLE = 20
CONTEXT_LENGTH = 2000     # samples of history before stepping/forecasting begins
HORIZON = 30              # forecast horizon per replan, in samples
REPLAN_INTERVAL = 1       # re-forecast every N steps
N_STEPS = None             # steps to play through; None = run to end of data
STEP_PAUSE_SEC = 0.05     # wall-clock pause between frames
PLOT_WINDOW = 50          # samples of history shown (display only)
MEASUREMENT_STD = {       # simulated sensor noise added to ground truth
    "C_A": 0.0005, "T": 0.05, "T_C": 0.05, "h": 5e-5, "Q": 0.001, "Qc": 0.001,
}
RNG_SEED = 0
SAVE_PATH = None          # set to e.g. "demo.gif" to save instead of showing a live window

STATE_NAMES = list(STATE_COLUMNS.values())
EXOG_NAMES = list(EXOG_COLUMNS.values())


def run():
    df, dt = load_cstr_data(downsample=DOWNSAMPLE)
    n = len(df)
    end = n if N_STEPS is None else min(CONTEXT_LENGTH + N_STEPS, n)

    forecaster = Chronos2Forecaster()
    measurement_var = {name: std**2 for name, std in MEASUREMENT_STD.items()}
    ekf = StateFilter(STATE_NAMES, measurement_var)
    rng = np.random.default_rng(RNG_SEED)

    filtered_history = {name: [] for name in STATE_NAMES}
    measurement_history = {name: [] for name in STATE_NAMES}
    time_history = []

    last_forecast = None
    last_forecast_start = None

    # h: fixed range around its mean, since rare spikes would otherwise dominate the axis
    h_mean, h_std = df["h"].mean(), df["h"].std()
    h_ylim = (h_mean - 4 * h_std, h_mean + 4 * h_std)

    fig, axes = plt.subplots(3, 2, figsize=(12, 9))
    axes = axes.ravel()
    lines = {}
    for ax, name in zip(axes, STATE_NAMES):
        ax.set_title(name)
        if name == "h":
            ax.set_ylim(*h_ylim)
        lines[name] = {
            "truth": ax.plot([], [], color="black", lw=1, label="ground truth")[0],
            "filtered": ax.plot([], [], color="tab:green", lw=1.2, label="filtered (EKF)")[0],
            "forecast": ax.plot([], [], color="tab:blue", lw=1.2, ls="--", label="forecast")[0],
            "band": ax.fill_between([], [], [], color="tab:blue", alpha=0.2),
        }
    axes[0].legend(fontsize=8, loc="upper left")
    fig.tight_layout()

    def step(t):
        nonlocal last_forecast, last_forecast_start

        actual_horizon = min(HORIZON, n - t)
        if (t - CONTEXT_LENGTH) % REPLAN_INTERVAL == 0 and actual_horizon > 0:
            context_df = df.iloc[:t]
            future_df = df.iloc[t:t + actual_horizon][["item_id", "timestamp"] + EXOG_NAMES]
            last_forecast = forecaster.forecast(context_df, future_df, STATE_NAMES, EXOG_NAMES, actual_horizon)
            last_forecast_start = t

        steps_ahead = t - last_forecast_start
        measurements = {}
        pred_means, pred_vars = {}, {}
        for name in STATE_NAMES:
            traj_len = len(last_forecast[name]["mean"])
            i = min(steps_ahead, traj_len - 1)
            pred_means[name] = last_forecast[name]["mean"][i]
            pred_vars[name] = last_forecast[name]["var"][i]
            measurements[name] = df[name].iloc[t] + rng.normal(0, MEASUREMENT_STD[name])

        fused_means, _ = ekf.update(pred_means, pred_vars, measurements)

        time_history.append(df["timestamp"].iloc[t])
        for name in STATE_NAMES:
            filtered_history[name].append(fused_means[name])
            measurement_history[name].append(measurements[name])

        for ax, name in zip(axes, STATE_NAMES):
            lo = max(0, len(time_history) - PLOT_WINDOW)
            t_hist = time_history[lo:]
            truth_hist = df[name].iloc[max(0, t - PLOT_WINDOW) + 1:t + 1]
            lines[name]["truth"].set_data(df["timestamp"].iloc[max(0, t - PLOT_WINDOW) + 1:t + 1], truth_hist)
            lines[name]["filtered"].set_data(t_hist, filtered_history[name][lo:])

            fc_i = steps_ahead
            fc_time = df["timestamp"].iloc[t:last_forecast_start + len(last_forecast[name]["mean"])]
            fc_mean = last_forecast[name]["mean"][fc_i:]
            fc_std = np.sqrt(last_forecast[name]["var"][fc_i:])
            lines[name]["forecast"].set_data(fc_time, fc_mean)
            lines[name]["band"].remove()
            lines[name]["band"] = ax.fill_between(fc_time, fc_mean - fc_std, fc_mean + fc_std, color="tab:blue", alpha=0.2)

            ax.set_xlim(df["timestamp"].iloc[max(0, t - PLOT_WINDOW) + 1], fc_time.iloc[-1])  # slide the window
            if name == "h":
                ax.set_ylim(*h_ylim)  # keep fixed - everything else autoscales
            else:
                ax.relim()
                ax.autoscale_view(scalex=False)
        fig.suptitle(f"t = {df['timestamp'].iloc[t]}  (step {t - CONTEXT_LENGTH + 1}/{end - CONTEXT_LENGTH})")
        return [l for ln in lines.values() for l in (ln["truth"], ln["filtered"], ln["forecast"])]

    ani = animation.FuncAnimation(fig, step, frames=range(CONTEXT_LENGTH, end), interval=STEP_PAUSE_SEC * 1000, repeat=False, blit=False)

    if SAVE_PATH:
        ani.save(SAVE_PATH, writer="pillow", fps=max(1, int(1 / STEP_PAUSE_SEC)))
    else:
        plt.show()


if __name__ == "__main__":
    run()
