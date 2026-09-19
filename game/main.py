'''Launcher for `uv run python game/main.py`.

The game itself lives in the installable `worlds_easiest_game` package under
`src/`, so the console script and this launcher run the same code.
'''

from worlds_easiest_game import main

if __name__ == '__main__':
    main()
