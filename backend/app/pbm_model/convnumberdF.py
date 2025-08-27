import numpy as np
import matplotlib.pyplot as plt

def convnumberdF(do, N, dF, timeplot):
    """
    Calculate aggregate collision diameter, volume, and number distribution.
    
    Parameters:
    do (float): Primary particle diameter in nm.
    N (np.ndarray): Number concentration of aggregates for each size bin (time x size bins).
    dF (np.ndarray): Fractal dimensions for each time step (time x 1).
    timeplot (int): Time index to plot the results.
    
    Returns:
    np.ndarray: D (aggregate collision diameters in microns).
    np.ndarray: Vol (volumetric distribution).
    np.ndarray: Numcalc (calculated number distribution in percentage).
    """
    m, n = N.shape  # Get the shape of N (m: time steps, n: size bins)
    
    # Convert primary particle diameter to cm
    d1 = do * 1e-7
    
    # Initialize arrays
    Di = np.zeros((m, n))  # Characteristic floc collision diameters
    TotalN = np.zeros(m)   # Total number concentrations
    Nest = np.zeros((m, n)) # Nest array
    Ni = np.zeros((m, n))  # Normalized number concentration
    Vi = np.zeros((m, n))  # Volume for each section
    vi = np.zeros((m, n))  # Individual volume for each size bin
    TotalV = np.zeros(m)   # Total volume for each time step
    Volume = np.zeros((m, n))  # Volume fraction for each section
    
    # Calculate Nest and TotalN
    for row in range(m):
        for col in range(n):
            Nest[row, col] = N[row, col] * (2 ** (col))  # Adjusting for the fractal scaling
        TotalN[row] = np.sum(Nest[row, :])  # Sum up to get the total number for each time step
    
    # Calculate Ni, Di, Vi, and TotalV
    for row in range(m):
        dFrow = dF[row]  # Fractal dimension for the current time step
        for col in range(n):
            Ni[row, col] = Nest[row, col] / TotalN[row]  # Normalized number concentration
            Di[row, col] = (2 ** ((col) / dFrow)) * d1  # Characteristic diameter
            vi[row, col] = (4 * np.pi / 3) * ((Di[row, col] / 2) ** 3)  # Volume of the aggregate in cm^3
            Vi[row, col] = N[row, col] * vi[row, col]  # Volume for the given section
        TotalV[row] = np.sum(Vi[row, :])  # Total volume for the time step
    
    # Calculate Volume fraction
    for row in range(m):
        for col in range(n):
            Volume[row, col] = Vi[row, col] / TotalV[row]  # Volume fraction for each section
    
    # Convert to percentage for number distribution and volumetric distribution
    Numcalc = Ni * 100  # Normalized number distribution in percentage
    Vol = Volume * 100  # Volumetric distribution in percentage
    
    # Convert diameter to microns
    D = Di * 1e4  # Convert diameter from cm to microns
    
    # Plotting the result for the specified time step
    Dplot = D[timeplot, :]
    Numplot = Vol[timeplot, :]
    
    plt.figure()
    plt.semilogx(Dplot, Numplot, 'k.-')
    plt.xlabel('Aggregate collision diameter (microns)')
    plt.ylabel('%Volume')
    plt.title('Volume Distribution vs. Collision Diameter')
    plt.grid(True)
    plt.show()

    return D, Vol, Numcalc

# Example usage of the function:
#do = 100  # Primary particle diameter in nm
#N = np.array([[100, 200, 300], [150, 250, 350], [120, 220, 320]])  # Example number concentrations (time x size bins)
#dF = np.array([2.5, 2.6, 2.7])  # Example fractal dimensions for each time step
#timeplot = 1  # Time step to plot (index)

# Call the function
#D, Vol, Numcalc = convnumberdF(do, N, dF, timeplot)
