# Movement Sandbox — Design Log

A living reference for the movement-tech sandbox game (working title). Spiritually inspired by
Super Smash Bros. Melee (momentum tech) and Mirror's Edge (freerunning fantasy), but not bound
to Melee's rules where we prefer something else.

This doc tracks two things:
1. **Character stats/modifiers** — the tunable numeric knobs that define how movement feels.
   Once the prototype exists, you can reference this doc to make precise requests like
   "increase Ground Max Speed by 10%."
2. **Decision log** — a dated record of design choices and the reasoning behind them.

**Code location:** as of 2026-09-19, the actual game code lives in `movement-sandbox/` (multiple
files: `index.html` + `src/*.js`), not the old single `movement-sandbox.html`, which is no longer
maintained. See the architecture entry near the end of the decision log for why and how it's split up.

---

## System properties

These aren't per-character stats, they're rules the whole simulation follows.

| Property | Decision |
|---|---|
| Simulation model | Deterministic, fixed-timestep (required to keep rollback netcode possible later, even though v1 is single-player) |
| Input model | Digital-first (on/off) as the baseline for both keyboard and controller; controller analog range may add nuance later, but nothing in v1 *requires* analog input |
| Movement plane | Strict 2D — only X (left/right) and Y (jumping) are simulated; no depth/spacing axis. (Revised 2026-09-19: originally shallow 2.5D, changed after playtesting felt like too much.) |
| Multiplayer | None in v1 (single-player sandbox). Rollback netcode is a future goal that constrains the architecture now. |
| Camera | Static, fixed frame showing the entire test area (no follow-cam in v1). Scale reference: character roughly Marth-sized (Melee), stage roughly Battlefield-sized (Melee) |

---

## Architecture watch-list

Most ideas for this game are cheap to try and cheap to undo — a new move, a sound, a pose, a tuning
pass. This list is for the other kind: decisions that would be genuinely expensive to backtrack on
once something is built on top of them. Anything here gets a real "here's the fork and what it
forecloses" conversation before code gets written, even if not explicitly asked for — see Nate's
process preference below.

| Fork | Why it's load-bearing | Status |
|---|---|---|
| Hitbox/hurtbox data model | Every future combat feature (moves, damage, knockback, eventually multiplayer-synced state) builds directly on top of however this is shaped. Picking a model that doesn't fit how moves actually need to behave later would mean reworking every move built on it, not just the model itself. | Not started — no design conversation has happened yet |
| Stage geometry model (single flat floor + solid boundary walls vs. real ledges/platforms) | Determines whether the stage can support Melee-style edge-guarding and multi-level layouts, or stays a flat sandbox forever. Blocked ledge grabbing specifically (needed floors/edges to exist as a concept first). | **Resolved 2026-09-20** — see below |
| Multiplayer/rollback integration point | The sim is already deterministic/fixed-timestep specifically to keep this option open, but *how* input/state gets synced (e.g., where input is buffered, how state gets serialized/rolled back) is still undecided. Bolting this on after a lot of single-player-only assumptions creep into the code (e.g., reading real-time input directly instead of from a buffer) would be costly to unwind. | Not started — current code reads input once per render frame, a known simplification flagged as "future networking work" in `main.js` |
| Entity/actor structure (single hardcoded `player` object vs. something that scales to N characters) | Right now there's exactly one `player` state object and all systems (physics, animation, input) are written assuming a single character. Multiplayer or even a second local character would need this generalized — the earlier that's considered, the less rewriting later. | **Resolved 2026-09-20** — see below |
| Moveset ownership model (do all roster characters share one move list, or can they differ?) | Determines whether "give a character a unique ability" needs a real per-character move/data system now, or can keep riding the existing shared-code-plus-different-numbers pattern. Getting this wrong either over-builds a data-driven move system nobody needs yet, or under-builds and requires a rework the moment the first movement exception shows up. | **Decided in direction 2026-09-20** — see below |

**Nate's process preference (2026-09-20):** he'd rather ideas get flagged *before* implementation than
find out later something painted us into a corner. Cheap/reversible ideas (the vast majority) just get
built. Anything that looks like it belongs on this list gets raised first, unprompted.

**2026-09-20 — Entity/actor structure: resolved.** Generalized away from the hardcoded `player`
singleton, ahead of adding any more movement tech, per the reasoning above (every feature added to
`physics.js` while it assumed a singleton was more code to eventually untangle). Nate confirmed he
wants this specifically so future characters can have their own distinct feel, not just exist as
independent instances of an identical character — so stats got bundled into the same generalization
pass rather than done as a separate refactor later. Changes:
- `state.js`: `player` (a single exported object) became `createPlayerState()`, a factory. Call it once
  per character; nothing else changed about the fields it returns.
- `stats.js`: added `DEFAULT_PROFILE = { stats: STATS, anim: ANIM }` — a character's tuning bundled
  into one object. `STATS`/`ANIM` themselves are unchanged and still exported directly (nothing else
  needed converting).
- `physics.js`: every function (`doJump`, `doWallJump`, `fixedUpdate`, `getWallJumpPushDir`) now takes
  the relevant `player`/`profile` as parameters instead of importing a singleton and bare `STATS`/`ANIM`
  globals. Level geometry (`STAGE`, `WALLS`, `WALL_HEIGHT`, `PLAYER_RADIUS`) stayed as direct imports —
  that's shared by every character, not per-character, so it doesn't belong on the profile.
- `main.js`: now the one place that calls `createPlayerState()` and picks `DEFAULT_PROFILE`, then
  threads both through `fixedUpdate()` each tick.
A second character today is "call `createPlayerState()` again, give it a different profile object, add
it to the render/update loop" — no engine code changes required. Multiplayer/rollback plumbing and the
hitbox/hurtbox model are unaffected and still open items above.

Verified via the real running game loop (not just direct physics calls): dash-dance running reached
exactly Ground Max Speed (14.0) over ~295 real physics ticks with `dirX` flowing correctly end-to-end;
running into a wall correctly zeroed horizontal speed; jumping, wall contact, and the dash-dance turn
sound all fired with zero console errors afterward.

**2026-09-20 — Moveset ownership model: decided in direction, nothing to build yet.** Asked Nate how
different a future roster's movesets should be, since it determines whether a real per-character move
data model is needed now or can keep waiting. His answer, paraphrased: movement (running, jumping,
crouching, etc.) should be shared code with different numbers for the large majority of the roster —
exactly the profile pattern already built — but he expects Melee-style exceptions eventually (a
character with a movement ability others don't have), and combat moves will definitely be
per-character once those exist. Conclusion: no new architecture needed right now — the profile system
already covers "shared code, different numbers." The pattern to reach for **when** the first movement
exception actually comes up (not preemptively) is a capability flag on the profile (e.g. `canWallJump`,
`extraJumps`) that the shared physics code checks, rather than inventing a full pluggable-move-list
system for a single exception. The real moveset/hitbox data model (see the row above) stays correctly
deferred until actual combat-move design starts — building it now would mean guessing at requirements
nobody's decided yet.

**2026-09-20 — Stage geometry redesign: ledges, platforms, and kill zones.** Nate wants this to become a
real Melee clone (full roster, shared physics rules, individually tuned). Asked which Melee mechanics
from his list (knockback/percent, ledge grabbing, ledges, platforms, kill zones) were ready to design
now vs. blocked on combat. Knockback/percent stays deferred — it can't exist without a hit to cause it,
so it's really part of the already-deferred hitbox/moveset conversation, not a separate item. The other
four are one fork (how does the stage represent floor surfaces at all), and unlike combat they need
zero hitboxes to make sense, so tackled now. Also confirmed with Nate that a full engine port (to a free
engine, likely for polish) is the eventual plan — this codebase is a prototype whose *design* is meant
to survive that, not its code, which reinforces designing mechanics carefully now even though this
exact implementation won't ship.

Replaced the old model (one infinite flat floor + solid walls at the stage edges acting as the only
boundary) with:
- **Main stage**: still the only solid floor (blocks from below, spans exactly `±STAGE.halfX`), but now
  bounded — walking past either end falls off instead of hitting a wall. Landing requires
  `Math.abs(pos.x) <= STAGE.halfX`, unlike the old unconditional `pos.y <= 0` check.
- **Ledges**: derived automatically from the main stage's two ends (`LEDGES` in stats.js), not separate
  data. Grabbing snaps to a hang position out past the edge; from there, holding toward the stage climbs
  up, holding away (or down) drops, and jump does a ledge jump (its own up speed + a kick back toward
  the stage). A regrab lockout (0.4s) prevents instantly re-grabbing after any of the three exits.
  Caught one real bug in testing: without a check, walking straight off the edge while still holding
  that direction would instantly re-grab the ledge you just walked past. Fixed by refusing a grab when
  held input points away from the stage — the same rule real ledge mechanics use to let you intentionally
  fall past a ledge instead of always catching it.
- **Platforms**: one-way floating floor segments (`PLATFORMS` in stats.js) — land on from above, pass
  through from below, or drop through deliberately by holding down. One example platform added at
  `y = 6` to prove the mechanic out.
- **Kill zone**: bounds well outside the stage (`KILL_BOUNDS`); crossing any of them resets to
  `SPAWN_POINT` at rest. This isn't optional once ledges exist — nothing else stops a fall or a shove
  past the edge from continuing forever, since the solid boundary walls are gone. No stocks/game-over
  yet, just the reset — that's meta-state, not physics.
- Wall-jumping off the stage edges is gone (they're ledges now, not walls) — `getWallJumpPushDir()` only
  checks the interior WALLS. Interior wall-jump/wall-slide are otherwise completely unaffected.

Verified extensively via direct deterministic physics-loop tests (more reliable in this environment than
real-time browser interaction, per the established testing approach): walking off an edge while holding
away falls past without grabbing; releasing before falling past grab range grabs correctly; climb-up,
drop, and ledge-jump all produce the exact expected position/velocity; the regrab lockout correctly
blocks an instant re-grab and expires on schedule; platforms correctly support landing from above,
drop-through via holding down, and pass-through from below; the kill zone correctly resets position/
velocity/state on crossing any bound; and existing mechanics (wall-slide, wall-jump, dash-dance, double
jump) all still behave identically to before. Confirmed the new platform mesh renders in the live scene
graph at the correct position (visually out of the current camera's frame, tuned for the older, smaller
stage — a framing fix, not a functional issue).

**2026-09-20 — Battlefield-style platform layout, and why the platform was invisible.** Nate asked for
a proper Melee Battlefield layout (top platform, two side platforms, ledges either side, blast zone
below) and flagged that the platform added earlier that same day wasn't visible at all in-game.
Re-laid-out `PLATFORMS` (stats.js) into a top platform (`-3` to `3`, `y=10`) and two side platforms
(`±6.4` to `±10`, `y=6`) — the side platforms specifically start past `x=6.4` to clear the interior
wall-jump WALLS sitting right below them (`x=±6`, occupying `5.7`-`6.3`): two separately-added features
that turned out to physically compete for the same space, not something either feature's own design
anticipated.

The invisibility bug had nothing to do with the platform mesh itself (it was correctly in the scene the
whole time) — the camera. `scene.js` sets an initial camera position/lookAt, but `main.js`'s render loop
**overwrites camera position and orientation every single frame** for the landing-shake effect, using
its own hardcoded values tuned back when the stage was flat with no platforms. Editing `scene.js` alone
did nothing, because those numbers never survived past frame 1. Fixed by updating the hardcoded values
in `main.js` (now `(0, 11, 26)` looking at `(0, 5, 0)`, pulled back and aimed higher to fit the full
stage including the top platform, instead of the old `(0, 9, 17)` / `(0, 3.8, 0)`) to match what
`scene.js` now also sets for consistency on the first frame before the loop takes over.

Verified via the scene graph directly (mesh positions/colors for all 5 stage objects: 2 walls, 3
platforms) and a screenshot on a guaranteed-fresh port, confirming the Battlefield silhouette (top
platform centered above, two side platforms symmetric, main stage with the interior walls still where
they were) is now actually visible, not just present in memory. Also hit a caching artifact tied to
`localhost:8732` specifically, independent of the dev server itself (confirmed via direct `fetch` that
the server was serving correct fresh content the whole time) — closing the browser tab and even opening
a brand new one against the same port didn't clear it, only moving to a never-before-used port did. **At
the time, wrongly assumed this was purely a testing-tool artifact that wouldn't affect Nate's own view —
it did** (see below); the real fix was moving the whole project off that port.

**Aside — found and fixed a real dev-server caching bug during this verification.** Plain
`python -m http.server` sends no `Cache-Control` header, so browsers apply heuristic caching and can
keep serving an old cached `.js` file after an edit even on a manual reload — not just a testing
artifact, a real trap for normal iteration (edit a file, reload, and silently still be looking at the
old behavior with no indication anything's stale). Added `no_cache_server.py` (project root): a drop-in
replacement built on the same stdlib `http.server`, which adds `Cache-Control: no-store` to every
response and also strips incoming `If-Modified-Since`/`If-None-Match` so an already-cache-poisoned
client can't keep getting `304`s and reusing its old body. `.claude/launch.json`'s `movement-sandbox`
config now runs this instead of the bare module. `saw-dodge` (the other project) is untouched.

**2026-09-20 — Recovery walls: the stage's own side faces, replacing the mid-stage wall-jump chambers.**
Nate looked at the Battlefield layout above and said it still didn't match, sharing a hand-drawn
reference: red rectangles for the three platforms (symmetric left/right), a black rectangle for the main
stage, with walls descending from the stage's own edges all the way down to the blast zone — used for
wall-jumping/wall-teching back onto the stage when recovering from off-stage, exactly how
Battlefield/Final Destination actually work in Melee. This is a different mechanic than what existed:
the old `WALLS` were two separate mid-stage obstacles (`x=±6`) for practicing wall-jumps on top of the
stage; what Nate wants is the stage's *own* vertical side faces, positioned at the ledges, functioning
as the recovery tool.

Removed the mid-stage wall-jump chambers entirely and replaced `WALLS` with two recovery walls at
`x = ±STAGE.halfX` (same X as `LEDGES` — they're literally the same edge), each carrying its own
`yMin`/`yMax` instead of a shared `WALL_HEIGHT` (removed, no longer meaningful once walls aren't a fixed
height above a floor): `yMin` reaches the kill-zone bound, `yMax` is exactly `0`, the stage surface.
Side platforms simplified to plain symmetric positions (`±5` to `±9`) now that there's no mid-stage
obstacle to dodge.

Two things needed care because the wall now shares space with the ledge above it, which never used to
be a design constraint:
- The `yMax` check uses a strict `<` (`pos.y < wall.yMax`, not `<=`) specifically so a grounded character
  standing exactly at the stage's edge (`y=0`) never counts as touching the wall — with `<=` (or no
  distinction), walking toward the ledge would just hit an invisible wall at the edge instead of letting
  you walk off it, breaking the entire ledge mechanic from last session.
- Ledge-grabbing's hang position sits *inside* the wall's X range by construction (the ledge and the
  wall below it are the same edge). Caught in testing: without an explicit guard, the wall-collision
  resolution loop would clamp a freshly-grabbed hang position straight back onto the wall face, since
  from its perspective a teleport into that zone looks identical to walking into the wall normally.
  Fixed by skipping wall-collision resolution entirely while `ledgeGrabbed`.

Verified via direct physics-loop tests: grounded movement walks straight past the ledge with the wall
not interfering; approaching the wall from below/outside while falling correctly wall-slides (capping at
the normal wall-slide speed) and wall-jumps (correct kick speed/direction, double-jump refreshed) —
identical behavior to the old mid-stage chambers, just relocated; ledge-grab position is provably stable
across multiple ticks after grabbing, confirming the wall-collision guard works; and existing regressions
(dash-dance speed, double jump, platform landing) are all unaffected. Confirmed visually via a screenshot
matching Nate's reference drawing closely: floating stage with descending side walls, top platform, two
symmetric side platforms.

**The real fix for the port-8732 caching problem, since Nate confirmed he was seeing the exact same
stale render (the earlier write-up above wrongly assumed this was a testing-only artifact).** Moved the
`movement-sandbox` dev server off port 8732 entirely — updated `.claude/launch.json` to run on 8850
instead. Whatever was caching independently of the server (confirmed via direct `fetch` that the server
itself always served correct, fresh content) was specific to that port; a fresh port sidesteps it
completely rather than trying to invalidate whatever was holding onto the old state.

**2026-09-20 — Fixed the recovery wall silently stealing every ledge grab.** Nate reported the
right-side ledge felt "slippery." Investigation found a real bug, not a right-specific one: the ledge-
grab check ran independent of wall contact, and since it's evaluated *after* that tick's wall-slide
physics and unconditionally overrides position/velocity when it fires, ledge-grab always won the instant
both conditions were true on the same tick — which, now that the recovery wall sits at the exact same X
as the ledge above it, is most of the usable recovery zone. In practice this means whichever of the two
(wall-grip or ledge-snap) won could flip tick-to-tick on tiny position differences — reading as an
unstable, "slippery" grip rather than a clean catch either way. Fixed by only allowing a ledge grab when
`wallDir === 0` (not currently touching a wall that tick) — wall contact now takes priority; you can still
chain wall-jump into a ledge grab afterward, once you're no longer pressed against the wall.

Tested exhaustively for an actual left/right asymmetry first (wall-slide, wall-jump, ledge-grab-from-
above, climb-up, ledge-jump, and walking off the edge while grounded, mirrored on both sides) — every
pair of results was numerically identical (mirrored exactly), and the raw `LEDGES`/`WALLS`/`PLATFORMS`
data confirmed no typo'd value. No code-level left/right difference found; best read is Nate hit this
same bug and happened to notice it on the right side specifically. Verified the fix directly: approaching
the recovery wall now cleanly wall-slides (clamps to the wall-slide speed, no grab) and wall-jumps
correctly with zero interference from the ledge above it.

**This fix was real but didn't address what Nate was actually seeing** — a good reminder that a found
bug isn't necessarily *the* bug. He clarified afterward: he wasn't fully landing on the right platform,
stuck in the jump animation instead of standing — "ledge" was being used loosely for "platform," not the
ledge-grab mechanic at all. See the next entry for the actual cause and fix.

**2026-09-20 — Fixed the right platform never actually holding a landed character.** `currentFloorBounds()`
(physics.js), used every tick to check whether a grounded character has walked off their current floor,
identified which floor you're on by matching Y height alone. The two side platforms share the same
`y=6`, and `PLATFORMS` lists the left one before the right one — so a character standing on the *right*
platform got matched against the *left* platform's X range (`-9` to `-5`) purely because it's checked
first in the array. Their actual X was never inside those bounds, so the "walked off the floor" check
fired almost immediately after landing, un-grounding them again — which shows up exactly as "not fully
landing, stuck in the jump animation." The left platform only ever worked by coincidence of being first
in the list; the same bug would hit *any* second platform sharing a height with an earlier one. Fixed by
matching on X range too, not just Y, so each platform is identified by where you actually are.

Verified via direct physics-loop tests: landing on the right platform with no drift, drifting toward
center, and drifting toward the outer edge all now land and **stay** grounded continuously (previously
grounded flickered back to `false` within a tick or two of landing) — the left platform, top platform,
main stage, and drop-through were all re-checked and remain correct.

**2026-09-20 — Fixed feet clipping into platforms (but not the main stage).** Once the landing bug above
was fixed, Nate noticed the character's feet visibly sink into a platform while standing on it, unlike
the main stage. Cause: `scene.js`'s platform mesh is a `BoxGeometry` with real thickness (`0.4`), and Box
geometry centers on its own origin — positioning it *at* `plat.y` put the box's **center** there, not its
top face, so the visible top surface sat `0.2` (half the thickness) above where physics actually places a
standing character's feet (`plat.y` exactly). The main stage never had this problem because it's a flat,
zero-thickness `PlaneGeometry` — no center-vs-surface distinction to get wrong. Fixed by offsetting the
mesh's Y position by half the thickness so its top face lands exactly on `plat.y`. Also confirmed the
character rig itself has no hidden offset to compound this: `thighLength + shinLength == hipHeight`
exactly, so the model's own origin already corresponds to feet-at-ground-level with straight legs.
Verified the fix numerically: platform mesh centers are now `plat.y - 0.2`, so their top faces compute to
exactly `10` and `6` — matching `PLATFORMS`' data exactly, not offset.

---

## Character stats / modifiers

Status legend: **Qualitative** = feel decided, exact number not yet set. **Set** = concrete value chosen and tuned in-game. **Planned** = feel not yet decided.

| Stat | What it controls | Current target | Status |
|---|---|---|---|
| Ground Max Speed | Top horizontal speed while running | "Very fast" — should feel like peak precision, not sluggish | Qualitative |
| Ground Acceleration | How quickly you reach Ground Max Speed from a stop, and how fast you can reverse direction | Snappy. Raised sharply (90 → 240) on 2026-09-19 after playtesting felt "slow/sticky" to turn — full-speed reversal went from ~0.31s to ~0.12s | Set (240), still open to further tuning |
| Dash-Dance Turn Behavior | How direction-reversal works while grounded | Instant physics response (can turn on a dime at any time while grounded, no Melee-style "locked into run" commitment window), but with a short, smooth visual turn-around blend so it reads as fast and precise rather than a glitchy teleport | Qualitative — deliberate departure from Melee's run-lock; open to revisiting if it feels wrong once playable |
| Jump Speed | Initial upward velocity for the (single) grounded jump. Height/hang-time are emergent from this + Gravity, not stored directly | Recalculated to 25.3, then 27.5, on 2026-09-19 as Gravity rose (72, then 85), each time specifically to keep jump HEIGHT unchanged (~4.44 units) while shortening hang time further — snappier arcs at the same height | Set (27.5) |
| Double Jump Speed | Initial upward velocity for the double jump | Set to 28.7, then recalculated to 31.2 on 2026-09-19 alongside the Gravity/Jump Speed changes, consistently targeting ~128% of the first jump's height — matching Fox's distinctive trait of a double jump that goes HIGHER than his first jump (most characters, e.g. Marth, are the opposite: ~72%). Verified in-game (before the second gravity bump): double jump gained ~5.96 units vs. the first jump's ~4.66 (ratio ~1.28, matches target) | Set (31.2) |
| Gravity | Downward acceleration while airborne | Raised 45 → 72 → 85 on 2026-09-19, modeled after Melee Fox's much heavier gravity relative to the cast, then nudged a little heavier again for an even faster-feeling arc. Jump Speed is recalculated alongside each change to preserve jump height, so the net effect is progressively shorter hang time, not less height (verified: single jump hang time down to ~570ms, from ~650ms then ~890ms) | Set (85) |
| Max Fall Speed (Terminal Velocity) | Caps how fast gravity can accelerate a fall | Raised 22 → 28 → 33 on 2026-09-19 alongside the Gravity increases, roughly proportional | Set (33) |
| Air Acceleration | How quickly you can redirect horizontal speed while airborne | Raised ~50% (16 → 24) on 2026-09-19, then raised ~50% again (24 → 36) the same day for more left/right control. Time to reach Max Air Speed from a standstill is now ~0.22s (was ~0.33s) | Set (36), still open to further tuning |
| Max Air Speed | Baseline cap on horizontal speed achievable via air control from a standstill (dynamically raised to match carried-over run speed — see Momentum Carry-Into-Jump) | Lowered 10.5 → 5.3 on 2026-09-19 (Fox's air speed is only ~38% of his run speed), then raised to 8 the same day after 5.3 felt too tight in practice | Set (8) |
| Air Friction | Passive deceleration that applies ONLY when no direction is held while airborne (distinct from Air Acceleration, which applies whenever a direction IS held) | Added 2026-09-19 — this was a real missing mechanic, not a tuning issue: with no air friction at all, releasing input mid-air did nothing, so any horizontal speed you picked up was permanent until landing, which read as "unwieldy." Real Melee has this as a separate stat from air acceleration; Fox's is ~25% of his total air acceleration. Set to 6 (25% of our Air Acceleration, 24). Verified in-game: velocity decayed 8 → 7.9 → 7.8 with no input held, exactly matching airFriction × dt per tick, versus staying frozen before this fix | Set (6) |
| Momentum Carry-Into-Jump | Whether horizontal ground speed at the moment of jumping affects your jump | **Revised again 2026-09-19.** History: removed entirely (felt bad, killed all speed) → restored as a dynamic cap that always let entry speed through uncapped → **now clamps to Max Air Speed at the instant of takeoff instead of expanding to match entry speed.** Below the cap, speed carries through untouched (verified: 3 → 3 unchanged); above it, speed snaps down hard (verified: 14 → 5.3) — matching real Melee's behavior for characters with a big gap between ground and air speed (a small gap barely clips anything; our current big gap causes a real, felt loss). A standstill jump is still unaffected either way since entry speed is already 0 | Set (hard clamp to Max Air Speed) |
| Fast-Fall | Command to drop faster than normal gravity | Added 2026-09-19, pressing down while already moving downward (not still rising) originally snapped instantly to Fast Fall Speed, matching what was believed to be Melee's mechanic. **Revised the same day**: Nate felt the instant snap was wrong regardless of Melee accuracy — fast-fall should accelerate like everything else, not teleport to max speed. Now it just raises the fall-speed cap; the same gravity used for a normal fall accelerates you toward it over time. Also lowered again (38 → 34, felt too fast even before this change). Horizontal air control was confirmed already fully independent of downHeld — holding down+direction keeps building sideways speed normally while fast-falling. Verified in-game: velocity ramps smoothly (~4.25/tick-group, matching gravity×dt) rather than snapping; diagonal fast-fall built horizontal speed to 8 while still accelerating downward | Set (fastFallSpeed: 34, gravity-accelerated, no snap) |
| Fast-Fall Gravity Multiplier | How much stronger gravity gets specifically while fast-falling, vs. a normal fall | Added 2026-09-19 — reusing plain gravity (the previous fix) felt unimpactful once the instant snap was removed. Doubling gravity while fast-falling is the middle ground: still a ramp, not a teleport, but noticeably snappier. Verified in-game: velocity steps by exactly 8.5/3-tick-group (2x the normal ~4.25), reaching the -34 cap in ~0.2s instead of ~0.34s | Set (2x) |
| Wavedash-equivalent | Melee-style emergent tech move | Not in v1 — deferred to a later phase | Planned |
| Takeoff Stretch | Cosmetic vertical stretch on the character the instant a jump (single or double) launches | Added 2026-09-19 — sells "coiled energy" being released on takeoff without adding any input delay (no jumpsquat-style wind-up). One signed `bodyStretch` value drives both this and Landing Squash below, easing back to 0 over time. Verified in-game: kicks to +0.22 on jump, decays smoothly afterward | Set (kick +0.22, eases at 1.6/sec) |
| Landing Squash | Cosmetic vertical squash the instant the character touches down | Added 2026-09-19, deliberately kept simple (a scale transform, not a new pose/asset) per the "keep animation barebones" direction. Shares the same `bodyStretch` mechanism as Takeoff Stretch, just a negative kick instead of positive. Verified in-game: kicks to -0.3 on landing, decays smoothly afterward | Set (kick -0.3, eases at 1.6/sec) |
| Double-Jump Leg Tuck | Cosmetic: legs snap to a tighter tuck right when you double-jump, then relax to the normal airborne pose | Added 2026-09-19. Reuses the existing leg-easing system with a temporary, more extreme target angle for a short timer window (0.18s) before falling back to the normal jumpPoseAngle. Verified in-game: timer counts down correctly and legs visibly ease toward the tucked angle on double jump | Set (tuck angle 1.15 rad, 0.18s) |
| Crouch Ease Rate | How fast the crouch squash engages when you hold down while grounded | Set to a much faster rate than the shared landing/takeoff squash rate, specifically so the pose reads as immediate rather than a slow squat. Verified in-game: reaches the full crouch target in exactly 5 frames at 60fps | Set (crouchEaseRate: 4.5, ~5 frames) |
| Crouch Movement Lock | Whether you can run while crouching | Added 2026-09-19 — running-while-crouched looked wrong (a squashed character sprinting at full gait). Holding down now suppresses horizontal acceleration while grounded, so existing speed bleeds off via normal deceleration; you can't build speed again until releasing down. Facing can still change while crouched, just not movement. Verified: held direction + down from full speed skidded to a stop in 8 ticks | Set (movement fully locked while crouching) — **but see idea below** |
| Idea: Dedicated Crouch Movement | Nate liked being able to move while crouching (before the lock above), but wants it to be its own distinct movement mode — not just normal running speed in a squashed pose — rather than either fully locked or fully unrestricted | Explicitly deferred 2026-09-19 to design later (e.g. a slower "crouch-walk" speed cap, distinct from both normal run and the current full lock). Noted here so it isn't lost | Idea — not started |
| Wall Jump | Pressing jump while airborne and touching a side wall kicks you away from it, refreshes the double jump, and turns you to face away from the wall | Added 2026-09-19 against dedicated mid-stage wall-jump chambers. **Revised 2026-09-20**: those chambers were removed and replaced by recovery walls — the main stage's own side faces, extending from the stage surface down to the blast zone (see Recovery Walls row) — so wall-jumping now only happens while recovering from off-stage, not on top of the stage. The mechanic itself (kick away from the wall, refresh double jump) is unchanged. No cooldown on repeated same-wall jumps. Verified: kick lands at exactly the stat values, decays via ordinary air friction afterward, double-jump-ready refreshes, and ordinary double-jumping away from walls is unaffected | Set (Wall Jump Push Speed: 10, Wall Jump Up Speed: 24) |
| Recovery Walls | The main stage's own side faces (not separate mid-stage obstacles) — positioned exactly at the ledges, extending from the stage surface (y=0) down to the blast zone. Used for wall-jumping/wall-teching back onto the stage when recovering from off-stage, matching how Battlefield/Final Destination actually work in Melee | Added 2026-09-20, replacing the old interior wall-jump chambers, per Nate's reference drawing. The wall's top bound is checked with a strict `<` at y=0 specifically so a grounded character standing exactly at the stage's edge never counts as touching it — otherwise walking off the ledge would just get blocked instead of letting you fall past. Caught and fixed a real bug in testing: since the wall now shares the same X position as the ledge above it, grabbing that ledge would get immediately clamped back onto the wall face unless wall collision is explicitly skipped while ledge-grabbed (the hang position sits inside the wall's X range by design) | Set (yMin: kill-zone bound, yMax: 0, positioned at ±STAGE.halfX) |
| Wall Slide | Touching a wall while falling clamps fall speed down to a much slower cap, refreshes the double jump on contact alone, and turns you to face the wall — a real window to react and wall-jump instead of rocketing past | Added 2026-09-19, chosen (over a purely cosmetic pose) in response to "should we make a wallgrab pose?" Fast-fall can't trigger while sliding — the wall grip overrides it outright. Pose is symmetric (bent legs, both arms reaching toward the wall), unlike the jump pose's asymmetric look. Verified: fall speed clamps to exactly the stat value regardless of prior fall speed, double-jump-ready refreshes on contact alone (not just kicking off), and facing correctly turns toward the wall while sliding and away from it on a wall-jump (a same-tick stale-flag bug in that last interaction was caught and fixed during testing) | Set (Wall Slide Speed: 5) |
| Ledge Grab | Falling near either end of the main stage (and not holding away from it) snaps you to hanging on the ledge; from there, toward-stage climbs up, away/down drops, jump does a ledge jump | Added 2026-09-20 as part of the stage-geometry redesign — see decision log. A regrab lockout (0.4s) prevents instant re-grabbing after any exit; refusing a grab when held input points away from the stage prevents an intentional walk-off from instantly snapping back. Verified: grab/climb/drop/jump all land on exactly the expected position/velocity values, and the walk-off-without-regrabbing case specifically confirmed fixed | Set (grab range 0.7 horiz / +1/-5 vert, regrab lockout 0.4s, ledge jump 26 up / 7 push) |
| Platforms | One-way floating floor segments: land on from above, pass through from below, drop through deliberately by holding down | Added 2026-09-20 alongside ledges — same stage-geometry redesign. **Revised same day** into a Battlefield-style layout (Melee) — one top platform, two side platforms, symmetric left/right — per Nate's reference drawing. Originally offset to dodge the old interior wall-jump chambers; those chambers are gone now (see Recovery Walls row), so the side platforms sit at clean, simple symmetric positions instead. Verified: landing from above, drop-through, and pass-through-from-below all behave correctly for all three platforms | Set (top: -3 to 3 @ y=10; sides: ±5 to ±9 @ y=6) |
| Kill Zone | Crossing bounds well outside the stage resets you to a spawn point at rest | Added 2026-09-20, made necessary (not just possible) by ledges replacing the old solid boundary walls — otherwise a missed grab falls forever. No stocks/game-over yet, just the reset. Verified: crossing any of the four bounds correctly resets position, velocity, and airborne/ledge/fast-fall state | Set (bounds ±22 X / -16 to 30 Y, spawn at (0, 3)) |
| Naruto Run (arms) | Cosmetic: both arms sweep back together at high speed instead of alternating with the legs | Engages once running at least 60% of Ground Max Speed AND committed to one direction for at least Naruto Min Distance (3 units) — otherwise dash-dancing flips the pose in and out. The raise itself is a time-based blend (0.5s), not tied to the fast per-frame arm ease rate, so it reads as deliberate rather than a snap; verified reaching full blend at exactly 0.5s. Drops back out over the same 0.5s the instant either gate condition stops holding | Set (angle -1.9 rad, min distance 3 units, transition 0.5s) |
| Sound Effects | Synthesized SFX (Web Audio API oscillator blips, no audio files) for footsteps, jump, landing, turn-dust, and fast-fall trigger | Added 2026-09-19. AudioContext created lazily on first keydown (browsers block audio before a user gesture). Landing volume scales with impact speed. Verified all five sound functions fire without error | Set |
| Camera Reaction | Shake on hard landings (decays over real time) plus a subtle FOV push that scales with ground speed | Added 2026-09-19, alongside sound, as the first "juice" pass beyond animation. Shake amount = min(0.25, impactSpeed × 0.006). FOV eases toward (50 + 4×speedFrac). Verified: FOV reaches exactly 54° at full speed; a landing with impact ~31.4 kicked shake to ~0.189 (matches formula), decaying fully to 0 | Set (max FOV boost +4°, shake cap 0.25) |
| Turn Dust | Cosmetic particle puff when reversing direction while grounded, only above a speed threshold | Added 2026-09-19 in response to Nate's "should there be a threshold?" question — recommended and implemented gating it to only fire above 50% of Ground Max Speed, so small direction wiggles stay silent and only committed reversals puff. Detected via an edge-trigger on "just started trying to move opposite current velocity," checked against speed BEFORE that tick's physics (not the instantaneous near-zero speed at the actual sign-crossing tick, which would always read near-zero). A minimal 6-particle burst, shrinks and is removed over ~0.3-0.45s. Verified in-game: 0 particles spawned below threshold (speed 2), exactly 6 spawned above it (speed 12) | Set (threshold: 50% of Ground Max Speed) |
| Jump Count | How many times you can jump before touching ground again | Single fixed-height grounded jump + one double jump usable mid-air (open to revisiting later, not locked in forever) | Qualitative |
| Ground Deceleration (Stopping) | How the character slows when direction input is released while running | Quick grip stop — fast deceleration, minimal slide, reads as precise/controlled | Qualitative |
| Air Turnaround Behavior | Whether/how much you can reverse horizontal direction mid-air | **Superseded 2026-09-19** by the Momentum Carry-Into-Jump clamp above: since horizontal speed is now always clamped to Max Air Speed the instant you leave the ground, every jump enters the air at the same speed regardless of how fast you were running — there's no more "fast run jump can only curve, standstill jump gets full control" distinction, since they now start identically | Superseded — see Momentum Carry-Into-Jump |
| Double-Jump Reversal | Special case: holding the opposite direction from your current horizontal motion at the moment you double-jump | Added 2026-09-19, **removed the same day** after research showed only Kirby/Jigglypuff can turn around via jump in real Melee — not a normal-character ability. No longer exists in the code | Removed |
| Air Facing Lock | Whether the character's visual facing can change while airborne | Facing is locked the moment you leave the ground and never changes for any reason — no exceptions, confirmed via testing (even a full velocity reversal from ordinary air control doesn't change facing). Matches real Melee's normal-character behavior | Set |

---

## Decision log

- **2026-09-19** — Settled on a Melee/Mirror's-Edge-inspired momentum movement sandbox, single-player
  first, camera as a shallow-2.5D side view (not first/third-person). v1 move set: run, jump, air
  control, dash-dance. Wavedash-equivalent and fast-fall deferred.
- **2026-09-19** — Input designed digital-first so keyboard and controller are both first-class.
- **2026-09-19** — Air control set to low/committal: a bad jump should be punishing, not correctable.
- **2026-09-19** — Added Max Fall Speed (terminal velocity): confirmed a fall-speed cap is wanted,
  both for feel (falls stay readable) and for simulation correctness (avoids tunneling through thin
  platforms at a fixed timestep).
- **2026-09-19** — Dash-dance should allow turning on a dime at any time while grounded, regardless
  of how long you've been running — an explicit, deliberate departure from Melee's run-lock/pivot
  mechanic. Physics response should be instant; the visual turn-around gets a short smooth blend so
  it doesn't look glitchy. Explicitly open to introducing a run-state-based turn cost later if the
  no-lock version feels wrong in practice.
- **2026-09-19** — Jump: single fixed-height grounded jump plus one double jump usable mid-air, for
  v1 (not considered a permanent lock-in). Ground stopping: quick grip stop when input is released.
  Air turnaround: should depend on entry speed (full control from a standstill, only curving at full
  run speed) — expected to emerge from the existing Air Acceleration + limited air-time model rather
  than a bespoke rule; confirm once playable. Camera: static fixed frame for v1, no follow-cam, sized
  to show a Battlefield-sized stage with a Marth-sized character.
- **2026-09-19** — Reverted the shallow-2.5D depth axis after playtesting the prototype: it felt like
  too much. Movement plane is now strict 2D (X + Y only); the Z axis and all associated input/physics
  code were removed from movement-sandbox.html rather than left in unused.
- **2026-09-19** — Added procedural leg animation to the placeholder character (hip-pivoted legs
  swinging in alternating phase), purely to make gait direction/speed readable during playtesting —
  not a step toward the real rigged/skinned character model, which stays deferred. Swing amplitude
  and cycle speed both scale with ground speed and ease to a neutral stance at rest; a fixed tucked
  pose plays while airborne. It's computed inside the same deterministic fixed-timestep update as
  physics (so it stays reproducible under rollback too), but it's purely cosmetic — it never feeds
  back into position, velocity, or collision.
- **2026-09-19** — Three feel fixes after more playtesting: (1) Ground Acceleration raised 90 → 240
  to fix dash-dancing feeling slow/sticky when reversing direction. (2) Added Double-Jump Reversal:
  holding the opposite direction at the moment of a double jump instantly mirrors horizontal speed
  the other way, as a deliberate exception to normal committal air control. (3) Added Air Facing
  Lock: facing can no longer change from ordinary air-control drift, only from a Double-Jump
  Reversal — verified via testing that this holds even when air control alone fully reverses
  velocity (a low-speed jump drifting from +3 to -7 correctly left facing unchanged).
- **2026-09-19** — Three more fixes from playtesting feedback: (1) Fixed a real bug where holding
  Space triggered an unintended double jump, caused by the browser's OS key-repeat re-firing
  `keydown` — now ignored via `event.repeat`, so only a genuine second press double-jumps.
  (2) Removed Momentum Carry-Into-Jump: after noticing jump distance/speed seemed to favor the
  facing direction, testing confirmed the physics don't care about facing at all — the real cause
  was leftover ground velocity carrying into the jump (the old Air Turnaround Behavior design).
  Explicitly decided to remove that carry-over entirely rather than keep it: horizontal velocity
  now always resets to zero on a (single) jump, making every jump symmetric regardless of prior
  movement. (3) Air Acceleration and Max Air Speed both raised ~50% (16→24, 7→10.5) since air
  control felt too strict.
- **2026-09-19** — Reverted the Momentum Carry-Into-Jump removal from earlier the same day: killing
  a full-speed run's momentum on jump felt bad. Restored the dynamic speed-cap system (jump keeps
  your horizontal velocity if you're still holding the direction; air control's cap expands to match
  it), while keeping the requirement that a standstill jump is symmetric regardless of facing — since
  entry speed is zero either way at a standstill, the cap is always the same baseline value in both
  directions. Verified both: momentum carried fully (14 → 14) when holding direction through a jump,
  and standstill jump distance was near-identical left vs. right. Air Turnaround Behavior is back in
  effect as originally designed.
- **2026-09-19** — Doubled jump height and set double-jump height to 50% of the first jump's height.
  Since height scales with speed squared (h = v²/2g), this meant multiplying jumpSpeed by sqrt(2)
  (14 → 19.8), not 2 — doubling the raw speed number would have quadrupled the height. doubleJumpSpeed
  was set to jumpSpeed/sqrt(2) = 14.0 to get exactly half the new jump's height. Verified in-game:
  single jump peak height roughly doubled, double-jump's own added height came out to ~51% of the
  first jump's (small deviation from fixed-timestep discretization, not a design error). Hang time on
  the first jump is also ~41% longer as an unavoidable side effect of the higher jump speed.
- **2026-09-19** — Standardized on talking about jumps in terms of Jump Speed / Double Jump Speed
  (raw velocity stats, which is what the code has always used internally) rather than target height,
  since height requires a sqrt() conversion to translate into a stat while velocity doesn't — and
  Nate wants to avoid accumulating per-stat custom formulas, especially with multiple characters
  planned later. No code changes were needed for this shift; every stat in STATS was already a plain
  velocity/acceleration value with height simulated as an emergent result, never stored directly.
  Set Jump Speed to 20 and Double Jump Speed to 10 (renamed from Jump Height/Double Jump Height in
  this doc to match the new convention).
- **2026-09-19** — Double Jump Speed set equal to Jump Speed (both 20): the 10 value made the double
  jump feel much weaker than intended, because a 50%-of-velocity ratio is only 25%-of-height (height
  scales with velocity squared) — a further illustration of why the earlier "10" wasn't the "half as
  strong" it looked like as a raw number. Double jump now runs through the identical formula as the
  first jump with no weakening at all.
- **2026-09-19** — Researched real Melee's physics for context on the double-jump reversal Nate was
  unsure about. Key findings: (1) Melee's ground pivot (reversing direction mid-dash) explicitly
  zeroes momentum rather than preserving/mirroring it — turning around costs you your speed, it
  doesn't let you keep it going the other way. (2) Only Kirby and Jigglypuff can change facing via
  jump in real Melee — it is not a normal-character ability. Given (2), removed the Double-Jump
  Reversal mechanic entirely rather than reworking its momentum handling: facing now never changes
  while airborne, full stop, matching normal-character Melee behavior. Verified via testing that
  double-jumping with the opposite direction held no longer changes facing (velocity can still drift
  via ordinary air control, unrelated to this).
- **2026-09-19** — Researched Melee Fox's stats (ssbwiki, cross-checked against the same source that
  validated Marth's numbers earlier) as a reference for a "twitchy/fast" feel: Run Speed 2.2, Air
  Speed 0.83 (only 37.7% of run speed — tighter than Marth's 50%), Gravity 0.23 (much heavier than
  Marth's 0.085), Jumpsquat 3 frames, Jump Height 31.28, Double Jump Height 40.204 (bigger than his
  own first jump — unusual; most characters' second jump is smaller). Exact numbers don't port across
  unit systems, so applied the *ratios* to our existing stats: Max Air Speed lowered 10.5 → 5.3,
  Gravity raised 45 → 72 with Jump Speed recalculated to 25.3 to preserve jump height while cutting
  hang time, Max Fall Speed raised 22 → 28, and Double Jump Speed set to 28.7 (~128% of the first
  jump's height, matching Fox's oversized double jump). Did not add Melee's jumpsquat (a startup
  delay before a jump launches) — that's a new mechanic we haven't built, not just a stat tweak, and
  wasn't part of what was agreed to change here. All changes verified in-game: jump height held at
  ~4.66 (target ~4.44) with hang time down from ~890ms to ~650ms; double jump gained ~5.96 vs. the
  first jump's ~4.66 (ratio ~1.28, matches target); air speed clamped at exactly 5.3 while airborne.
- **2026-09-19** — Changed how Momentum Carry-Into-Jump works: instead of dynamically expanding the
  air-speed cap to match entry speed (never clipping momentum), horizontal velocity now clamps hard
  to Max Air Speed the instant you leave the ground. Below the cap, nothing changes; above it, you
  take a real, felt speed loss on takeoff — this matches real Melee's behavior for characters with a
  big gap between ground and air speed, which describes our current Fox-tuned numbers (14 ground vs.
  5.3 air). Verified via direct testing of doJump(): entry speed 3 (under cap) passed through
  unchanged, entry speed 14 (over cap) clamped to exactly 5.3. Side effect: Air Turnaround Behavior's
  old "fast run can only curve, standstill gets full control" distinction is now moot, since every
  jump enters the air at the same (capped) speed regardless of prior ground speed — noted as
  superseded in that row rather than removing the row's history.
- **2026-09-19** — Raised Max Air Speed 5.3 → 8 (felt too tight). Researched Melee's actual air
  control model since it still felt unwieldy — found we were missing Air Friction entirely, a
  separate deceleration that only applies with no direction held (air acceleration, which we did
  have, only applies while a direction IS held). Without it, releasing input in the air did nothing,
  so any horizontal speed became permanent until landing. Added Air Friction at 6 (25% of Air
  Acceleration's 24, matching Fox's real friction-to-accel ratio). Verified in-game: velocity now
  decays toward zero when no direction is held while airborne, at exactly the expected rate.
- **2026-09-19** — Raised Air Acceleration 24 → 36 (~50%) for more left/right control in the air.
  Air Friction left unchanged at 6, so friction is now a smaller fraction of acceleration (~17%
  instead of the original 25% Fox-matched ratio) — releasing input still stops drift, just
  relatively less crisply than active steering now. Not changed since the ask was specifically
  about steering control, not stopping.
- **2026-09-19** — Added five "fun/weighty" features in one pass, all verified in-game:
  1. **Fast-fall** (fastFallSpeed 43, ~1.3x Max Fall Speed): pressing down while already falling
     instantly snaps to the faster terminal velocity, matching Melee's real mechanic. Resets on
     landing or any new jump.
  2. **Landing squash**: a simple scale-transform squash on touchdown, kept deliberately barebones
     (no new pose/asset) per Nate's direction to keep animation simple. Shares one signed
     `bodyStretch` value with takeoff stretch below.
  3. **Turn dust**: a small particle puff on grounded direction reversals, gated to only fire above
     50% of Ground Max Speed (Nate asked whether a threshold made sense; recommended and implemented
     one so small wiggles don't spam dust). Detection is edge-triggered on the tick you START trying
     to reverse, checked against your speed BEFORE that tick's deceleration — checking speed at the
     exact zero-crossing tick instead would always read near-zero and never trigger, since velocity
     is always small right when it crosses zero regardless of how fast you were going beforehand.
  4. **Takeoff stretch + double-jump leg tuck**: a stretch on jump takeoff (same `bodyStretch`
     mechanism as landing squash, opposite sign), and a brief tighter leg tuck specifically on double
     jump (0.18s timer) that relaxes back to the normal airborne pose, reusing the existing leg-easing
     system rather than a new animation asset.
  5. **Heavier gravity for a shorter, faster-feeling jump**: raised Gravity again (72 → 85) with Jump
     Speed/Double Jump Speed recalculated to preserve the same heights (~4.44 / ~128% ratio) —
     hang time dropped to ~570ms from ~650ms, same methodology as the earlier Fox-inspired gravity
     change. All five are purely additive; no existing mechanic was changed to make room for them.
- **2026-09-19** — Fixed an anatomical error in the placeholder character model: the two legs were
  offset along X, which is the character's own forward/back (facing) axis, so turning to face
  left/right staggered them front-and-back like a wheelbase instead of side-by-side like real hips.
  Moved the leg pivots to offset along Z instead (the axis perpendicular to facing). The swing
  animation itself needed no change, since rotating a pivot around Z swings it through the local X-Y
  plane regardless of the pivot's own position along Z. Visual side effect, expected and fine: since
  the camera looks straight down that same Z axis, the two legs now mostly overlap when standing
  still (reading as one leg) but separate correctly into a visible stride once mid-swing — this
  matches how real 2D side-view games typically render legs.
- **2026-09-19** — Four more quality-of-life additions:
  1. **Camera raised**: position (0,7,17)→(0,9,17), look-at target (0,2.5,0)→(0,3.8,0). Flattens the
     downward tilt so more sky shows and less foreground, giving headroom to see jumps.
  2. **Arms**: same hinge-pivot pattern as legs, offset along Z (same anatomical fix as the legs
     above), swinging contralateral to the legs (armL shares legR's gait phase and vice versa) —
     verified in-game. Torso/head/nose/arms were regrouped under a new `upperBody` pivot (legs stay
     direct children of the top-level group) so the lean below can tilt them independently.
  3. **Crouch**: holding down while grounded sustains the existing `bodyStretch` value at a squash
     target (-0.35) instead of it decaying back to 0 — reuses the landing/takeoff squash mechanism
     rather than adding a new one, releasing cleanly back to 0 on letting go. Shares the Down key
     with Fast-Fall; no conflict since one requires grounded and the other requires airborne.
  4. **Running lean**: a new `upperBodyLean` value tilts the upper-body pivot toward local-forward,
     scaled by ground speed (0 at rest, up to 0.22 rad at full speed), for a more athletic look.
     Defined relative to the character's own facing rather than world direction, so it automatically
     leans the correct way after inheriting the parent group's yaw — no direction-based sign-flipping
     needed. Verified in-game: reaches exactly -0.22 at full speed in either direction.
- **2026-09-19** — Added a "Naruto run": above 60% of Ground Max Speed, arms blend from the normal
  alternating swing into both sweeping back together at a fixed angle (-1.9 rad — past 90°, so they
  end up raised behind rather than just trailing at hip level), fully in by 95% speed. Legs keep
  their normal gait throughout; only the arms change. Verified in-game: at 21% speed arms alternate
  normally (-0.27 / +0.27), at full speed both lock to exactly -1.9 together.
- **2026-09-19** — Two quality fixes: (1) The Naruto pose looked wrong during dash-dancing, flipping
  in and out as speed repeatedly crossed the 60% threshold on each direction tap. Added a same-direction
  distance tracker that resets the instant travel direction changes (or you stop moving), and gated
  the pose behind it (3 units minimum) on top of the existing speed blend — you now have to actually
  commit to running one way, not just briefly touch high speed, before it engages. Verified: simulated
  rapid reversals (~8 ticks/0.13s apart) never accumulated past 1.03 units and never triggered the
  pose; sustained one-direction running reached 7.80 units and triggered it correctly. (2) Crouch now
  eases in at a separate, much faster rate (crouchEaseRate: 4.5) than the landing/takeoff squash
  (which stays at the original, slower stretchEaseRate) — verified reaching the full crouch target in
  exactly 5 frames at 60fps, as requested.
- **2026-09-19** — The Naruto pose still "snapped" in instantly the moment the distance gate opened,
  because it reused the arms' fast per-frame ease rate (tuned for responsive normal swinging, not a
  deliberate pose change). Replaced the instant gate with a dedicated `narutoBlendFactor` (0-1) that
  ramps over a fixed narutoTransitionDuration (0.5s) whenever both gate conditions hold, and ramps
  back down the instant either stops holding; the arm target now interpolates by this smoothly-eased
  factor instead of jumping straight to the gate's boolean value. Removed the now-unused speed-ratio
  blend (narutoBlendEnd) since this replaces it. Verified in-game: blend factor rises linearly in
  exact 0.1-per-6-ticks steps, reaching 1.0 at exactly tick 30 (0.5s), with the arm angle tracking
  smoothly alongside it the whole way rather than jumping.
- **2026-09-19** — Fixed running-while-crouched: holding down while grounded now suppresses
  horizontal acceleration entirely (movement direction is treated as none while crouching), so
  existing speed bleeds off via normal deceleration instead of sprinting in a squashed pose. You can
  still turn to face a direction while crouched (facing isn't affected, only movement), but can't
  build or hold speed until releasing down. Verified in-game: holding a direction and down together
  from full speed (14) skidded to a full stop in 8 ticks while the crouch squash engaged fully.
- **2026-09-19** — Legs upgraded to two segments with a knee joint, as a first prototype toward
  eventual hitboxes/hurtboxes needing real body-segment structure rather than one rigid capsule per
  limb (see the "how big a lift" scoping discussion above — arms are intentionally NOT touched yet,
  legs first to validate the approach). Each leg is now a hip pivot (thigh) with a knee pivot nested
  inside it (shin), same hinge-pivot pattern as before just one level deeper; a small sphere at each
  pivot's origin masks the joint gap that opens up when a rigid segment rotates away from its socket.
  Knee bend is a first-pass procedural approximation (not a real IK solve): a half-wave-rectified
  cosine that peaks when that leg's hip swings through neutral moving forward (foot-clearance moment)
  and clamps to zero for the stance/push-off half of the cycle, so only the currently-swinging leg's
  knee bends at a time. Verified in-game: knee angles alternate correctly between legs across the
  gait cycle, matching the intended timing. Explicitly flagged as needing visual tuning once seen in
  motion — this is an approximation, not a solved animation.
- **2026-09-19** — More athletic torso/head, plus a neck. The torso switched from a uniform capsule
  to a tapered cylinder (broader "shoulders" at top, narrower "waist" at bottom) — a capsule can't
  taper since it has one radius along its whole length, so this was a primitive change, not just a
  resize. Added a short neck cylinder between the torso top and the head. Since neither joint rotates
  independently (no head-turning or torso-twisting animation exists), they don't need the socket
  spheres the knee/hip joints use — a small fixed overlap (0.03) at each seam is enough to guarantee
  no visible gap regardless of exact dimensions. Shoulder height and arm attachment offset were
  updated to match the new, broader shoulder radius. Verified: torso/neck and neck/head overlap by
  exactly 0.03 each, confirming no gaps in the stack.
- **2026-09-19** — Slimmed the torso (torsoRadiusTop 0.40→0.33, torsoRadiusBottom 0.26→0.21) and
  shrank the head (0.28→0.23). Also adjusted the two dependent values that were sized relative to the
  old dimensions so they'd stay correctly attached rather than floating off the now-smaller body: the
  nose cone's size and offset now reference `headRadius` directly instead of a hardcoded value, and
  the arm attachment offset (0.45→0.38) was reduced to match the narrower shoulder radius.
- **2026-09-19** — Fixed a real bug behind the "torso disconnects from the legs" look during the
  running lean: `upperBody` was rotated around its own origin, which sat at ground level (y=0) since
  it was never given a position — so leaning swung the whole torso through an arc around a point down
  near the feet instead of pivoting from the waist where it actually meets the hips. Fixed by moving
  `upperBody`'s origin to hip height and re-deriving all of its children's Y positions (torso, neck,
  head, nose, shoulder height) relative to that new origin instead of ground level. Verified via
  matrix math: the torso's bottom-center point now stays fixed at exactly hip height (0.85) whether
  leaning or not, confirming it pivots from the waist. Also shrank the neck (radius 0.14 → 0.10).
- **2026-09-19** — Added a "Marth jump" default airborne pose, replacing the old generic symmetric
  tuck. Couldn't find a reliable sourced description of Marth's actual Melee jump animation (search
  kept surfacing his taunts/victory poses instead), so asked Nate what specifically he wanted rather
  than guess: legs together trailing behind, sword arm extended. Implemented as: both legs swept back
  together to -0.45 rad (same angle on both hips, so they read as one trailing silhouette) with a
  modest 0.25 rad knee bend rather than a tight tuck, plus an asymmetric arm pose — armR ("sword arm")
  extended to 0.9 rad, armL relaxed/trailing at -0.25 rad. This is the default pose for the whole
  flight (not just a brief moment); the existing double-jump tuck still plays its own brief tighter
  symmetric tuck right at the moment of double-jumping before settling into this pose. Old
  jumpPoseAngle/armJumpPoseAngle constants removed (fully replaced, not left dangling). Verified
  in-game: all four leg/knee/arm values matched their targets exactly after landing-timer expired.
- **2026-09-19** — Made the legs asymmetric in the jump pose too, per Nate's request for one leg
  driven up with a bent knee (basketball-dunk-style), not both legs doing the same trailing sweep.
  legL now drives up and forward (hip 1.0 rad, knee folded to 1.0 rad); legR keeps the original
  trailing pose (hip -0.45, knee 0.25) — paired opposite the sword arm (R), so the "forward-focused"
  side (extended sword arm) is opposite the raised leg. Verified in-game: legL and legR angles reach
  their distinct targets exactly after 15 ticks airborne.
- **2026-09-19** — Two fixes for the jump pose feeling static: (1) Added `player.jumpPoseFlipped`,
  set false on a grounded jump and true on a double jump, so which leg drives up and which arm is the
  "sword arm" swaps between the two — no longer the same pose every time. The existing brief tighter
  double-jump tuck still plays first (0.18s) before settling into the swapped pose. (2) Added a small
  continuous sine wiggle (`jumpPoseWiggleAmplitude` 0.08 rad, ~2.5 Hz) applied to the raised leg and
  sword arm via `player.airTime` (resets each jump), so a long hang time doesn't read as a frozen
  snapshot. Verified in-game: first jump defaults to legL raised/armR sword; after the tuck window,
  double jump correctly swaps to legR raised/armL sword; the raised leg's angle visibly oscillates
  between ~0.92 and ~1.08 (matching the wiggle amplitude around the 1.0 target) while airborne.
- **2026-09-19** — Added hip/shoulder counter-rotation to the jump pose, since it still looked static
  even with the leg-swap and wiggle: whichever leg is raised should bring that hip forward (and the
  other back), with the shoulders twisting the opposite way — the athletic torque real bodies get any
  time one leg drives forward. Required restructuring the model: legs now live under a new `pelvis`
  pivot (positioned at hip height, same pattern as `upperBody`) instead of being direct children of
  the top-level group, so the hips can twist (yaw) independently of, and opposite to, the upper body.
  `player.bodyTwist` eases toward ±bodyTwistMax (0.25 rad) based on which side is raised
  (player.jumpPoseFlipped), 0 while grounded; pelvis.rotation.y = bodyTwist, upperBody.rotation.y =
  -bodyTwist (opposite sign). Verified via world-position math: with legL raised, legL's hip pivot
  moves to world X = +0.0396 (forward) while legR's moves to -0.0396 (backward), and the upper body's
  twist is exactly opposite in sign to the pelvis's.
- **2026-09-19** — Added synthesized sound effects and camera reaction, the first "juice" pass beyond
  animation, in response to the game still feeling rigid. Both are additive — no existing mechanic
  changed. **Sound** (Web Audio API, oscillator-based blips, no external audio files — AudioContext
  created lazily on first keydown since browsers block audio before a user gesture): footstep (fires
  once per gait half-cycle via the same edge-detection pattern used elsewhere), jump (both single and
  double), landing (volume scales with impact speed), turn-dust whoosh, and fast-fall trigger. **Camera
  reaction**: a shake that kicks up on hard landings (proportional to impact speed, capped) and decays
  over real time, plus a subtle FOV push (+4° max) that eases toward a target based on current ground
  speed, for a sense of velocity during fast movement. Verified in-game: all five sound functions fire
  without error; FOV correctly reaches exactly 54° (50 base + 4 max) at full speed; a hard landing
  (impact ~31.4) kicks shake to ~0.189 matching the formula exactly, decaying fully to 0 afterward.
- **2026-09-19** — Architecture cleanup: split the single ~800-line `movement-sandbox.html` into a
  proper multi-file structure under `movement-sandbox/`, needed before combat/multiplayer make one
  giant file unmanageable. Originally planned as a Vite + npm project, but Node.js couldn't be
  installed (no local admin rights — this is a work laptop; the winget install's UAC prompt was
  declined by policy). Pivoted to **native browser ES modules** instead: plain `.js` files using
  `import`/`export`, no bundler, no build step, served via a plain Python `http.server` (already used
  for saw-dodge) since native ES modules are blocked by CORS when loaded via `file://`. An import map
  in `index.html` maps the bare `three` specifier to the CDN's ES-module build
  (`three.module.js`, not the old classic `three.min.js`), so every module can still write the clean
  `import * as THREE from 'three'` — if Node ever becomes available later (e.g. a personal machine)
  and we move to Vite, no source file needs to change, just drop the import map.
  Module split: `stats.js` (STATS/ANIM/STAGE/FIXED_DT constants), `state.js` (the `player` object +
  `moveToward`), `input.js` (keyboard/gamepad, exposes `consumeJumpQueued()` rather than a raw
  mutable export, since ES module bindings are read-only to importers), `audio.js`, `scene.js`
  (renderer/camera/stage/lighting), `character.js` (`buildCharacter()`), `particles.js` (turn dust),
  `physics.js` (`fixedUpdate`/`doJump` — the core sim), and `main.js` (entry point: builds the
  character, runs the render loop, applies simulation state to the Three.js objects and HUD).
  Physics/animation logic is verbatim from the tested single-file version, not rewritten — this was a
  reorganization, not a rebuild. New launch config added (`.claude/launch.json`, port 8732). Verified
  in-game via the new server: running reaches full speed (14), jump and double jump both fire with
  correct relative velocities (24.7 vs 28.4) and correctly consume/restore the double-jump-ready
  flag, and a hard dash-dance reversal triggers turn dust/sound with no console errors — matching the
  original file's behavior with nothing regressed.
- **2026-09-19** — Added wall jump, the first "more movement tech" addition post-architecture-cleanup
  (picked over air-dodge/wavedash, wall run, and air dash as the cheapest high-payoff option, since
  the stage's side boundaries already existed and previously just stopped you dead). Pressing jump
  while airborne and touching a side wall kicks you away from it instead of consuming your double
  jump — takes priority over the double jump when touching a wall. Touching a wall also refreshes the
  double jump (a standard, well-liked convention in wall-jump games), and it's a deliberate exception
  to "facing locked in air," since kicking off a wall is clearly a turn. No cooldown/lockout on
  repeated same-wall wall-jumps — this is a sandbox for exploring movement tech, so chaining them for
  extra height is a feature, not a bug, unless it turns out to feel bad. Reuses `doJump()` for the
  shared resets (fast-fall, takeoff stretch, airTime) with the horizontal kick and facing set
  afterward. If you hold into the wall at the moment of the kick, ordinary air control fights it back
  down toward the normal Max Air Speed within about a tick — an accepted trade-off for keeping one
  uniform air-speed cap rather than adding a kick-protection lockout window. Verified in-game:
  kick lands at exactly Wall Jump Push Speed (10) and Wall Jump Up Speed (24) the instant of the jump;
  with no input held afterward it decays via ordinary air friction (8.2 after 300ms, matching the
  friction formula, not stuck at a plateau); double-jump-ready correctly refreshes to true; and
  ordinary double-jumping away from any wall is unaffected (unchanged velocities/flag behavior).
- **2026-09-19** — Added two interior walls to actually practice wall-jumping on, at x = ±6, leaving
  a 12-unit-wide open lane in the middle for normal running/dash-dancing untouched. Each interior wall
  pairs with the nearby stage edge to form a jumpable "chamber" on either end, rather than being a
  freestanding pillar in the middle of the main path. Required two changes: (1) real two-sided AABB
  collision for interior walls (the existing stage-edge collision only ever needed to stop you from
  one direction, so it couldn't reuse that code as-is) — resolved using `prevPos` to tell which side
  you approached from, so the wall's two faces don't fight each other. (2) Generalized wall-jump
  detection (`getWallJumpPushDir()`) to check interior walls in addition to the stage edges, replacing
  the old inline edge-only check. Also gave both wall types real geometry for the first time — the
  stage edges were previously an invisible numeric limit, which would've been confusing to wall-jump
  against now that it matters. Verified in-game: running into the interior wall stops exactly at its
  face (speed → 0), and wall-jumping off it lands at exactly the same Wall Jump Push Speed (10) /
  Wall Jump Up Speed (24) as the stage edges, confirming the generalized detection works identically
  for both wall types.
- **2026-09-19** — Added wall-slide, in response to "should we make a wallgrab pose?" Presented the
  choice between a purely cosmetic pose and a full slide with slowed-fall physics; Nate picked the
  full slide. Touching any wall (stage edge or interior) while falling clamps the fall-speed cap down
  to Wall Slide Speed (5, well under both Max Fall Speed and Fast-Fall Speed) — gravity itself is
  unchanged, so the existing fall-speed clamp just snaps down to whichever cap is active, no separate
  deceleration logic needed. Wall contact alone refreshes the double jump (not just kicking off, so
  you can grab, drop, and still double-jump), and fast-fall can't even trigger while sliding — gripping
  the wall overrides it outright rather than stacking. It's also a second deliberate exception to
  "facing locked in air" (alongside wall jump): while sliding, facing turns toward the wall you're
  gripping. Pose is symmetric (both legs bent, both arms reaching toward the wall) rather than the
  jump pose's asymmetric raised-leg/sword-arm look, since bracing against a wall isn't a one-sided
  motion; shares the jump pose's continuous wiggle so a long grab doesn't read as frozen. One bug
  caught during testing: wall contact is detected once at the top of each physics tick and reused all
  the way through (fall-cap override, facing, jump handling, pose) for consistency within that tick —
  but on the exact tick a wall jump fires, that same reused flag is now stale (computed from the
  position *before* the kick) and was overriding the away-from-the-wall facing `doWallJump()` had just
  set, dragging it back toward the wall for a frame. Fixed with a same-tick guard so the wall-slide
  facing override is skipped whenever a wall jump just fired this tick. Verified in-game: fall speed
  clamps to exactly -5 while sliding regardless of how fast you were falling; holding down while
  sliding does not raise the cap or set fastFalling; double-jump-ready refreshes on contact alone;
  legs/knees/arms ease to the wall-slide pose targets; facing turns toward the gripped wall; and,
  after the fix, wall-jumping off a slide correctly snaps facing away from the wall and stays there
  rather than sliding back.
- **2026-09-19** — Fixed invisible walls extending above the visible wall geometry. Both wall
  collision (stage edges and interior walls) and wall-jump detection (`getWallJumpPushDir()`) were
  purely X-axis checks with no height limit, so they blocked/registered contact at any altitude even
  though the wall mesh (scene.js) is only 8 units tall — you'd hit a solid, invisible ceiling-less
  "wall" high above where the visible geometry actually ends. Added a shared `WALL_HEIGHT` constant
  (stats.js, also now used for the mesh height in scene.js instead of a separate local constant) and
  gated all three checks on `player.pos.y < WALL_HEIGHT`. Climbing above that height (e.g. via double
  jump) now lets you fly cleanly over any wall, including the stage edges — falling back below the
  wall's height mid-flight re-engages collision, so you can't permanently escape by floating above and
  drifting sideways forever; you have to actually clear the wall's X range before coming back down.
  Verified via direct physics-loop tests: below WALL_HEIGHT, both wall types still block exactly as
  before; above it, horizontal movement passes cleanly through both (isolated with `grounded: true` to
  hold altitude constant, since gravity would otherwise pull the test back below the threshold
  mid-loop); and wall-jump input above WALL_HEIGHT correctly does nothing (no velocity kick, no
  double-jump refresh) rather than firing.
- **2026-09-20** — Replaced the dash-dance turn sound's high-pitched sawtooth blip with a "whoosh":
  Nate didn't like the pitch. A pure oscillator can't read as moving air no matter how it's swept, so
  this needed actual noise instead of a tone — added `playWhoosh()` (audio.js), a second synth path
  alongside the existing `playBlip()` helper, built from a filtered noise burst rather than an
  oscillator: a cached white-noise buffer (content is reused across calls, only the filter sweep
  changes) run through a bandpass filter sweeping high-to-low (1800Hz → 350Hz over 0.12s), which reads
  as air rushing past rather than a musical note. `playTurnSound()` now calls this instead of
  `playBlip()`; all four other SFX (footstep, jump, land, fast-fall) are untouched. Verified the new
  node graph (buffer source → bandpass filter → gain → destination) builds and plays with no errors.
- **2026-09-20** — Nate still heard the turn whoosh as too high-pitched. Switched the filter from
  bandpass to lowpass (bandpass only *favors* a band around its center frequency — everything above it
  still leaks through at reduced volume, which read as a high pitch riding underneath; lowpass
  actually caps anything above the cutoff). Sweep range lowered to fit entirely at or under Nate's
  requested 1200Hz ceiling (1200Hz → 300Hz, was 1800Hz → 350Hz), giving the requested "muffled" feel.
  Q lowered to 0.7 (flat rolloff) so the cutoff itself doesn't ring/resonate. Verified the updated node
  graph builds and plays with no errors.
- **2026-09-20** — Lowered the turn whoosh an octave, per Nate's request. Halved the lowpass sweep
  (1200Hz → 300Hz became 600Hz → 150Hz), since halving frequency is exactly what an octave down means.
  Verified it still builds and plays with no errors.
