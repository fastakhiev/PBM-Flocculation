import numpy as np
from app.pbm_model.radius import radius

def aggregationdF(t, Y, Alpha, B, G, dcurrent, dFmax, do, nref, dFref, gama, imax):
    # Y = [N, dF] is a row vector (2D array)
    # dYdt = [dNdt; ddFdt] return a column vector (2D array)
    Y=Y.reshape(-1,1)
    dYdt = np.zeros((imax + 1, 1))  # a column vector of size (imax+1)x1

    # Constants
    v = 1e-2  # kinematic viscosity (cm^2/s)
    e = G**2 * v  # energy dissipation rate (cm^2/s^3)
    temp = 296  # temperature in K
    kb = 1.380622e-23  # Boltzmann constant (J/K)
    miu = 1e-3  # viscosity of surrounding medium (Pa.s)

    Nref = np.transpose(nref)  # transpose of nref
    N = Y[:imax, 0] * Nref  # size N = imax x 1
    dFcurrent = Y[imax, 0] * dFref

    # Calculate collision radius for class i
    Rc = radius(do, imax, dFcurrent)

    dNdt = np.zeros(imax)  # Initialize dN/dt
    dNnormdt = np.zeros(imax)  # Initialize normalized dN/dt

    for i in range(imax):
        # First term: birth in interval i due to collision between particles in intervals i-1 and 1 to i-2
        if i - 2 >= 0:
            first = np.zeros(i)
            for j in range(i - 1):
                Beta1a = 1.294 * G * (Rc[i - 1] + Rc[j])**3  # shear kernel, cm^3/s
                Beta1b = ((2 * kb * temp) / (3 * miu)) * ((1 / (Rc[i - 1] * 1e-2)) + (1 / (Rc[j] * 1e-2))) * ((Rc[i - 1] * 1e-2) + (Rc[j] * 1e-2)) * 1e6  # Brownian kernel, cm^3/s
                Beta1 = Beta1a + Beta1b
                first[j] = 2**(j - i + 1) * Alpha[i - 1, j] * Beta1 * N[i - 1] * N[j]
            sumfirst = np.sum(first)
        else:
            sumfirst = 0

        # Second term: birth in interval i due to collisions between particles in interval i-1 and i-1
        if i - 1 >= 0:
            Beta2a = 1.294 * G * (Rc[i - 1] + Rc[i - 1])**3  # shear kernel, cm^3/s
            Beta2b = ((2 * kb * temp) / (3 * miu)) * ((1 / (Rc[i - 1] * 1e-2)) + (1 / (Rc[i - 1] * 1e-2))) * ((Rc[i - 1] * 1e-2) + (Rc[i - 1] * 1e-2)) * 1e6  # Brownian kernel, cm^3/s
            Beta2 = Beta2a + Beta2b
            second = (1 / 2) * Alpha[i - 1, i - 1] * Beta2 * (N[i - 1] ** 2)
        else:
            second = 0

        # Third term: death by aggregation in interval i due to collision of particles in intervals i and 1 to i-1
        if i - 1 >= 0:
            third = np.zeros(i)
            for j in range(i):
                Beta3a = 1.294 * G * (Rc[i] + Rc[j])**3  # shear kernel, cm^3/s
                Beta3b = ((2 * kb * temp) / (3 * miu)) * ((1 / (Rc[i] * 1e-2)) + (1 / (Rc[j] * 1e-2))) * ((Rc[i] * 1e-2) + (Rc[j] * 1e-2)) * 1e6  # Brownian kernel, cm^3/s
                Beta3 = Beta3a + Beta3b
                third[j] = 2**(j - i) * Alpha[i, j] * Beta3 * N[j]
            sumthird = np.sum(third) * N[i]
        else:
            sumthird = 0

        # Fourth term: death by aggregation of particles in intervals i and i to imax
        fourth = np.zeros(imax)
        if i < imax-1:
            p = 0
            for j in range(i, imax):
                Beta4a = 1.294 * G * (Rc[i] + Rc[j])**3  # shear kernel, cm^3/s
                Beta4b = ((2 * kb * temp) / (3 * miu)) * ((1 / (Rc[i] * 1e-2)) + (1 / (Rc[j] * 1e-2))) * ((Rc[i] * 1e-2) + (Rc[j] * 1e-2)) * 1e6  # Brownian kernel, cm^3/s
                Beta4 = Beta4a + Beta4b
                fourth[p] = Alpha[i, j] * Beta4 * N[j]
                p += 1
            sumfourth = np.sum(fourth) * N[i]
        else:
            sumfourth = 0

        # Fifth term: death by fragmentation of flocs in interval i
        if i > 0:
            ebi = B / Rc[i]
            Si = (4 / (15 * (22 / 7)))**(1/2) * G * np.exp(-ebi / e)
            fifth = Si * N[i]
        else:
            fifth = 0

        # Sixth term: breakage of flocs greater than i into flocs of size i (binary breakage)
        if i < imax-1:
            R = 2  # V(i+1)/V(i)
            ebi = B / Rc[i+1]
            Si = (4 / (15 * (22 / 7)))**(1/2) * G * np.exp(-ebi / e)
            sixth = R * Si * N[i+1]
        else:
            sixth = 0

        # Calculate aggregation and fragmentation terms
        agg = sumfirst + second - sumthird - sumfourth
        frag = -fifth + sixth

        # Calculate dN/dt and normalized dN/dt
        dNdt[i] = (agg + frag) * 60  # Multiply by 60 to match the units in the original MATLAB code
        dNnormdt[i] = dNdt[i] / Nref[i]

    # Update the output derivative (dYdt)
    dYdt[:imax] = dNnormdt.reshape(-1,1)
    ddFdt = gama * (dFmax - dFcurrent)
    ddFnormdt = ddFdt / dFref
    dYdt[imax] = ddFnormdt

    return dYdt.ravel()

# Example usage of the function:
# Define your input parameters here
# t = time (not used in the function but needed for compatibility)
# Y = current state vector (N and dF)
# Alpha, B, G, etc. are arrays/matrices from the system

# t = 0
# Y = np.array([...])  # Replace with your actual data for N and dF
# Alpha = np.array([...])  # Example matrix for Alpha
# B = 1.0  # Example value for B
# G = 1.0  # Example value for G
# dcurrent = 0.1  # Example value for current fragmentation size
# dFmax = 10.0  # Example value for max fragmentation size
# do = 1.0  # Example value for initial size
# nref = np.array([...])  # Replace with actual reference number density
# dFref = 1.0  # Example value for reference fragmentation size
# gama = 1.0  # Example value for gama
# imax = 10  # Example number of size bins

# Call the function
# result = aggregationdF(t, Y, Alpha, B, G, dcurrent, dFmax, do, nref, dFref, gama, imax)
