import argparse
import json
import _bootstrap
from skate4d.validation import validate

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate synchronized multi-view frames")
    parser.add_argument("dataset")
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.dataset), indent=2))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"INVALID: {error}\n")
