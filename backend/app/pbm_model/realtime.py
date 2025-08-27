# --- START OF FILE realtime.py (ФИНАЛЬНАЯ ВЕРСИЯ С УПРАВЛЕНИЕМ СОСТОЯНИЕМ) ---

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from app.pbm_model.convertVDM import convertVMD
from app.pbm_model.alphaest import alphaest
from app.pbm_model.aggregationdF import aggregationdF


# --- Вспомогательные функции ---
def get_measurement(time, t_exp, d43_exp, df_exp):
    """Имитирует получение данных с датчика."""
    d43_measured = np.interp(time, t_exp, d43_exp)
    df_measured = np.interp(time, t_exp, df_exp)
    return d43_measured, df_measured


def correct_distribution_robust(N_pred, dFo, do, d43_measured):
    """Робастный ЛОГАРИФМИЧЕСКИЙ алгоритм коррекции."""
    N_corr = N_pred.copy()
    if np.sum(N_corr) < 1e-12: return N_corr
    total_volume_initial = np.sum(N_corr * (2 ** np.arange(len(N_corr))))
    if total_volume_initial < 1e-12: return N_corr
    for _ in range(10):
        d43_current = convertVMD(N_corr, dFo, do)
        if np.isnan(d43_current) or d43_current < 1e-9: return N_pred
        ratio = d43_measured / d43_current
        if abs(ratio - 1) < 0.02: break
        strength = np.exp(-abs(np.log(ratio))) * 0.5
        imax = len(N_corr)
        correction_vector = np.linspace(-1, 1, imax)
        multiplicative_factor = (ratio ** strength) ** correction_vector
        N_corr_new = N_corr * multiplicative_factor
        current_volume = np.sum(N_corr_new * (2 ** np.arange(len(N_corr_new))))
        if current_volume > 1e-12:
            scale_factor = total_volume_initial / current_volume
            N_corr = N_corr_new * scale_factor
        else:
            return N_corr
    return N_corr


def run_realtime_simulation(opt_params, csv_data, G, do, dFmax_val, initial_state=None):
    amax, B, gama = opt_params['amax'], opt_params['B'], opt_params['gama']
    texp, dexp, dF_exp = csv_data['Time(min)'].values, csv_data['d43'].values, csv_data['DF'].values
    dFmax = dFmax_val

    imax, x, y = 30, 0.1, 0.1
    Alpha = alphaest(x, y, imax, amax)

    a_ref = np.array([4.60e8, 6.31e9, 1.24e9, 2.89e6, 4.24e7, 8.77e6, 5.79e5, 1.34e5, 2.32e4, 1.89e3])
    b_ref = np.zeros(imax - len(a_ref))
    no_ref = np.concatenate([a_ref, b_ref])
    nref_initial = np.where(no_ref > 0, no_ref, 1)
    dFref_initial = dF_exp[0]

    if initial_state:
        if texp[0] < initial_state['t']:
            raise ValueError("")

        current_t = initial_state['t']
        N_corr = np.array(initial_state['N'])
        dF_corr = initial_state['dF']
    else:
        current_t = 0
        N_corr, dF_corr = no_ref.copy(), dF_exp[0]

    N_pure, dF_pure = N_corr.copy(), dF_corr

    time_step, t_history_end = 0.1, texp[-1]

    time_hist = [current_t]
    VMD_corr_hist = [convertVMD(N_corr, dF_corr, do) * 1e-3]
    DF_corr_hist = [dF_corr]
    VMD_pure_hist = [convertVMD(N_pure, dF_pure, do) * 1e-3]

    while current_t < float(t_history_end):
        t_span = [current_t, min(current_t + time_step, t_history_end)]
        if t_span[0] >= t_span[1]: break

        d_vmd_corr = convertVMD(N_corr, dF_corr, do)
        nonorm_corr = N_corr / nref_initial
        dFnorm_corr = dF_corr / dFref_initial
        Yo_corr = np.concatenate((nonorm_corr, [dFnorm_corr])).flatten()
        sol_corr = solve_ivp(aggregationdF, t_span, Yo_corr, method='BDF',
                             args=(Alpha, B, G, d_vmd_corr, dFmax, do, nref_initial, dFref_initial, gama, imax))

        d_vmd_pure = convertVMD(N_pure, dF_pure, do)
        nonorm_pure = N_pure / nref_initial
        dFnorm_pure = dF_pure / dFref_initial
        Yo_pure = np.concatenate((nonorm_pure, [dFnorm_pure])).flatten()
        sol_pure = solve_ivp(aggregationdF, t_span, Yo_pure, method='BDF',
                             args=(Alpha, B, G, d_vmd_pure, dFmax, do, nref_initial, dFref_initial, gama, imax))

        current_t = t_span[1]

        last_Y_pure = sol_pure.y[:, -1]
        last_Y_pure[last_Y_pure < 0] = 0
        N_pure = last_Y_pure[:imax] * nref_initial
        dF_pure = last_Y_pure[imax] * dFref_initial

        last_Y_pred = sol_corr.y[:, -1]
        last_Y_pred[last_Y_pred < 0] = 0
        N_predicted = last_Y_pred[:imax] * nref_initial
        dF_predicted = last_Y_pred[imax] * dFref_initial

        d43_measured, _ = get_measurement(current_t, texp, dexp, dF_exp)
        N_corr = correct_distribution_robust(N_predicted, dF_predicted, do, d43_measured * 1000)
        dF_corr = dF_predicted

        time_hist.append(current_t)
        VMD_corr_hist.append(convertVMD(N_corr, dF_corr, do) * 1e-3)
        DF_corr_hist.append(dF_corr)
        VMD_pure_hist.append(convertVMD(N_pure, dF_pure, do) * 1e-3)


    final_state = {
        "t": current_t,
        "N": N_corr.tolist(),
        "dF": dF_corr
    }

    results_df = pd.DataFrame({
        'time': time_hist,
        'VMD_corrected': VMD_corr_hist,
        'DF_corrected': DF_corr_hist,
        'VMD_pure_forecast': VMD_pure_hist
    })

    return results_df, final_state
