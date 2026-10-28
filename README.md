# Masters-Forecasting
Contains all files related to forecasting for my Masters. This keeps the forecasting separate from the model.

## Unseen-fault test set (`CSTR_SimulationData_Unseen`)
Tests how the forecaster handles faults it has never seen in its context. It is the same size as the eval set: 100,000 raw 1 s samples, which gives 5,000 samples after downsampling by 20.

Files:
- `CSTR-Input-Unseen.ipynb` generates `CSTR_InputVectors_Unseen.h5` (seed 7).
- `CSTR-Simulation.ipynb` produces `CSTR_SimulationData_Unseen.h5`, and `CSTR-Downsample.ipynb` produces `CSTR_SimulationData_Unseen_ds20.h5`. Both were run with only their filenames swapped.

The data has two regions:
- **Context, raw `[0, 75000)` / ds20 `[0, 3750)`.** It contains 16 single faults that never overlap. The last 1,500 raw samples are at baseline.
  - U_Ac (F2): 4 events.
  - C_F (F5): 4 events, 2 positive and 2 negative.
  - T_CF (F6): 4 events, 2 positive and 2 negative.
  - T_F (F4): 4 events, **all positive**.
  - **E_R (F1) and Q_F (F7) never occur.** The E_R column stays constant. Q_F carries only the usual AR1 sensor noise.
- **Test, raw `[75000, 100000)` / ds20 `[3750, 5000)`.** It contains 6 cases, with about 1,300 raw samples (65 ds20 samples) of settling time between them. Each new element appears exactly once. When you forecast a later case, the earlier test cases sit in the context, but they reveal nothing about the case being forecast:
  - the overlaps only combine faults that were already seen, in their seen directions;
  - the unseen faults and T_F− never appear in an overlap.

### Test cases, as indexed in `Chronos2-Forecast.ipynb`
In `Chronos2-Forecast.ipynb`, the `events` list has 25 entries. An overlap case adds one entry for each of its faults. Point `EVENT_INDEX` at the fault that starts first.

`HORIZON` (ds20 samples) runs up to the start of the next case. Set it explicitly: with `None`, the horizon reaches 500 samples past the event and runs into the following cases.

| Case | What it tests | `EVENT_INDEX` | ds20 start | `HORIZON` | Faults (raw sample span, magnitude) |
|---|---|---|---|---|---|
| 1 | Unseen fault: E_R | -9 | 3816 | 178 | F1 E_R [76304, 78568), +285.9 K |
| 2 | Overlap: U_Ac + C_F− | -8 | 3994 | 217 | F2 U_Ac [79872, 82027), −238.6; F5 C_F [80668, 82907), −0.161 |
| 3 | Opposite direction: T_F− (context has only T_F+) | -6 | 4211 | 170 | F4 T_F [84211, 86301), −89.4 K |
| 4 | Overlap: T_F+ + T_CF− | -5 | 4381 | 220 | F4 T_F [87605, 89665), +81.1 K; F6 T_CF [88549, 90702), −32.6 K |
| 5 | Unseen fault: Q_F (positive) | -3 | 4601 | 173 | F7 Q_F [92006, 94166), +0.512 L/s |
| 6 | Overlap: C_F+ + T_CF+ | -2 | 4774 | 226 | F5 C_F [95470, 97622), +0.151; F6 T_CF [96463, 98693), +30.6 K |

Case 5 (Q_F) is the hardest. In the whole context, `h` and `Q` are flat apart from noise, because Q_F is the only fault that moves them. In this case `Q` steps from 1.67 to 2.18 L/s and `h` spikes. Cases 2–4 also take `Qc` and `T_C` beyond anything in the context (`Qc` falls to 0.02, and `T_C` ranges from 307 to 387 K).

The other indices are -7 (C_F, the second fault of case 2), -4 (T_CF, case 4) and -1 (T_CF, case 6). Each of these starts its forecast partway through the first fault of its case.

To run the forecast notebook on this set, change its two load paths to `CSTR_SimulationData_Unseen_ds20.h5` and `CSTR_InputVectors_Unseen.h5`, keeping `DOWNSAMPLE = 20`.
