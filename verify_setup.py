"""
verify_setup.py

Quick sanity check that all required data-analytics libraries
(from requirements.txt) are installed and importable, and prints
each one's version.

Run with:
    python verify_setup.py
"""

import importlib
import sys

# (import name, display name)
LIBRARIES = [
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("matplotlib", "matplotlib"),
    ("seaborn", "seaborn"),
    ("plotly", "plotly"),
    ("scipy", "scipy"),
    ("statsmodels", "statsmodels"),
    ("sklearn", "scikit-learn"),
    ("jupyter_core", "jupyter"),
    ("ipykernel", "ipykernel"),
    ("openpyxl", "openpyxl"),
    ("xlrd", "xlrd"),
    ("dotenv", "python-dotenv"),
    ("tqdm", "tqdm"),
]


def main():
    print(f"Python: {sys.version.split()[0]} ({sys.executable})\n")

    ok, failed = [], []

    for import_name, display_name in LIBRARIES:
        try:
            module = importlib.import_module(import_name)
            version = getattr(module, "__version__", "unknown")
            print(f"[OK]   {display_name:<15} {version}")
            ok.append(display_name)
        except ImportError as e:
            print(f"[FAIL] {display_name:<15} not installed ({e})")
            failed.append(display_name)

    print(f"\n{len(ok)}/{len(LIBRARIES)} libraries OK.")

    if failed:
        print(f"Missing: {', '.join(failed)}")
        print("Install with: pip install -r requirements.txt")
        sys.exit(1)
    else:
        print("All libraries installed correctly.")


if __name__ == "__main__":
    main()
