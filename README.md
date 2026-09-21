### Game

Recreating the game "World's hardest game"

### Running it

```
uv run worlds-easiest-game
```

The game opens on a menu; click Start to play the first level. Move with WASD.
Touching a blue dot sends you back to the start, the dots back to theirs, and
any coins you picked up back to where they were. Collect every yellow coin, then
reach the level's goal, a green zone (usually the one on the far side, but on
level 3 the one you start in), to finish the level and move on to the next.
After the last level you win: click Restart to play again from level 1, or Quit
to close the game.
Press Q or close the window to quit.

Dependencies (pygame, and the game itself) come from uv, which installs them
into the project environment on first run.

`uv run python game/main.py` starts the same game if you prefer launching the
script directly.
