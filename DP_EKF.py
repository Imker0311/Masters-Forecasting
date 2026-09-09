def kalman_update(pred_mean, pred_var, measurement, measurement_var):
    k = pred_var / (pred_var + measurement_var)
    fused_mean = pred_mean + k * (measurement - pred_mean)
    fused_var = (1 - k) * pred_var
    return fused_mean, fused_var


class StateFilter:
    def __init__(self, state_names, measurement_variance):
        self.state_names = list(state_names)
        if isinstance(measurement_variance, dict):
            self.r = dict(measurement_variance)
        else:
            self.r = {name: measurement_variance for name in self.state_names}

    def update(self, pred_means, pred_vars, measurements):
        fused_means, fused_vars = {}, {}
        for name in self.state_names:
            fused_means[name], fused_vars[name] = kalman_update(
                pred_means[name], pred_vars[name], measurements[name], self.r[name]
            )
        return fused_means, fused_vars
