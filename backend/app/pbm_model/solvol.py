import numpy as np

def solvol(Y, do):
    """
    Calculate the total solid volume for lumped discrete population balance.
    
    Args:
    - Y (numpy.ndarray): The population balance data (each column represents a different size class).
    - do (float): The primary particle size in nanometers.
    
    Returns:
    - TotalVol (numpy.ndarray): The total volume of aggregates.
    """
    # Convert primary particle diameter to meters
    ro = (do / 2) * 1e-9  # Convert to meters
    
    # Volume of a single primary particle (in cubic meters)
    u1 = (4/3) * np.pi * ro**3
    Y=Y.reshape(-1,1)
    # Number of rows (m) and columns (jmax) in Y
    jmax,m=Y.shape
    
    vo = np.zeros(jmax)

    # Calculate volumes for each size class
    for j in range(1, jmax + 1):
        vo[j-1] = u1 * (2 ** (j-1)) # Volume for each size class
        j=j+1
    vi=vo
    Vol=vi
   
    # Transpose Y (this is equivalent to Y' in MATLAB)
   
    
    # Calculate total volume per size class
    Totalvoli = np.zeros((jmax, m))
    Sumvoli = np.zeros(m%2)
    for i in range(m):
        Totalvoli[:, i] = Y[:,i]* Vol
        Sumvoli[i] = np.sum(Totalvoli[:,i])
        i = i+1
    
    # Sum the volumes for each aggregate
    
    
    # Return the total volume for each time step
    return Sumvoli

# Example usage:
# Assuming Y is a 2D numpy array where each row is a time step and each column is a size class
#Y = np.array([1,2,3])  # Just an example, replace with actual data
#do = 100  # Primary particle size in nanometers

# Calculate the total solid volume
#TotalVol = solvol(Y, do)
#print("Total Volume of Aggregates:", TotalVol)
