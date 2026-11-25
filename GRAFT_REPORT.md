# Graft field report: building `feat/platformer`

*Written by Claude (Opus 5.5) after using [Graft](https://graft-workspace.vercel.app) v0.2.0 on macOS (APFS, M3) for one real task in this repo.*

## The task
I explored Sumi no Kage as a 2D platformer. The finished work has three coloured-ink heroes (Swordsman, Gunslinger, Archer) and a vertical descent through the mine under the Kurogane Shrine, modelled on `docs/reference/platformer/layout.jpeg`. It also has goons, two bosses (the Oni Captain and the Drowned Maw), maces, lifts, arena gates, and a neon zone behind a sealed rift. Partway through, the brief changed: you asked for bosses and goons, a locked portal, an ink-only stage and real level design. The details are in [docs/platformer.md](docs/platformer.md).

The result is about 3,700 lines of new GDScript plus 3 shaders. None of the existing files were touched apart from one main-menu button and a README section.

## What I did with Graft
```sh
graft init                      # register the repo as a Root
graft new platformer            # workspace from HEAD (da70c87)
# ...all edits, Godot imports and screenshot runs happened inside "$(graft path platformer)"
graft radar                     # "No overlaps between live grafts."
graft ls                        # state / changed files / disk use
graft materialize platformer --branch feat/platformer
```

## What I loved
- **It kept me out of your working tree.** Root has about 40 uncommitted changes: modified `.blend` and `.glb` binaries, an untracked ronin/katana in progress, and so on. Working in a graft meant I could not accidentally stage, overwrite or re-export any of it, and I didn't have to stash anything. For an agent dropped into a dirty repo, this was the biggest win.
- **Creation is effectively free.** `graft new` took 0.07 s (206 files reflinked, 27 written from git objects). It cost nothing to start, and it would cost nothing to throw away.
- **It's a real checkout.** The graft was an ordinary working tree on branch `graft/platformer`, so `git status`, Godot, Python and `sed` all just worked. I didn't have to learn any new tooling to use it.
- **`graft ls` is a nice at-a-glance view.** It showed a `ronin-katana` graft from an earlier session, marked *integrated*. That told me another agent had worked here, and that `radar` had nothing to warn about.
- **`materialize --branch` fits exactly what you asked for:** "put this on a new branch", without touching what Root has checked out.

## Pain points
- **The path has a space in it.** Graft home is `~/Library/Application Support/graft/...`, so every shell command needed quoting. `graft doctor` warns about this (good) and suggests `GRAFT_HOME`. A default without spaces on macOS would remove a whole class of mistakes.
- **A graft starts from HEAD, not from your working tree.** That is correct for isolation, but you have to keep it in mind. The platformer reference images were untracked in Root, so I had to copy them into the graft by hand. Something like `graft new --with-untracked docs/reference/platformer` would have helped.
- **Cold engine cache.** `game/.godot/` is git-ignored, so the graft started without Godot's import cache. That meant a full re-import, and Godot's class cache needed an `--editor --quit` scan before my new `class_name`s resolved. One headless `--import` hung and had to be killed. `--clone-ignored game/.godot` exists for exactly this; I found it in `--help` after the fact. A hint in `graft new` output along the lines of "ignored build dirs detected: game/.godot" would have saved time.
- **`graft log` only works for virtual (NFS/FUSE) grafts.** I used the default reflink backend, so I had no op log of what I wrote. That's fine, but it's surprising the first time you run it.
- **`graft run` and the sandbox didn't fit this workload.** Godot writes to `~/Library/Application Support/Godot` (outside the graft), so I ran it directly instead of confining it. Being able to declare extra writable paths per command (without a `graft.toml` + `trust` round-trip) would make confined runs practical for game engines.
- **Unclear which landing command to use.** There's a choice between `integrate` (merge queue, test gate, lands on Root's checked-out branch by default) and `materialize --branch`, which writes **one commit**, and it isn't obvious which fits "make me a branch". I used `materialize`. It gave no way to set the commit message, so I reworded the commit afterwards in a temporary `git worktree`.

## Would I use it again?
Yes, especially in a repo with uncommitted work I must not disturb, and whenever more than one agent is working at once. With a single agent and a single task its value is mostly isolation and a clean landing. The features I didn't need this time (radar, claims, plan, and the integrate queue with test gates) look aimed at the multi-agent case, which is where I'd expect Graft to pay off most.

## How the work was verified (honest scope)
- `--pf-shots` drives a scripted bot through the select screen and every section. It checks that the Oni gate closes on entry and the lid opens on its death (the Oni is killed by script), and that the Maw activates. It also captures the screenshots in `docs/renders/platformer/`. The run finished with 0 engine errors.
- No human has played it yet. Jump distances in the map were reasoned out from the movement constants (about 4 tiles high, about 6 tiles across), not playtested, and balance is untuned.
