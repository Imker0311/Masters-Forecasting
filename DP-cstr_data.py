import numpy as np
import pandas as pd
import h5py

STATE_COLUMNS = {"C_A": "C_A", "T": "T", "T_C": "T_C", "h": "h", "Q_vec": "Q", "Q_c_vec": "Qc"}
EXOG_COLUMNS = {"F1": "E_R", "F2": "U_Ac", "F4": "T_F", "F5": "C_F", "F6": "T_CF", "F7": "Q_F"}


def load_cstr_data(downsample=20, input_file="CSTR_InputVectors.h5", sim_file=None):
    sim_file = sim_file or f"CSTR_SimulationData_ds{downsample}.h5"

    with h5py.File(sim_file, "r") as f:
        data = {col: f[key][:, 0] for key, col in STATE_COLUMNS.items()}
        n = len(data["C_A"])

    # state[j] corresponds to raw input index 1 + j, strided by `downsample`
    idx = 1 + np.arange(n) * downsample

    with h5py.File(input_file, "r") as f:
        for key, col in EXOG_COLUMNS.items():
            data[col] = f[key][idx, 0]
            data[f"{col}_active"] = f[f"{key}.plt"][idx]

    df = pd.DataFrame(data)
    df["item_id"] = "cstr"
    df["timestamp"] = pd.date_range("2026-01-01", periods=n, freq=f"{downsample}s")
    ordered = ["item_id", "timestamp"] + list(STATE_COLUMNS.values()) + list(EXOG_COLUMNS.values())
    ordered += [f"{c}_active" for c in EXOG_COLUMNS.values()]
    return df[ordered], downsample
