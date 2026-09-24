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
step it ended on, the player's final position, the coins collected and the ones
still out, and whether the player reached the level's checkpoint. The same moves
on the same level always end the same way.

`headless.play_all(level, move_lists)` plays many lists at once, stepping the
runs together so they share one set of dots, and reports each run as `play`
would. `headless.Runs(level, move_lists)` plays them the same way one step at a
time, so they can be drawn as they go.

### Teaching an AI to beat the game

```
uv run worlds-easiest-game train 300
```

trains a population of 300 characters to beat every level in turn, with no
window, as fast as the machine allows. A character plays by movement alone, from
its own list of moves (one of the eight directions or standing still, each held
for 12 steps, a tenth of a second), until it dies, beats the level, or its moves
run out. The first generation's lists are 10 random moves long, and each
generation adds 3 more, up to the level's time limit. Each level has its own,
at least twice as long as a perfect run of it takes: 15 seconds on level 1, and
up to 50 seconds on level 6.

After each generation, every character is scored by where its run ended: how far
it still had to walk along the corridors, never through a wall, to its next
target. On a level with coins the goal only counts once every coin is collected,
so the targets are the coins it has not collected yet, whichever is the shortest
walk away, and then the goal. On level 9 the checkpoint is a target too, until
the character reaches it. Every coin collected, and the checkpoint reached, is a
large step up in score: a character that has reached one more target always
scores above one that has not, wherever each ended. Beating the level scores
highest, and higher the sooner it happens. Dying scores a little less than
stopping at the same place, but less than a tile of progress is worth, so
pushing on beats hanging back. The best character carries over to the next
generation unchanged, so the best score never drops, and the rest are children
of characters picked more often the better they scored, each a copy of its
parent's moves with 1.5% of them changed at random.

Learning goes level by level. Once a character beats a level, its winning moves
are kept as that level's solution, and a new population starts on the next
level, from its spawn. Once the last level is beaten, the kept solutions together
are one run of the whole game, and the command replays it end to end, level by
level, printing when each level was beaten again and how long the whole game
took.

Each level starts with a line naming it, and each generation prints one line:
its number, the best score, how far the best character ended from its next
target (and on a level with coins, how many it collected), how many characters
died, and whether one beat the level. Beating a level prints the generation
that did it, how long training on the level took, and the length of the winning
list. Training stops once every level is beaten, or when a level has had
`--generations` generations (1000 unless given) without being beaten, naming
that level and exiting with status 1. The same `--seed` always trains the same
way; without one a random seed is used, and printed. `train --help` lists the
other settings: `--mutation`, `--hold`, `--first-moves`, `--growth`,
`--time-limit` (which, if given, every level gets instead of its own), and how
much each scoring rule counts (`--progress-weight`, `--death-penalty`,
`--speed-weight`).

With 300 characters, the defaults usually beat level 1 within 30 generations,
in under 10 seconds, and level 2 within about a minute. They do not beat the
whole game yet: training stops at level 3, where no character finds its way out
through the moving gap in the ring of dots.
`uv run python game/main.py train 300` does the same.

### Watching it learn

```
uv run worlds-easiest-game train 300 --watch
```

trains the same way, taking the same options, but in the game window, on each
level as the game draws it. Every character of the generation plays at once,
at the game's normal speed, each drawn as the red player square; a character
that dies disappears. A coin is drawn until every character drawn has collected
it. A generation ends once every character has died or used up its moves, and
the next one starts straight away, so the first generations, with their short
lists, flash by in about a second each and later ones run longer. Once a
character beats the level, the window moves on to the next level, and a new
population starts there. These are the very runs the learner scores and breeds
from.

Instead of the top bar, a line of white text at the top left shows the level
being learned, the generation, how many of its characters are still alive, and
how many steps its run has taken, with a hint line for the keys under it:

- F switches to fast mode, which trains as fast as the machine allows and only
  draws where training has got to every thirtieth of a second, and back.
- B switches between drawing every character and drawing only the best one.
  The readout still counts the whole generation. The best one is the best
  character of the generation before, which the learner carries over unchanged,
  until a dot touches it; before there is one (in the first generation) or once
  it has died, it is whichever character still alive is closest to beating the
  level, by the same measure it is scored by.
- Q, or closing the window, quits.

Once the last level is beaten, the window replays the whole game from the kept
solutions, each level's winning run in turn from level 1 to the last, at
normal speed, and then shows where the last one ended until you quit. If a
level is not beaten within `--generations` generations, training stops there,
on that level. The command still prints the same training lines as without
`--watch`, though the replay is only shown in the window, not printed, and it
exits with status 1 unless every level was beaten by the time the window closed.
