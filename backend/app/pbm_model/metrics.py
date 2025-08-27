import numpy as np


def calculate_gof(d_exp, d_model):
    if len(d_exp) != len(d_model):
        raise ValueError("error")

    n = len(d_exp)
    p = 3

    dof = n - p
    if dof <= 0:
        raise ValueError("error")
    sum_sq_diff = np.sum((d_exp - d_model) ** 2)

    st_error = np.sqrt(sum_sq_diff / dof)
    mean_d_exp = np.mean(d_exp)

    if mean_d_exp == 0:
        return 0.0

    gof = (mean_d_exp - st_error) / mean_d_exp
    return gof * 100