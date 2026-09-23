### Game

Recreating the game "World's hardest game"

### Running it

```
uv run worlds-easiest-game
```

The game opens on a menu; click Start to play the first level. Move with WASD.
While you play, a black bar across the top of the window shows the coins you
have on this level out of its total (top left), which level you are on out of
all of them (top middle), and how many times you have died
since you pressed Start or Restart (top right).
Touching a blue dot sends you back to the start, the dots back to theirs, and
any coins you picked up back to where they were. Collect every yellow coin, then
reach the level's goal, a green zone, to finish the level and move on to the next.
The goal is the starting zone on level 3, the middle zone on level 5, and the
lower-left zone on level 6.
Level 9 has a checkpoint, the green zone in the middle of the course: once you
have reached it, touching a dot sends you back there instead of to the start.
The dots and coins still go back to where they were.
After the last level you win: click Restart to play again from level 1, or Quit
to close the game.
Press Q or close the window to quit.

Dependencies (pygame, and the game itself) come from uv, which installs them
into the project environment on first run.

`uv run python game/main.py` starts the same game if you prefer launching the
script directly.

### Developer mode

Developer-only: launch with `--dev` (`uv run worlds-easiest-game --dev`, or
`uv run python game/main.py --dev`) to enable god mode. Press T during a level to
toggle it; while it is on, a "GOD MODE" label shows in the bottom-left corner and
touching a blue dot does nothing (and is not counted as a death), so you can reach
the end of the game to check it.
Without `--dev`, T does nothing.

### Playing a level from a list of moves

`worlds_easiest_game.headless.play(level, moves)` plays one level with no window,
as fast as the machine allows, one move per game step (1/120 of a second). A move
is one of the eight directions or standing still (`headless.Move`), and moves the
player exactly as holding those keys would. The run ends at the first death, on
beating the level, or when the moves run out, and the result reports which, the
step it ended on, the player's final position, and the coins collected. The
same moves on the same level always end the same way.
