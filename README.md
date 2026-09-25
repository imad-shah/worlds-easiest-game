Recreating the popular flash game "World's Hardest Game", but making it easy by having AI beat it

### Running it

```
uv run worlds-easiest-game
```

### 300 players

![demo](assets/images/weg-1.gif)

### Fast mode (Toggleable by F while watching the AI)

![demo](assets/images/weg-fast-mode.gif)

The game opens on a menu with two options

1. Click `Start game` to play the game yourself (Move with WASD)
2. `Watch the AI beat the game` to watch the learner train on every level

Press `Esc` in any level to go back to the menu  
Press `Q` or close the window to quit

### Dependencies

pygame and the game itself come from `uv`, which installs them into the project environment on first run

### Developer mode

Run `uv run worlds-easiest-game --dev` to enable god mode. Press `T` during a level to toggle it.

### Teaching an AI to beat the game

Pick `Watch the AI beat the game` on the menu to watch an AI learn every level in turn.
The box under it sets how many characters play at once (300 to start with)

#### How a character plays

A character is just a list of moves. Each move is held for a tenth of a second and is one of nine choices:

- one of the eight directions
- or standing still

It plays its list until it dies, beats the level, or runs out of moves.
Lists never grow past the level's time limit (15 seconds on level 1, up to 50 on level 6)

#### How runs are scored

When every character is done, each one is scored by where its run ended:
how far it still had to walk to its next target, going around walls, not through them

- The targets are the coins not collected yet, then the goal (and the checkpoint on level 9)
- Collecting one more coin always beats being closer with fewer
- Beating the level scores highest, and sooner is better
- Dying counts as ending 3 tiles further back, so waiting safely for a gap beats rushing in

#### How the next generation is made

1. The best character is kept unchanged, so the best score never drops
2. The best fifth of the characters become parents
3. Every other character is a child of a random parent
4. A child copies its parent's moves up to a few moves before where the parent's run ended,
   then adds a few new random moves that go past that point

So if the parent died, its child usually tries something different just before that spot.
If the parent ran out of moves, the child carries on from there

New random moves often repeat the one before, so straight dashes and long waits are common.
Parents are picked from all the different places the runs got to, so the characters do not all crowd into one dead end

#### Level by level

```
level 1: generation 1, 2, 3 ... until one character beats it -> keep its moves
level 2: new characters start here ...                        -> keep its moves
...
level 9: ...                                                  -> keep its moves
```

If a level is not beaten within 1000 generations, training stops there

#### Replaying the win

Once the last level is beaten, the kept moves of all levels together are one run of the whole game.
The window replays it from level 1 to the end, which takes about a minute and a half
