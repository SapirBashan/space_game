import numpy as np

def _check_diff():
    mat1 = np.ones((254, 64))
    mat2 = np.ones((256, 64))
    try:
        diff = mat1 - mat2
    except ValueError as e:
        print(f"Error caught: {e}")
        
    
_check_diff()
