import numpy as np

def alphaest(x, y, imax, amax):
    """
    Estimate the collision efficiency between aggregates.
    
    Args:
    - x (float): Constant for the exponential term.
    - y (float): Constant for the denominator power term.
    - imax (int): Maximum size index (number of size classes).
    - amax (float): Maximum collision efficiency factor.
    
    Returns:
    - alpha (numpy.ndarray): Collision efficiency matrix of size (imax, imax).
    """
    # Initialize an empty matrix for alpha
    alpha = np.zeros((imax, imax))
    
    # Loop through all pairs of size classes (i, j)
    for i in range(imax):
        for j in range(imax):
            hmin = min(i+1 , j+1 )  # i and j are 1-indexed in the MATLAB code, so we adjust by adding 1
            hmax = max(i+1 , j+1 )
            
            # Calculate alpha(i, j) using the provided formula
            alpha[i, j] = (np.exp(-x * (1 - (hmax / hmin))**2) / (hmax * hmin)**y) * amax
            j=j+1
        i=i+1
    return alpha

# Example usage:
#x = 0.1    # example constant
#y = 0.1    # example constant
#imax = 10  # example number of size classes
#amax = 1   # example maximum collision efficiency

# Calculate the alpha matrix
#alpha_matrix = alphaest(x, y, imax, amax)
#print("Collision Efficiency Matrix (alpha):")
#print(alpha_matrix)
