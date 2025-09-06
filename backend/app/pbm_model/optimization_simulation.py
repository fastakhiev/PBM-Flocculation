# --- START OF FILE pbm_tasks.py ---

import pandas as pd
from io import StringIO
import json
from app.core.celery_worker import celery
from app.core.redis_sync import redis_sync
from scipy.integrate import solve_ivp
from app.pbm_model.optimization import run_optimization, run_optimization_ga
from app.pbm_model.realtime import run_realtime_simulation
from app.pbm_model.metrics import calculate_gof
from app.pbm_model.aggregationdF import aggregationdF
from app.pbm_model.convertVDM import convertVMD
from app.pbm_model.alphaest import alphaest
import numpy as np


def check_status(task_id):
    c = celery.AsyncResult(task_id)
    return c


def stop_task(task_id):
    redis_sync.set(f"stop:{task_id}", 1)

    result = celery.AsyncResult(task_id, app=celery)
    result.revoke(terminate=True, signal="SIGKILL")


@celery.task(bind=True)
def optimization_task(self, csv_str_exp, csv_str_init, g, do, e1_index, optimization_algorithm, dosage):
    try:
        csv_data_init = pd.read_csv(StringIO(csv_str_init), sep=';', engine='python')
        csv_data_exp = pd.read_csv(StringIO(csv_str_exp), sep=';', skiprows=2, engine='python')
        for col in ['Time(min)', 'd43', 'DF']:
            if col in csv_data_exp.columns:
                csv_data_exp[col] = pd.to_numeric(csv_data_exp[col].astype(str).str.replace(',', '.'), errors='coerce')
        csv_data_exp.dropna(inplace=True)

        G_val = float(g)
        do_val = float(do)

        if optimization_algorithm == "Differential Evolution Algorithm (DEA)":
            results = run_optimization(csv_data_exp, G_val, do_val, csv_data_init["initial_distribution"].tolist(), e1_index, dosage)
        elif optimization_algorithm == "Genetic Algorithm (GA)":
            results = run_optimization_ga(csv_data_exp, G_val, do_val, csv_data_init["initial_distribution"].tolist(), e1_index, dosage)

        texp = csv_data_exp['Time(min)'].values
        dexp = csv_data_exp['d43'].values

        imax, x, y = 30, 0.1, 0.1
        a_dist = np.array(csv_data_init["initial_distribution"].tolist())
        b_dist = np.zeros(imax - len(a_dist))
        no = np.concatenate([a_dist, b_dist])
        dFo = csv_data_exp['DF'].values[0]
        dFmax_str = str(csv_data_exp.iloc[-1, 2])
        dFmax = pd.to_numeric(dFmax_str.replace(',', '.'), errors='coerce')

        nref_initial = np.where(no > 0, no, 1)
        dFref_initial = dFo
        nonorm_initial = no / nref_initial
        dFnorm_initial = dFo / dFref_initial
        dcurrent_initial = convertVMD(no, dFo, do_val)
        Yo = np.concatenate((nonorm_initial, np.array([dFnorm_initial]))).flatten()

        Alpha_opt = alphaest(x, y, imax, results['amax'])

        sol = solve_ivp(
            aggregationdF, [texp[0], texp[-1]], Yo, method='BDF', t_eval=texp,
            args=(Alpha_opt, results['B'], G_val, dcurrent_initial, dFmax, do_val,
                  nref_initial, dFref_initial, results['gama'], imax),
            rtol=1e-5, atol=1e-6
        )

        d_model = []
        for i in range(len(texp)):
            no_i = sol.y[:imax, i] * nref_initial
            dFo_i = sol.y[imax, i] * dFref_initial
            vmd_i = convertVMD(no_i, dFo_i, do_val)
            d_model.append(vmd_i * 1e-3)
        d_model = np.array(d_model)

        gof_value = calculate_gof(dexp, d_model)
        results['gof'] = gof_value

        print(f"Goodness of Fit (GoF) = {gof_value:.2f}%")

        redis_sync.set(str(self.request.id), json.dumps(results))
        return results

    except Exception as e:
        error_result = {"success": False, "message": str(e)}
        redis_sync.set(str(self.request.id), json.dumps(error_result))
        return error_result


@celery.task(bind=True)
def simulation_task(self, opt_params, G, do, csv_str, mode = "realtime"):
    try:

        if mode == 'realtime':
            init_state = redis_sync.get("previous")
            df_test_raw = pd.read_csv(StringIO(csv_str), sep=';', skiprows=2, engine='python')
            last_row = df_test_raw.iloc[-1]
            dFmax_val_str = str(last_row.values[2]) if len(last_row.values) > 2 else '0'
            dFmax_val = pd.to_numeric(dFmax_val_str.replace(',', '.'), errors='coerce')
            df_test_clean = df_test_raw.iloc[:-1].copy()
            for col in ['Time(min)', 'd43', 'DF']:
                df_test_clean[col] = pd.to_numeric(df_test_clean[col].astype(str).str.replace(',', '.'),
                                                   errors='coerce')
            df_test_clean.dropna(inplace=True)

            if init_state is not None:
                loaded_init_state = json.loads(init_state)
                df_test_clean['Time(min)'] += loaded_init_state['t']
            else:
                loaded_init_state = None

            results_df, final_state = run_realtime_simulation(
                opt_params,
                df_test_clean,
                dFmax_val=dFmax_val,
                G=float(G),
                do=float(do),
                initial_state=loaded_init_state
            )
        else:
            raise ValueError("")

        redis_sync.set(str(self.request.id), json.dumps({
            "time": results_df["time"].tolist(),
            "VMD_corrected": results_df["VMD_corrected"].tolist(),
            "DF_corrected": results_df["DF_corrected"].tolist(),
            "time_exp": df_test_clean["Time(min)"].tolist(),
            "d43_exp": df_test_clean["d43"].tolist(),
            "df_exp": df_test_clean["DF"].tolist()
        }))
        return None

    except Exception as e:
        error_result = {"success": False, "message": str(e)}
        redis_sync.set(str(self.request.id), json.dumps(error_result))
        return error_result