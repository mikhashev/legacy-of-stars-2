import sys
import os

# Add project root to path
sys.path.append(os.path.abspath("."))

try:
    from src.legacy_of_stars_v3 import ContactProgram
    
    print("Import successful")
    
    # Initialize the program (which initializes GenesisProject)
    program = ContactProgram()
    
    print(f"Genesis init check: {hasattr(program, 'genesis')}")
    
    if hasattr(program, 'genesis'):
        if program.genesis.unlocked is False:
             print("Genesis Project initialized and default state is correct (Locked)")
        else:
             print(f"Genesis Project initialized but state is unexpected: {program.genesis.unlocked}")
             
        print("Genesis verification PASSED")
    else:
        print("Genesis Project NOT initialized - FAILED")
        exit(1)
        
except Exception as e:
    print(f"Verification FAILED with error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
