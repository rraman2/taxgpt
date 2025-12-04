"""
Path setup helper for examples.
This module handles finding and setting up the tenforty library path.
"""

import sys
from pathlib import Path


def setup_tenforty_path():
    """
    Set up Python path to find tenforty library.
    Also attempts to use venv if available.
    """
    project_root = Path(__file__).parent.parent
    tenforty_src = project_root / "tenforty" / "src"
    tenforty_venv = project_root / "tenforty" / "venv"
    
    # Try to use venv Python if available
    if tenforty_venv.exists():
        venv_python = tenforty_venv / "bin" / "python"
        if venv_python.exists():
            # Note: We can't switch interpreters, but we can add venv site-packages
            venv_site_packages = tenforty_venv / "lib" / "python3.9" / "site-packages"
            if venv_site_packages.exists() and str(venv_site_packages) not in sys.path:
                sys.path.insert(0, str(venv_site_packages))
    
    # Add tenforty src to path
    if tenforty_src.exists() and str(tenforty_src) not in sys.path:
        sys.path.insert(0, str(tenforty_src))
    
    return tenforty_src.exists()


# Auto-setup when imported
setup_tenforty_path()

