'''Launcher for `uv run python game/main.py`.

The game itself lives in the installable `worlds_easiest_game` package under
`src/`, so the console script and this launcher run the same code. The sys.path
line lets this file work straight from a checkout, before the project is
installed.
'''

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from worlds_easiest_game import main

if __name__ == '__main__':
    main()
