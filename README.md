### Game

Recreating the game "World's hardest game"

### Running it

```
uv run worlds-easiest-game
```

The game opens on a menu; click Start to play the level. Move with WASD.
Touching a blue dot sends you back to the start, and the dots back to theirs.
Press Q or close the window to quit.

Dependencies (pygame, and the game itself) come from uv, which installs them
into the project environment on first run.

`uv run python game/main.py` starts the same game if you prefer launching the
script directly.
