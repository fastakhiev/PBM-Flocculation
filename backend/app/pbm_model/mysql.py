# --- START OF FILE mylsq_fast.py ---

import numpy as np
from scipy.integrate import solve_ivp
from app.pbm_model.aggregationdF import aggregationdF
from app.pbm_model.convertVDM import convertVMD
from app.pbm_model.alphaest import alphaest

def mylsq_fast(teta, nonorm_initial, dFnorm_initial, G, dcurrent_initial, dFmax, do, nref_initial, dFref_initial, imax, x, y, data):
    amax, B, gama = teta
    if any(p < 0 for p in teta):
        return 1e12


    Yo = np.concatenate((nonorm_initial, np.array([dFnorm_initial]))).flatten()
    
    t_eval = data[:, 0]
    t_span = [t_eval[0], t_eval[-1]]

    Alpha = alphaest(x, y, imax, amax)

    sol = solve_ivp(
        aggregationdF,
        t_span,
        Yo,
        method='BDF',
        t_eval=t_eval,
        args=(Alpha, B, G, dcurrent_initial, dFmax, do, nref_initial, dFref_initial, gama, imax),
        rtol=1e-3, atol=1e-4
    )


    if sol.status != 0:
        return 1e12
        
    Y_result = sol.y.T 

    y_cal = []
    for i in range(len(t_eval)):
        nonorm_i = Y_result[i, :imax]
        dFnorm_i = Y_result[i, imax]
        
        no_i = nonorm_i * nref_initial
        dFo_i = dFnorm_i * dFref_initial
        
        vmd_i = convertVMD(no_i, dFo_i, do)
        y_cal.append(vmd_i * 1e-3)

    y_obs = data[:, 1]
    
    if len(y_cal) != len(y_obs):
        return 1e12
        
    lsq = np.sum((np.array(y_obs) - np.array(y_cal))**2)
    
    print(f"teta: [amax={teta[0]:.4f}, B={teta[1]:.2f}, gama={teta[2]:.4f}] -> lsq: {lsq:.2f}")

    return lsq