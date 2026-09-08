import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")  # avoid libomp double-init abort (numpy and torch both bundle OpenMP on macOS)
os.environ.setdefault("OMP_NUM_THREADS", "1")           # avoids an OMP pthread_mutex_init segfault during inference on macOS

import numpy as np
from chronos import Chronos2Pipeline

# 90% interval -> std, assuming an approximately Gaussian predictive distribution
_Z_90 = 1.2815515655446004


class Chronos2Forecaster:
    def __init__(self, device="cpu"):
        self.pipeline = Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map=device)

    @property
    def max_context_length(self):
        return self.pipeline.model_context_length

    @property
    def max_prediction_length(self):
        return self.pipeline.model_prediction_length

    def forecast(self, context_df, future_df, state_columns, exog_columns, horizon):
        pred_df = self.pipeline.predict_df(
            context_df,
            future_df=future_df,
            prediction_length=horizon,
            quantile_levels=[0.1, 0.5, 0.9],
            id_column="item_id",
            timestamp_column="timestamp",
            target=list(state_columns),
        )
        out = {}
        for col in state_columns:
            sub = pred_df[pred_df["target_name"] == col]
            std = (sub["0.9"].to_numpy() - sub["0.1"].to_numpy()) / (2 * _Z_90)
            out[col] = {"mean": sub["predictions"].to_numpy(), "var": std**2}
        return out
