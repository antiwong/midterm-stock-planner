#!/usr/bin/env python3
"""
Run All Tests
=============
Run the complete test suite.
"""

import sys
import subprocess
from pathlib import Path

if __name__ == '__main__':
    project_root = Path(__file__).parent.parent
    
    # Run pytest
    result = subprocess.run(
        ['python', '-m', 'pytest', 'tests/', '-v', '--tb=short'],
        cwd=project_root
    )
    
    sys.exit(result.returncode)
