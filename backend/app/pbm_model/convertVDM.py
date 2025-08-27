import numpy as np

def convertVMD(N, dF, do):
    """
    Calculate the volume mean diameter (VMD) of aggregates.
    
    Parameters:
    N (np.ndarray): Array of number concentrations of aggregates for each size bin.
    dF (float): Fractal dimension.
    do (float): Primary particle diameter in nm.
    
    Returns:
    float: Volume mean diameter in nm.
    """
    d1 = do * 1e-7  # Convert primary particle diameter to cm
    n = len(N)  # Number of size bins
    
    # Calculate characteristic floc diameters (Di) for each size bin
    Di = np.zeros(n)
    for i in range(n):
        Di[i] = (2 ** ((i) / dF))*d1  # Calculate Di for each section i
        i=i+1
    D=Di
    # Calculate the volume-weighted VMD
    TopVMDi = np.zeros(n)
    BotVMDi = np.zeros(n)
    
    for col in range(n):
        TopVMDi[col] = N[col] * D[col]**4
        BotVMDi[col] = N[col] * D[col]**3
        col=col+1
    
    # Calculate VMD
    TopVMD = np.sum(TopVMDi)
    BotVMD = np.sum(BotVMDi)
    
    VMD = TopVMD / BotVMD
    VMDm = VMD * 1e7  # Convert VMD to nm
    
    return VMDm

# Example usage of the function:
#N = np.array([100, 200, 300])  # Example number concentrations for each size bin
#dF = 2.5  # Example fractal dimension
#do = 100  # Example primary particle diameter in nm

# Call the function to calculate the volume mean diameter (VMD)
#VMDm = convertVMD(N, dF, do)

# Print the result
#print("Volume Mean Diameter (VMD) in nm:", VMDm)
