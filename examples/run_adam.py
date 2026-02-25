import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from cdiscbuilder.adam.adam_derivation.engine import AdamDerivation

def main():
    base_dir = Path(__file__).parent
    spec_path = base_dir / "adam" / "specs" / "adsl.yaml"
    
    print(f"\n--- Generating ADaM ADSL ---")
    engine = AdamDerivation(str(spec_path))
    engine.save()
    print(f"\nSuccess! ADaM datasets created.")

if __name__ == "__main__":
    main()
