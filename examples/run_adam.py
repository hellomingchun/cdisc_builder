import argparse
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from cdiscbuilder.adam.adam_derivation.engine import AdamDerivation

def main():
    base_dir = Path(__file__).parent
    
    parser = argparse.ArgumentParser(description="Run ADaM derivation pipeline.")
    parser.add_argument("--spec", default=str(base_dir / "adam" / "specs" / "adsl.yaml"), help="Path to ADaM YAML spec file")
    
    args = parser.parse_args()

    print(f"\n--- Generating ADaM ADSL from {Path(args.spec).name} ---")
    engine = AdamDerivation(args.spec)
    engine.save()
    print(f"\nSuccess! ADaM datasets created.")

if __name__ == "__main__":
    main()

