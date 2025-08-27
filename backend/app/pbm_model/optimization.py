import numpy as np
import time
from scipy.optimize import differential_evolution
from app.pbm_model.objective_function import mylsq_fast
from geneticalgorithm import geneticalgorithm as ga
from app.pbm_model.convertVDM import convertVMD
import matplotlib

matplotlib.use('Agg')

def run_optimization(csv_data, G, do, initial_distribution, e1_index, dosage):
    texp = csv_data['Time(min)'].values
    dexp = csv_data['d43'].values
    dF_exp = csv_data['DF'].values
    data = np.column_stack((texp, dexp))

    dFo = dF_exp[0]
    dFmax = dF_exp[-1]

    imax = 30
    x, y = 0.1, 0.1
    a_dist = np.array(initial_distribution)
    b_dist = np.zeros(imax - len(a_dist))
    no = np.concatenate([a_dist, b_dist])

    nref_initial = np.where(no > 0, no, 1)
    nonorm_initial = no / nref_initial
    dFref_initial = dFo
    dFnorm_initial = dFo / dFref_initial
    dcurrent_initial = convertVMD(no, dFo, do)

    bounds = [(0.01, 1.0), (1.0, 100.0), (0.01, 2.0)]
    args = (nonorm_initial, dFnorm_initial, G, dcurrent_initial, dFmax, do, nref_initial, dFref_initial, imax, x, y, data)

    start_time = time.time()

    result = differential_evolution(
        mylsq_fast, bounds, args=args, maxiter=100, disp=True, tol=0.01
    )

    end_time = time.time()
    print(f"\nTime: {end_time - start_time:.2f} seconds.")

    if result.success:
        teta_opt = result.x
        return {
            "success": True, "amax": teta_opt[0], "B": teta_opt[1], "gama": teta_opt[2],
            "g": G, "do": do, "cpamm": e1_index, "dosage": dosage,
            "optimization_time": round(end_time - start_time, 2), "error": result.fun, "message": "Optimization successful."
        }
    else:
        return {"success": False, "message": result.message}


def run_optimization_ga(csv_data, G, do, initial_distribution, e1_index, dosage):
    texp = csv_data['Time(min)'].values
    dexp = csv_data['d43'].values
    dF_exp = csv_data['DF'].values
    data = np.column_stack((texp, dexp))
    dFo = dF_exp[0]
    dFmax = dF_exp[-1]
    imax = 30
    x, y = 0.1, 0.1
    a_dist = np.array(initial_distribution)
    b_dist = np.zeros(imax - len(a_dist))
    no = np.concatenate([a_dist, b_dist])
    nref_initial = np.where(no > 0, no, 1)
    nonorm_initial = no / nref_initial
    dFref_initial = dFo
    dFnorm_initial = dFo / dFref_initial
    dcurrent_initial = convertVMD(no, dFo, do)

    args = (nonorm_initial, dFnorm_initial, G, dcurrent_initial, dFmax, do, nref_initial, dFref_initial, imax, x, y,
            data)

    def fitness_function(X):
        return mylsq_fast(X, *args)


    varbound = np.array([[0.01, 1.0], [1.0, 100.0], [0.01, 2.0]])

    algorithm_param = {
        'max_num_iteration': 100,
        'population_size': 50,
        'mutation_probability': 0.1,
        'elit_ratio': 0.01,
        'crossover_probability': 0.5,
        'parents_portion': 0.3,
        'crossover_type': 'uniform',
        'max_iteration_without_improv': None,
        'disable_plot': True
    }

    print("Запускаю оптимизацию с Genetic Algorithm...")
    start_time = time.time()

    model = ga(function=fitness_function, dimension=3, variable_type='real', variable_boundaries=varbound,
               algorithm_parameters=algorithm_param)
    model.run()

    end_time = time.time()
    print(f"\nTime: {end_time - start_time:.2f} seconds.")
    if model.best_variable is not None:
        teta_opt = model.best_variable
        best_fun = model.best_function

        return {
            "success": True, "amax": teta_opt[0], "B": teta_opt[1], "gama": teta_opt[2],
            "g": G, "do": do, "cpamm": e1_index, "dosage": dosage,
            "optimization_time": round(end_time - start_time, 2), "error": best_fun,
            "message": "Genetic Algorithm optimization finished."
        }
    else:
        return {"success": False, "message": "Genetic Algorithm failed to find a solution."}