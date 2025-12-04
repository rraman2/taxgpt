"""
Path setup helper for examples.
Automatically finds tenforty library and its dependencies.
"""

import sys
from pathlib import Path


def setup_tenforty_path():
    """
    Set up Python path to find tenforty library and its dependencies.
    Tries to use venv site-packages if available.
    """
    project_root = Path(__file__).parent.parent
    tenforty_src = project_root / "tenforty" / "src"
    tenforty_venv = project_root / "tenforty" / "venv"
    
    # Try to use venv site-packages for dependencies
    if tenforty_venv.exists():
        # Find the Python version directory dynamically
        lib_dir = tenforty_venv / "lib"
        if lib_dir.exists():
            # Look for pythonX.Y directories
            python_dirs = [d for d in lib_dir.iterdir() if d.is_dir() and d.name.startswith("python")]
            if python_dirs:
                # Use the first one found (should only be one)
                venv_site_packages = python_dirs[0] / "site-packages"
                if venv_site_packages.exists() and str(venv_site_packages) not in sys.path:
                    sys.path.insert(0, str(venv_site_packages))
    
    # Add tenforty src to path
    if tenforty_src.exists() and str(tenforty_src) not in sys.path:
        sys.path.insert(0, str(tenforty_src))
    
    return tenforty_src.exists()


# Auto-setup when imported
setup_tenforty_path()

