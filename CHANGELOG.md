# Changelog

All notable changes to YATA are documented in this file.

The version scheme is `X.Y.Z`:
- `X` — major changes
- `Y` — minor changes
- `Z` — bugfixes, trivial changes, or changes unrelated to code (e.g. documentation)

## [0.25.3] - 2026-08-01

### Added
- **YATAS list window names now show in that window's own custom border
  color** (color only, no glow) — each row reads its own window's color via
  `windowManager.getBorderColor()`, since a YATAS row can represent a
  different window than the one the list itself lives in. Not tint-gated,
  matching the border's own behavior (only buttons/links are tint-gated).
  `WindowManager.setBorderColor()` now also emits `windowsChanged` (was
  previously the one mutator in that class that didn't), so a freshly-picked
  color shows up in the list immediately.

## [0.25.2] - 2026-08-01

### Changed
- **Links view no longer glows**, per explicit follow-up — reverted to flat
  colored text (still following the custom border color when set, just no
  `MultiEffect` glow). It was the only glow added fresh by r-5.md rather
  than an existing one just recolored, and didn't fit here after all.
- **Buttons/links now ignore the custom border color under any CRT tint**
  (green/goldenrod/black) — only the border itself takes the raw custom
  color regardless of tint; buttons/links keep that tint's own
  accent-derived color exactly as they did before r-5.md, since a
  tint's own palette is already tuned per-element for legibility and an
  arbitrary picked color could clash with it. Only under the "none" tint
  do buttons/links follow the custom color, as before.

## [0.25.1] - 2026-08-01

### Fixed
- **0.25.0's button/link glow didn't cover every hover-glow icon in the
  app, and read fainter than the old fixed cyan even where it did apply.**
  User feedback with a screenshot: the task list's ✓/✕/↺/🗑 hover icons
  still showed the old hardcoded cyan glow, not the custom border color.
  Turned out ~15 more spots across `TaskDelegate.qml`, `YatasRow.qml`
  (show/paint-bucket/delete/recreate/purge icons), and
  `LinkToTaskButton.qml` all hardcoded `"#00FFFF"` directly rather than
  going through `Theme` — now all route through the same
  `Theme.effectiveGlowColor`. `DragGhost.qml`'s cyan border is
  deliberately left as-is: it's a single app-wide window built once,
  outside any per-window `Theme`/`appSettings` context, and mid cross-window
  drag there's no single unambiguous window's color to borrow anyway.
- **Faintness**: a custom color can be any brightness the user picks (a
  mid-tone pink has much lower perceived luminance than the old fixed
  `#00FFFF`), so the same shadow parameters read weaker. Added
  `Theme.effectiveGlowShadowColor`/`effectiveLinkShadowColor`
  (`Qt.lighter(effective*Color, 1.4)`, same lightening factor
  `filterHoverColor` already uses) — the base fill/text/border stays the
  exact picked color, only the glow itself is lightened for visibility.

## [0.25.0] - 2026-08-01

### Added
- **Pushed FilterBar/OrderBar buttons and markdown links now follow the
  window's custom border color** (r-5.md), instead of each having its own
  independently-themed accent color. `ThemeImpl.qml` gained
  `effectiveGlowColor`/`effectiveLinkColor`, both falling back to their
  existing theme defaults when no custom border color is set (and
  reverting automatically on THEME > RESET, since these are plain reactive
  bindings off `appSettings.borderColor`).
- Links in the LINKS view (`LinkRow.qml`) now have a real glow effect
  (previously flat colored text only), matching the border/tag/button glow
  treatment, on by default using the theme's own link color. Inline
  markdown links inside a task's own text (`TaskDelegate.qml`) get the
  color update only, not a glow — a glow effect applies to a whole text
  element's rendered layer, not a substring within it, so glowing just the
  link portion of mixed prose+link text isn't achievable without fragile
  per-link overlay hacks; a Links-view row is 100% link text so it doesn't
  have that problem.



### Fixed
- **README's screenshot grid had unequal column widths** — the
  `main-yatas-multiwindow.png` image (1535px wide, two windows side by
  side) is nearly double the width of every other screenshot (991px), so
  its column stretched wider than its neighbor across the whole table
  (each `<td>`'s only sizing came from `<img width="100%"/>`, which
  collapses to the image's own intrinsic width when the cell itself is
  unconstrained). Fixed by adding `width="50%"` to every `<td>` directly,
  pinning both columns equal regardless of each image's own size.

## [0.24.1] - 2026-08-01

### Changed
- **README screenshots regenerated** to reflect the border/tag glow now
  being on by default (0.24.0): `main-green`, `main-goldenrod`, `main-dark`,
  `main_settings`, `main-links` all recaptured via
  `scripts/capture_screenshots.py`.
- The `main-yatas-multiwindow.png` screenshot's two windows now each have a
  distinct, contrasting custom border color (`#FF3DB2` / `#39FF14`) to
  demonstrate the colorized-border feature (r-4.md) directly — real
  geometry re-derived live (both windows now genuinely need 760px width at
  the current `minimumWidth`, up from the stale 599px/610px baked into the
  script) rather than reusing old constants.

### Fixed
- `scripts/capture_screenshots.py`'s `main-green` scenario, which
  regenerates `docs/screenshots/main-green.png`, had been accidentally
  deleted from `SCENARIOS` in an earlier commit (1155ace) even though
  README still references that file — restored.

## [0.24.0] - 2026-08-01

### Changed
- **The border + tag-name glow (r-4.md) is now on by default for every
  window**, not just when a custom border color is picked — it uses the
  theme's own default border/text color as the glow color instead. The
  border's glow width (4px) is likewise now permanent rather than
  custom-color-only. Confirmed live: subtle on the default theme color,
  same vivid look as before when a custom color is set.
- Content margin from the border tuned down from 30px (0.23.5) to 15px —
  30 read as too much empty space around the content.

## [0.23.5] - 2026-08-01

### Changed
- **Window content felt cramped against the border**, especially after
  0.23.4 thickened the border to 4px for the colorized-border glow — the
  content area's margin from the border went from 6px to 30px (5x) on all
  sides. Confirmed live.

## [0.23.4] - 2026-08-01

### Fixed
- **The colorized border's glow was still noticeably fainter than the rest
  of the app's glow effects**, even after 0.23.3's 2px stroke fix — an
  isolated side-by-side comparison against `TaskDelegate.qml`'s own
  `deleteBtn` hover glow (the exact reference the user pointed to) showed
  2px still reading as a thin haze, while a much bigger `blurMax` made
  almost no difference. `border.width` for the custom-color case now goes
  to 4px (drag-hover's own highlight keeps its existing, unrelated 2px),
  which reads as a proper neon-tube glow matching the reference intensity.
  Confirmed live.

## [0.23.3] - 2026-08-01

### Fixed
- **The colorized border's glow was barely visible**, even after 0.23.2
  fixed its positioning — a 1px stroke doesn't give `MultiEffect`'s blur
  enough alpha "mass" to build a visible halo from, unlike the task item
  buttons' glyphs (solid filled shapes) or the tag-name text, which don't
  have this problem. `border.width` now goes to 2px (same width the
  existing drag-hover highlight already uses) whenever a custom color is
  active, giving the glow a visibly comparable presence to the rest of the
  app's glow effects. Confirmed live.

## [0.23.2] - 2026-08-01

### Fixed
- **The colorized border's glow rendered as a separate, displaced rounded
  box instead of hugging the actual border line** — 0.23.1's fix
  (`shadowScale: 0.9`, inward) did make a glow appear, but a nonzero
  `shadowScale` makes `MultiEffect` draw an entirely separate, differently-
  sized *copy* of the whole shape; for a small icon that copy is close
  enough to read as a tight halo, but for this window-filling `Rectangle`
  even a 10% scale is tens of pixels of absolute displacement — visibly a
  second, disconnected box floating inside the window, not a glow on the
  border. Fixed with `shadowScale: 1.0` (no scale change at all) — draws
  the shadow at the exact same geometry as the source, so `shadowBlur`
  alone softens it into a halo that hugs the real line and bleeds inward,
  with zero displacement.

## [0.23.1] - 2026-08-01

### Fixed
- **The colorized window border had no glow** — only the tag-name text did.
  Root cause: the border `Rectangle` is `anchors.fill: parent` of the whole
  window, flush against the real window edges on 3 sides, and the glow
  used `MultiEffect`'s usual outward `shadowScale` (>1.0) — but a real
  window surface has zero pixels to render into past its own true
  boundary, on any platform, so the outward bleed had nowhere to go and
  was invisible (confirmed empirically: even a 40px margin barely made it
  appear, an unacceptable layout change just to make room). Fixed by
  scaling the shadow copy *inward* (`shadowScale: 0.9`) instead — bleeds
  toward the window's own interior, where there's always room, with zero
  change to the border's actual on-screen position. The tag text was
  already fine (has a few pixels of natural inset from its own label
  background) and is unchanged.

## [0.23.0] - 2026-08-01

### Added
- **Colorized window border + tag name** (`claude-docs/freq/r-4.md`): each
  window can now be given its own custom color, an additional way to tell
  windows apart beyond tag name and theme. New paint-bucket button on each
  ACTIVE row in the YATAS list opens the system's native color picker (GTK
  color chooser on GNOME, confirmed live); picking a color tints that
  window's border outline and tag-name text, with the same glow treatment
  already used for the task list's hover icons — kept even under CRT
  tints, still respects the opacity slider. Works for windows that aren't
  currently open too (persists to that window's settings file directly).
  `THEME > RESET` clears a window back to following its theme's own border
  color, same as it already resets opacity/zoom. New `AppSettings.
  borderColor` (empty string = no override), `WindowManager.
  getBorderColor`/`setBorderColor(window_id, ...)`. New icon: `resources/
  assets/noun-paint-bucket-104334.svg` (Arthur Shlain, Noun Project,
  attribution added to README).

## [0.22.0] - 2026-07-31

### Changed
- **QML brought into compliance with Qt Quick Best Practices**
  (https://doc.qt.io/qt-6/qtquick-bestpractices.html), following an audit
  against the doc. Two real gaps found and fixed; everything else the doc
  covers was already followed (platform-agnostic style, bundled resources,
  SVG icons, scalable sizing, `onMoved` over `onValueChanged`, business
  logic kept out of QML).
  - **Every user-facing string wrapped in `qsTr()`** across all of
    `yata-src/qml/` — button labels, dialog titles/bodies, tooltips,
    placeholders, status/empty-state text, and the Month/Year calendar's
    month-name/weekday-abbreviation arrays. Concatenated strings (e.g. "Are
    you sure you want to delete “X”?") use `qsTr("...%1...").arg(...)`
    rather than wrapping fragments, so a translator gets the whole sentence
    in context. Icon-button glyphs (🗑, ↺, ✓, ✕, ⋮⋮) are deliberately left
    unwrapped — they're iconography, not language text. No `.ts`/`.qm`
    files or language switcher were added; this only makes the strings
    translatable, per the doc's own framing.
  - **`TaskListModel._recompute()` no longer destroys every delegate on
    every mutation.** It previously called `beginResetModel()`/
    `endResetModel()` unconditionally on all 13 of its call sites,
    including plain `setText()`/`setStatus()` — exactly the "state lives
    in the delegate, gets lost" problem the doc warns about (and the
    reason `TaskDelegate.qml` needed its `suppressAutoSave`/
    `committedViaEnter` workaround for a reset firing mid-edit-commit).
    Now compares the visible task ID order before/after recomputing: if
    unchanged (the common case for an edit with no active search/sort),
    emits a plain `dataChanged()` instead, letting existing delegates
    update in place. Falls back to the full reset exactly as before for
    anything genuinely structural (search, sort, grouping, reordering,
    visibility filters). The existing workaround is left in place as a
    safety net for the cases that still reset.

## [0.21.5] - 2026-07-31

### Changed
- **README grid cell corrected**: the multi-window YATAS screenshot
  belonged at 0-indexed grid position (1,1) — second row, second column,
  previously `main-yata.png`'s ("Teletype-paper theme with day grouping")
  cell — not (0,0), the top-left cell, which was mistakenly replaced
  earlier and has been restored to the original green-theme screenshot it
  always showed. `main-yata.png` is no longer referenced from the README
  (removed from `docs/screenshots/`, same treatment the green screenshot
  got when it was first displaced) since a 3×2 grid can only show one
  image per cell.

## [0.21.4] - 2026-07-31

### Fixed
- **The multi-window YATAS screenshot's two windows visibly overlapped**,
  covering part of the back window's task list. Root cause: the requested
  geometry for the back window (552px wide) was narrower than `Main.qml`'s
  own `minimumWidth: toolbar.actionButtonsWidth * 2`, which silently
  clamped it to ~760px on actual render — wide enough to push its right
  edge past the front window's left edge. The *requested* rectangles never
  overlapped; only the *rendered* ones did, so nothing caught it until the
  image itself was inspected. Fixed with real geometry picked live (both
  windows dragged/resized directly by hand until neither overlapped, then
  read back via `xdotool getwindowgeometry` against the already-rendered
  windows — not fed back in as a new request, so this specific clamping
  can't recur for these values) and a new sanity check in
  `run_yatas_multiwindow_scenario` that compares each window's requested
  size against its actually-rendered size and raises immediately if
  `Main.qml` clamped it, instead of only surfacing as a bad final image.

## [0.21.3] - 2026-07-31

### Fixed
- **The multi-window YATAS screenshot had a visible seam and transparent
  gaps** between the two windows — 0.21.2 captured each window separately
  (`import -window <id>`) and glued them together with ImageMagick, but
  each window's own translucent areas already bake in whatever was really
  behind *that* window during *its own* separate capture, so gluing two
  such captures together breaks background continuity between them
  (exactly what the user's carefully-chosen real desktop position was
  meant to preserve). Fixed by replacing the two-capture-then-composite
  step with a single live `import -window root -crop <geometry>` grab of
  the real, composited desktop region spanning both windows — safe now
  that `enable_always_below()` is neutralized for screenshot windows
  (0.21.2), so stacking is deterministic and `root` genuinely shows the
  front window on top.

## [0.21.2] - 2026-07-31

### Changed
- **README screenshots regenerated** for the current app version (multi-
  window YATAS, drag-and-drop, real-window dialogs, and all the other
  changes since the last capture). `scripts/capture_screenshots.py`'s
  `run_scenario()` predated the multi-window feature and never set the
  `windowManager`/`windowId` context properties `Main.qml` has required
  since — every scenario now builds its window via `main._make_window()`
  (the same construction path a real launch uses) instead of loading
  `Main.qml` by hand, fixing that. Also patches `enable_always_below()` to
  a no-op for screenshot windows only (it was silently breaking real
  `xdotool`-driven hover-glow capture) and lengthens the settle delays
  before each interaction (the heavier window construction needed more
  time to finish laying out than the old direct `engine.load()` did).
- **New top-left grid cell**: two real windows in one screenshot
  (`main-yatas-multiwindow.png`), demonstrating multi-window management —
  a Goldenrod-themed window with YATAS open (listing both windows) in
  front of a Black-themed window showing its own task list, replacing the
  old plain green-theme screenshot. Composited from two individually
  captured windows (not a single live screen-region grab — each window's
  own translucent areas already bake in whatever was really behind them at
  capture time, which would look wrong pasted over a different
  background). Position/size for both windows picked interactively by the
  user on the real desktop, same procedure as the existing single-window
  capture geometry.

## [0.21.1] - 2026-07-30

### Fixed
- **Cross-window drag placeholder animation lagged noticeably**, more so
  than the same-window reorder case. `TaskDelegate.qml`'s `onCentroidChanged`
  ran the expensive per-move work — `windowManager.windowAt()`'s Python
  round trip + cross-window broadcast, and `moveDragGhost()`'s real native
  OS window reposition — directly on every raw pointer-move event, which
  can fire far more often than the screen redraws. That saturated the event
  loop with comparatively costly native window moves; the cross-window
  placeholder update depends on that same single-threaded loop, so it
  visibly lagged behind the always-locally-smooth same-window case. Fixed
  by decoupling: `onCentroidChanged` now only records the latest pointer
  position (cheap, local), while a new 16ms-interval `Timer` drives the
  actual `windowAt()`/`moveDragGhost()` work at a capped, steady ~60fps.

## [0.21.0] - 2026-07-30

### Added
- **YATAS soft-delete/recreate/purge lifecycle.** Deleting a window from the
  YATAS list no longer immediately discards it: `WindowManager.deleteWindow`
  now closes it and marks it "deleted" in the registry, keeping its
  registry entry and on-disk tasks/settings intact. Two new actions handle
  what happens next, both only ever shown on a DELETED row: **Re-create**
  (same icon as a task's "re-active" — `WindowManager.recreateWindow`)
  restores it to ACTIVE and reopens it from its still-on-disk data; **Purge**
  (`WindowManager.purgeWindow`, always confirmed via new
  `PurgeWindowDialog.qml`) permanently removes its registry entry and
  deletes its data — the only way any of it actually gets discarded now.
  Soft-deleted windows are never restored at app startup regardless of
  their "open" field (`main.py`'s `_windows_to_restore`), and never count
  against `next_available_tag`'s dedup check (they aren't currently
  visible).
- **YATAS sub-toolbar reworked to match**, only while the Yatas view is
  active (reverts to the normal task sub-toolbar otherwise): the Day/Month/
  Year calendar group hides entirely (a window list has no date concept),
  the visibility group becomes ACTIVE/DELETED (independent toggles, both
  can be shown together), and the order group mirrors the same two options
  (single-select, brings whichever category is picked to the top when both
  are visible) — new `yatasShowActive`/`yatasShowDeleted`/`yatasSortMode`
  properties on `FilterBar.qml`, relayed into `YatasView.qml` via
  `Main.qml`, same pattern as `toolbar.searchText`'s existing relay.

## [0.20.0] - 2026-07-30

### Changed
- **Every confirmation dialog is now a real top-level window**, not a
  QtQuick.Controls `Dialog`/`Popup` rendered inside its parent YATA window's
  own Overlay layer. Concretely fixes the "Delete window?" and "Delete
  task?" dialogs being part of the exact same X11 window as their parent —
  which has `_NET_WM_STATE_BELOW` set on it (see `x11_stacking.py`) so YATA
  stays beneath other apps on the desktop, meaning a confirmation dialog
  could pop up hidden behind whatever else was on screen. New shared
  `DialogWindow.qml` base (a nested `Window {}`, auto-`transientParent`-ed
  to its enclosing YATA window by Qt Quick, never itself passed to
  `enable_always_below()`) replaces both `DeleteWindowDialog.qml`'s and
  `TaskDelegate.qml`'s inline `Dialog`s — same external API (`open()`,
  `accepted`/`rejected`, centered over its parent, `Qt.WindowModal`,
  Escape/Enter handling), zero `Dialog {` usages remain anywhere in the app.

## [0.19.4] - 2026-07-30

### Fixed
- **The floating drag preview window was far wider than the (correctly
  elided) text it showed** for long tasks — `DragGhost.qml` sized itself
  from `label.implicitWidth` (the full, un-elided text's natural width),
  while the label itself was already capped to 320px and elided beyond
  that. Fixed by sizing off `label.width` (the actual, capped/possibly
  elided on-screen width) instead.

## [0.19.3] - 2026-07-30

### Fixed
- **Cross-window task drops still always landed at the top of the destination
  window's list**, even though the placeholder correctly showed a specific
  row. 0.19.2 only fixed *same-window* reordering — `WindowManager.
  moveTaskToWindow()` handed the moved task to `TaskListModel.insert_task()`,
  which unconditionally inserted at index 0 regardless of where the
  placeholder was hovering in the target window. Fixed by having each
  window's `Main.qml` report its own live placeholder row index back to
  `WindowManager` (`setDragHoverIndex`) as it's computed, so
  `moveTaskToWindow()` can read it back at drop time and land the task right
  after that row — the same "insert after the target" semantics `moveTask()`
  already uses for same-window drags.

## [0.19.2] - 2026-07-30

### Fixed
- **A dropped task landed higher up the list than the placeholder showed**
  — a semantic mismatch left over from 0.19.0's redesign: the drop
  placeholder renders *below* the hovered row (meaning "insert right after
  this one"), but `TaskListModel.moveTask()` still inserted *before* the
  hovered row, a leftover from when the old thin-line marker sat at the
  *top* of the hovered row instead. Every drop landed one position higher
  than shown — most noticeably "at the top" when dropping just below the
  first row. Fixed by inserting after the target task instead of at its
  index.

## [0.19.1] - 2026-07-30

### Fixed
- **0.19.0's drop placeholder cut through the middle of the row above it**
  — `TaskDelegate.qml`'s row content (`mainRow`) was still vertically
  centered in the whole delegate, so when the placeholder made a row taller
  to reserve space below it, the centered content shifted *down* into that
  reserved space instead of staying put, overlapping the placeholder.
  `mainRow` is now top-anchored with a fixed margin instead, so its
  position no longer depends on how much extra height the placeholder
  adds. Confirmed visually via an offscreen render (with the height
  animation given real time to settle, unlike a first, too-quick capture
  that was misleadingly inconclusive) — the placeholder now sits cleanly
  between the two rows with no overlap.

## [0.19.0] - 2026-07-30

### Added
- **Task lists now reflow with a highlighted drop placeholder while
  dragging**, instead of just a thin line — the row being dragged
  collapses out of its original spot, and a row-shaped placeholder opens up
  wherever it would land, pushing the rows after it down to make room. This
  works identically for same-window reordering and for hovering a
  *different* YATA window during a cross-window move — one mechanism drives
  both, via `WindowManager.taskDragHoverChanged` now also broadcasting the
  pointer's global position so whichever window is currently the target can
  translate it into its own list's local coordinates. Placeholder color is
  the same "cyan by default, tint's own accent color for CRT themes" rule
  already used for every other active/hover glow in the app
  (`Theme.filterGlowColor`) — the window-border drop-target highlight from
  0.18.0 was switched to the same color for consistency.
- **The list now auto-scrolls while dragging near its top or bottom edge**
  (and stops correctly once already at the start/end) — works in whichever
  window's list is currently the drop target, same as the placeholder.
- `WindowManager.windowAt()` no longer excludes the caller's own window —
  same-window and cross-window hovering are now just two cases of "which
  window is currently under the pointer," rather than separate code paths.

## [0.18.4] - 2026-07-30

### Fixed
- **0.18.3's drag preview broke drag-and-drop entirely** — the moment a
  drag started, showing the `DragGhost` window silently cancelled the
  `DragHandler`'s active pointer grab in the source window, since a newly
  mapped window taking focus/activation on X11 can do that even when it's
  otherwise click-through. `Qt.WindowTransparentForInput` alone stops it
  from *receiving* clicks but not from taking window focus; added
  `Qt.WindowDoesNotAcceptFocus` to `DragGhost.qml`'s window flags, which is
  what actually prevents it.

## [0.18.3] - 2026-07-30

### Added
- **A floating preview of the task now follows the cursor while dragging**,
  visible even outside the source window's own bounds (e.g. while hovering
  over a different YATA window mid cross-window move) — previously only the
  mouse cursor itself was visible during a drag. New `DragGhost.qml`: a
  single, app-wide, frameless, always-on-top, click-through window (built
  once at startup, reused for every drag regardless of which window/row
  started it) showing the dragged task's text and status, trailing just
  past the cursor. `WindowManager` gained `showDragGhost`/`moveDragGhost`/
  `hideDragGhost` slots, called from `TaskDelegate.qml`'s `DragHandler`
  alongside the existing same-window/cross-window drag logic.

## [0.18.2] - 2026-07-30

### Changed
- **Task drag-and-drop (same-window reorder and cross-window move) now
  works by pressing anywhere on the row**, not just the small "⋮⋮" handle
  glyph — that glyph is now a purely visual hint, still shown on hover while
  reordering is possible. Replaced the handle's dedicated `MouseArea` with a
  row-wide `DragHandler`, which only takes the exclusive grab once the
  pointer actually crosses the platform's real drag threshold — a plain
  click, double-click-to-edit, link tap, hover-button tap, or right-click
  (context menu) never reaches that threshold, so every other gesture on
  the row keeps working unchanged. This is the standard Qt Quick mechanism
  for letting a tap and a drag coexist on the same item.

## [0.18.1] - 2026-07-30

### Fixed
- **Cross-window task drag printed "windowManager is not defined" to the
  console right after a successful drop.** Root cause: moving a task to
  another window removes it from the source window's model, which
  synchronously destroys the very `TaskDelegate` instance whose own
  `MouseArea.onReleased` handler was still executing — the very next
  statement's bare `windowManager` identifier could no longer be resolved
  through that now-torn-down delegate's context. Fixed by capturing
  `windowManager` (and reusing the already-captured `view`) into local JS
  variables *before* the model-mutating call, so the rest of the handler
  references already-resolved object references instead of re-doing a
  scope lookup afterward. Reproduced and confirmed fixed in isolation with a
  minimal throwaway QML harness before touching the real file, to be sure
  the fix pattern (not just this specific line) was actually correct.

## [0.18.0] - 2026-07-30

### Added
- **Drag a task from one YATA window and drop it onto another to move it
  there.** Uses the task row's existing drag handle (the same "⋮⋮" gesture
  already used for same-window reordering) — drag it past your window's own
  edge onto a different YATA window and the target window's border glows
  cyan; release to move the task there (text/status/created_at/completed_at
  all preserved), or release back inside the source window to reorder as
  before. Implemented as pure in-process coordinate math rather than real
  platform drag-and-drop: `WindowManager.windowAt()` finds which open
  window's on-screen geometry contains the pointer's global position
  (computed in `TaskDelegate.qml` via each window's own `x`/`y`, no
  `QQuickWindow.mapToGlobal` dependency), `moveTaskToWindow()` transfers the
  task directly between the two windows' in-process `TaskListModel`
  instances via new `take_task()`/`insert_task()` methods (also used to
  simplify `deleteTask()`/`addTask()` internally). `WindowManager` gained a
  `taskDragHoverChanged` signal so every window can light up its own border
  only when it's the actual drop target.

## [0.17.5] - 2026-07-30

### Added
- **New windows created via YATAS+ADD no longer duplicate an existing tag.**
  If a window is already named e.g. "YATA", the next new one is named
  "YATA - 2" instead of a second identical "YATA" — `n` is one more than the
  highest number already in use for that base name (so "YATA - 2" and
  "YATA - 5" both existing produces "YATA - 6" next, not "YATA - 3").
  `WindowRegistry` gained `next_available_tag(base_tag)`; only
  `WindowManager.createWindow()` uses it — `add()`/`renameWindow()` still
  allow duplicate tags freely, since a manual rename is the user's own
  explicit choice.

## [0.17.4] - 2026-07-30

### Added
- **The SHOW eye icon hides itself on the last open window.** Closing it
  would leave nothing on screen and no YatasView left to reopen anything
  from, so `YatasRow.qml` now hides the button entirely (not just disables
  it) when its own window is the only one currently open — a closed window's
  row always keeps its button, since reopening is always safe.
  `WindowManager.closeWindow()` enforces the same "at least one must stay
  open" guard independently (silent no-op, same pattern as
  `TaskListModel`'s visibility filters), so the invariant holds even if
  something other than this button ever calls it.

## [0.17.3] - 2026-07-30

### Fixed
- **YatasView's SHOW eye icon overshot after the 0.17.2 nudge** — the user
  confirmed live it now sat too far below the trash/DELETE icon. Pulled back
  up by a literal 15px (`Layout.topMargin: Math.round(Theme.taskFontPixelSize
  * 0.2) - 15`), per direct pixel feedback rather than another proportional
  guess.

## [0.17.2] - 2026-07-30

### Fixed
- **YatasView's SHOW eye icon still sat too high relative to the trash/DELETE
  icon** even after matching `Layout.alignment`, since the eye's tightly-
  cropped SVG box and the trash emoji's own line-height box (which reserves
  descender padding, pushing the visible glyph above its box's true center)
  don't share an optical center. Nudged down via `Layout.topMargin:
  Math.round(Theme.taskFontPixelSize * 0.2)` to match, per a side-by-side
  before/after mockup from the user.

## [0.17.1] - 2026-07-30

### Fixed
- **YatasView's new SHOW eye icon was too large and not vertically centered
  with the trash/DELETE icon next to it** — shrunk to 65% of its previous
  size (`IconIndicator`'s `sizeScale: 1.15 * 0.65`, height follows via its
  own aspect-ratio sizing) and given an explicit `Layout.alignment:
  Qt.AlignVCenter` to match.

## [0.17.0] - 2026-07-30

### Added
- **SHOW toggle button in the YATAS window list**, next to DELETE, using the
  same eye icon as the sub-toolbar's visibility-filter group. Tapping it
  closes the corresponding window (hides it, keeping its tasks/settings and
  registry entry intact) or reopens it, rebuilt fresh from its own persisted
  data — same as at app startup. The button visually reflects the window's
  current state: full brightness while shown, dimmed while closed. A
  window's open/closed state is itself persisted immediately (`WindowRegistry`
  gained an `open` field) and honored on the next app launch — a closed
  window stays closed across a restart instead of reopening on its own,
  unless every window was closed, in which case startup reopens everything
  rather than launching with nothing on screen and no way to reach YATAS.
  `WindowManager` gained `openWindow`/`closeWindow` slots and now reports
  each window's *live* open state (not just the persisted one) through
  `listWindows()`.

## [0.16.3] - 2026-07-30

### Fixed
- **Settings (theme, geometry, filters — any window setting) could silently
  fail to persist across a restart**, most visibly with "Switch zoom
  direction": toggling it off worked correctly for the rest of the session,
  but the app came back up with it checked again next launch. Root cause:
  every setter in `AppSettings` and `TaskListModel` called
  `QSettings.setValue()` but never `.sync()`, relying entirely on Qt's
  deferred/implicit flush (a periodic auto-sync or a sync triggered by the
  `QSettings` object's own destruction) to eventually get the value onto
  disk. That flush depends on teardown ordering that isn't guaranteed —
  confirmed directly: writing a value and letting the process exit without
  an explicit `sync()` left the on-disk `.ini` file completely unwritten.
  Fixed by calling `self._settings.sync()` immediately after every
  `setValue()` (geometry writes batch into one `sync()` call rather than
  one per field) — every setting is now written to disk the moment it
  changes, matching the standing "remembers its settings immediately, per
  window" requirement, rather than only when something else happens to
  flush it later.

## [0.16.2] - 2026-07-30

### Changed
- **Font zoom (Ctrl+=/Ctrl+Wheel) max raised from 2x to 200x** — per request,
  "preferably indefinitely, even if it looks ugly and unreadable." Not
  literally unbounded: `font.pixelSize` is still a real `int` under the
  hood, and an astronomically large `fontScale` risks overflow there; 200x
  (2800px base task text) is far past anything anyone would actually scroll
  to while staying nowhere near that ceiling. `AppSettings` gained
  `minFontScale`/`maxFontScale` read-only properties (mirroring the
  existing `defaultFontScale`) so the 4 places in `Main.qml` that clamp
  zoom (two keyboard shortcuts, two `Ctrl+Wheel` branches) read from one
  source of truth instead of hardcoding the bounds themselves.

## [0.16.1] - 2026-07-30

### Fixed
- **Zooming (Ctrl+=/Ctrl+-/Ctrl+Wheel) repeatedly logged "Binding loop
  detected for property implicitWidth" for TaskDelegate's "Delete task?"
  confirmation dialog.** That `Dialog` had no explicit `width`, so Qt Quick
  Controls derived `implicitWidth` from its own font-scaled content —
  circularly, on every font-size change. Gave it an explicit
  `width: Math.max(260, Math.round(Theme.taskFontPixelSize * 20))`, the same
  fix/formula already used for `DeleteWindowDialog.qml`.

## [0.16.0] - 2026-07-30

### Added
- **Double-click a window's tag label (on its own top border) to rename it
  in place** — previously the only way to rename was via a row in the
  YATAS list. Swaps the label for an editable field styled like the
  toolbar's search box (same rounded, subtly-tinted background), spanning
  from the label's own start position to half the window's width. Enter or
  clicking away commits the rename (empty/unchanged input is a no-op,
  matching the YATAS list's own rename field); Escape cancels.

## [0.15.7] - 2026-07-30

### Fixed
- **Windows created via YATAS+ADD never came back after restarting the
  app.** `main()` only ever reopened the original/default window at
  startup — any additional window was silently skipped forever after
  (its tasks/settings stayed safely on disk, just never shown again,
  with no way to reopen it since a plain click on its YATAS row is
  intentionally a no-op). Fixed: startup now reopens every window in the
  registry, each at its own persisted position/theme/content, falling back
  to seeding one fresh window only if the registry is completely empty
  (every window, including "default", was explicitly deleted). The
  restore-list logic was pulled out into a small pure function
  (`_windows_to_restore()`) specifically so this has real regression test
  coverage (`tests/test_main.py`) without needing a live QML engine.

### Notes
- The `TypeError: Cannot read property ... of null` messages some users see
  in the console right after pressing Ctrl+C are expected app-quit teardown
  noise (bindings evaluating once more against already-torn-down context
  properties) — not a bug, and predates this whole multi-window feature.

## [0.15.6] - 2026-07-29

### Fixed
- **`Main.qml` logged "Binding loop detected for property width" on every
  window.** Introduced by 0.15.4's `width: Math.max(appSettings.width,
  minimumWidth)` fix — `width`'s own binding read `appSettings.width`,
  which `onWidthChanged` (right below it) writes to on every `width`
  change, a shape QML's binding-loop detector correctly flags even though
  it happened to converge rather than truly infinite-loop. Fixed by moving
  the "grow to at least minimumWidth" correction out of `width`'s
  declarative binding entirely, into a plain imperative
  `ensureMinimumWidth()` function called from `Component.onCompleted` and
  `onMinimumWidthChanged` — `width: appSettings.width` stays a simple,
  loop-free binding, exactly like before 0.15.4, and the imperative
  assignment breaks/replaces it only when the floor actually needs
  enforcing (same as a user's own resize already does), still persisting
  correctly afterward via the existing `onWidthChanged` handler.

## [0.15.5] - 2026-07-29

### Fixed
- **The window tag label was invisible (or only showed its bottom half) on
  a real live window**, even though it rendered fully in every offscreen
  test used to verify it. Root cause: it was positioned at `y:
  -height / 2` to straddle the border line like a fieldset legend — but a
  `QQuickWindow`'s actual drawable surface starts at `y=0`; content above
  that is genuinely off-surface and isn't rendered on a real GPU-backed
  window (the offscreen `grabWindow()` backend used for testing turned out
  to be more forgiving of negative-`y` content than a live one, which is
  why this was never caught before shipping). Fixed by reserving real space
  instead: the border and background wash `Rectangle`s now start
  `tagLabelBg.height / 2` down from the window's actual top edge (via
  `anchors.topMargin`), and the label itself sits at `y: 0` — its vertical
  center still lands exactly on the border's (now-inset) top edge, achieving
  the same straddling look with nothing ever positioned off-surface.

## [0.15.4] - 2026-07-29

### Fixed
- **Window could open narrower than its own toolbar needed**, clipping
  toolbar buttons and the window's tag label at the window's own edge — a
  window's *persisted* width from before the YATAS button existed (which
  grew the real minimum needed) wasn't being raised back up to the new
  `minimumWidth` on open; the `minimumWidth` hint alone isn't reliably
  WM-enforced for this frameless window's explicitly-bound width. `width`
  is now `Math.max(appSettings.width, minimumWidth)` instead of relying on
  the hint alone. Also added elide-safety to the tag label itself (capped
  and ellipsized against the window's actual width) so an unusually long
  custom tag name can't overflow past the window edge either, independent
  of the width fix above.

## [0.15.3] - 2026-07-29

### Fixed
- **Delete-window dialog was undersized and its checkbox unreachable.** The
  dialog's width was a fixed 360px that didn't scale with font zoom (unlike
  everything else in the app), so at a larger zoom the text ran past the
  dialog's edges — now `Theme.taskFontPixelSize`-scaled like `ThemeMenu`'s
  width. The checkbox's label lived inside `CheckBox.contentItem` with a
  manually-computed `leftPadding`, which fought the Basic style's own
  indicator/content positioning — the indicator ended up rendered mid-
  sentence in the label text, with its actual clickable area not matching
  where it visually appeared. Replaced with a plain `CheckBox` (untouched
  default indicator) next to a separate `Label` in a `RowLayout`, with the
  label also tap-to-toggle for a larger hit target.

## [0.15.2] - 2026-07-29

### Fixed
- **Theme changes stopped applying, and icons disappeared, after 0.15.0's
  multi-window support.** Root cause: `Theme.qml`'s *filename* still defined
  an implicitly-importable QML type named "Theme" (Qt's directory-import
  convention maps filenames to types regardless of `pragma Singleton`),
  which silently collided with the "Theme" context property every window
  now injects. QML's compiled-bindings path resolved the (no-longer-
  registered) type reference instead of falling back to the context
  property, leaving every `Theme.*` binding in every other `.qml` file
  permanently `undefined` — rendering as default Qt colors (black text,
  white/opaque backgrounds instead of each theme's real colors) and, for
  icons specifically, an invalid recolor tint that made them vanish
  entirely. This is why it was easy to miss during 0.15.0's own testing:
  reading a `Theme` property directly off the live Python object always
  returned the correct value, and so did dynamically-evaluated QML
  expressions — only *compiled* property bindings elsewhere in the app were
  affected, which nothing in that testing checked. Fixed by renaming the
  file to `yata-src/qml/ThemeImpl.qml` (content unchanged) — it's still
  injected as the context property named "Theme", so no other `.qml` file
  needed to change. Confirmed via a from-scratch reproduction isolating the
  filename as the sole variable, and via a live check that both text color
  and background now update correctly when the theme changes.

## [0.15.1] - 2026-07-29

### Fixed
- **Clicking ADD while YATAS was active didn't create a window, and crashed
  `WindowManager.createWindow()`** — it called `dict(caller_state)` directly
  on the argument, but QML passes a JS object literal as a `QJSValue`, not
  something Python's `dict()` can iterate (`TypeError: 'QJSValue' object is
  not iterable`). The uncaught exception firing mid-callback appears to be
  what caused the wave of "Unable to assign [undefined] to QColor" errors
  and the "theme stopped working" symptom the user saw right after — a
  live, QML-triggered reproduction confirms window creation and every
  window's `Theme` both work correctly once the argument is unwrapped via
  `QJSValue.toVariant()` before use.

## [0.15.0] - 2026-07-29

### Added
- **Multi-window support** (`claude-docs/freq/r-3.md`): YATA can now run
  several independent windows in one process, e.g. to keep work and personal
  todos apart. Each window has its own tasks, theme, position/size, and a
  "tag" (display name) shown on its own top border like a fieldset legend.
  The original/pre-existing window keeps using its original data/settings
  files unchanged (`tasks.json`, `~/.config/yata/yata.conf`) for full
  backward compatibility; every window created afterward gets its own
  dedicated files under `instances/<id>/`.
  - New "YATAS" toolbar button switches the content area to a list of every
    known window (mutually exclusive with DAY/MONTH/YEAR/LINKS, same as
    those already were with each other). Double-click a row to rename its
    tag; each row has a delete button that always asks for confirmation via
    a themed (but not opacity-affected) dialog, with an unchecked-by-default
    option to also delete that window's tasks/settings — closing the window
    first if it's currently open, even if it's the one you're looking at.
  - While YATAS is active, the toolbar's ADD button creates a new window
    (cloning the current window's theme, auto-positioned to avoid
    overlapping existing windows) instead of a new task, and the search
    field filters window tags with a "Search for window" placeholder.
  - Architecturally: `Theme.qml` is no longer a `pragma Singleton` (a
    singleton is one instance per QQmlEngine, shared by every window —
    incompatible with per-window theming), instead created fresh per window
    and injected as a context property alongside a new `WindowManager`
    (`yata-src/window_manager.py`) and `WindowRegistry`
    (`yata-src/window_registry.py`, the persisted id+tag list). `main.py`
    now builds every window (including the first) through one shared
    `_make_window()` factory using `QQmlComponent`/`QQmlContext` instead of
    `QQmlApplicationEngine.load()`.

### Fixed (during the above)
- A `QQmlComponent` object must itself stay alive for as long as anything
  it created (via `.create()`) is in use — not just the created object or
  its `QQmlContext` — or the created object's underlying C++ instance gets
  torn down out from under a still-live Python reference (surfaced as
  `libshiboken: Internal C++ object (QQuickWindow) already deleted` the
  next time anything touched it). `_make_window()` and `WindowManager`
  together keep every component/context/object alive for each window's
  whole lifetime.

## [0.14.3] - 2026-07-24

### Changed
- **main-yata.png (teletype-paper theme) regenerated at full opacity** (was 65%) — the translucent look washed out the paper-cream background against the desktop behind it. `scripts/capture_screenshots.py`'s `main-yata` scenario now sets `opacity=100`.

## [0.14.2] - 2026-07-24

### Fixed
- **main_settings.png's popup was in the wrong corner.** `scripts/capture_screenshots.py` opened the ThemeMenu via a direct `popup()` call without first moving the mouse there — `Menu.popup()` with no arguments opens at the *current cursor position*, not anchored to its button, so it landed wherever the pointer happened to be left over from a previous scenario. Fixed by moving the pointer onto the THEME toolbar button immediately before calling `popup()`, matching what a real click would do. Regenerated `docs/screenshots/main_settings.png`.

## [0.14.1] - 2026-07-24

### Changed
- **Regenerated all README screenshots** to reflect the current toolbar
  (LINKS button, redesigned FilterBar) and added a 6th: the Links view with
  a hover-glowing "to task" button. New `scripts/capture_screenshots.py`
  drives a real, isolated, live app instance per scenario (theme/filters/
  hover targets set programmatically, then captured via ImageMagick's
  `import`) so this never has to be redone by hand again — see the script's
  own docstring for usage and how to re-pick the capture window's position/
  zoom if the target monitor layout ever changes.
- README's Features list now documents the Month/Year calendar views and
  the Links view, both previously undocumented there.

## [0.14.0] - 2026-07-24

### Added
- **Search now works in the Links view.** The toolbar's search field is
  shared between contexts: while Links is active its placeholder switches
  from "Search for task" to "Search for link", and typing filters the link
  list by link **label or URL** (case-insensitive substring), client-side
  against the already-fetched link list — a separate filter context from the
  main list's task-text search, which keeps running unaffected underneath.
  Shows "No links match your search" instead of "No links found in any task"
  when a search yields zero results but links do exist.

## [0.13.5] - 2026-07-24

### Changed
- **"To task" flash duration shortened to 1.2s** (was 2s), still 3 blinks —
  `TaskDelegate.qml`'s per-blink `NumberAnimation` duration and `Main.qml`'s
  clearing `Timer` interval both updated to match.

## [0.13.4] - 2026-07-24

### Changed
- **"To task" flash now blinks 3 times over 2s** (was a single flash+fade
  over 1.5s): `TaskDelegate.qml`'s flash animation is now a
  `SequentialAnimation { loops: 3 }`, each iteration an instant jump to full
  glow opacity followed by an eased fade over 1/3 of the total 2s. The
  clearing `Timer` in `Main.qml` was bumped from 1500ms to 2000ms to match.

## [0.13.3] - 2026-07-24

### Changed
- **"To task" flash highlight redesigned**: instead of reusing the plain
  hover background tint, `TaskDelegate` now has a dedicated flash overlay
  that jumps instantly to full brightness in the app's glow color
  (`Theme.filterGlowColor` — the same color used for FilterBar's active-toggle
  glow) and fades out over 1.5s with an eased (`Easing.OutCubic`) curve, so it
  reads as "sudden flash, slow fade" rather than a flat on/off tint.

## [0.13.2] - 2026-07-24

### Fixed
- **LinksView "to task" navigation now visually highlights the destination
  row.** Clicking "to task" scrolls the main list to that task but doesn't
  move the real mouse cursor, so the row never got the usual hover tint and
  looked unselected. `TaskDelegate` now also tints its background when
  `ListView.flashTaskId` matches its own task id; `Main.qml` sets that
  property (and a 1.5s `Timer` clears it) right after `positionViewAtIndex`.
  Only the background tint is replicated — wrap/elide and the action-button
  row still require a real hover, so the flash can't be mistaken for one or
  accidentally clicked.

## [0.13.1] - 2026-07-24

### Changed
- **LinksView row layout**: the status tag now sits *beneath* the link list
  (`LinkRow.qml`'s links `Text` and `StatusTag` are stacked in a `Column`),
  matching how the status tag sits beneath the task name in the main list —
  previously it was a leading sibling on the same line.
- **Links now show their label, not the raw URL** — `models.py`'s
  `linkedTasks()`/`_MARKDOWN_LINK_RE` now capture both the `[label]` and
  `(url)` parts of each Markdown link (falls back to the URL itself for the
  rare empty-label case); the URL is still the click target, just not what's
  displayed. All links per task are shown, comma-separated (already worked —
  re-verified after this change since it touched the same code path).
- **"To task" icon** halved in size (`taskFontPixelSize × 1`, was `× 2`) and
  moved 8px further from the row's right edge (`Layout.rightMargin: 8`).

## [0.13.0] - 2026-07-24

### Added
- **Links view** (`claude-docs/freq/r-2.md`): a new "LINKS" button in the main
  toolbar (`ADD RELOAD THEME LINKS [Search]`) replaces the task list with a
  list of every task that mentions at least one Markdown `[label](url)` link
  — regardless of status or the current visibility/search filters, since
  it's a lookup across all tasks, not the filtered view. Mutually exclusive
  with Day/Month/Year (activating any one of the four clears the rest,
  matching the existing FilterBar pattern — the mutual-exclusivity state and
  logic stays centralized in `FilterBar.qml` even though Links' own toggle
  button lives in `Toolbar.qml`; `Main.qml` relays between the two).
- Each row (`LinkRow.qml`) shows: a status tag (`StatusTag.qml`, new —
  ACTIVE/DONE/CANCELLED, colored + glowing, ACTIVE has no timestamp unlike
  the other two), the task's URL(s) as clickable links (opens the default
  browser via `Qt.openUrlExternally`, same as the main list's Markdown
  links), and a "to task" icon button (new
  `resources/assets/noun-link-7985857.svg`, Noun Project, attribution
  stripped from the file per the established pattern and added to README)
  that switches back to the task list and scrolls to that task.
- New `Theme.activeTagColor` — "white with glow" per spec; `Theme.textColor`
  for the "none" theme (already correctly near-white in dark mode without
  being illegible in light mode, unlike a literal white), `Theme.accentColor`
  for CRT tints (each tint's own most prominent color).
- `models.py`: `linkedTasks()` (sparse list of tasks with Markdown links,
  `@Slot(result='QVariant')`) and `indexForTask(task_id)` (row index in the
  current visible list, for the "to task" scroll-to behavior — mirrors
  `indexForDate`). 6 new tests.

## [0.12.4] - 2026-07-22

### Fixed
- **YearView's grid could overflow past the right edge during a window-width
  resize**, leaving an asymmetric ~10px gap on the left and none (or
  negative) on the right — reproduced and measured: at one width the grid
  sat 8px from the left but overflowed the container by 10px on the right.
  Root cause: `Layout.alignment: Qt.AlignHCenter` positions a `GridLayout`
  using its implicit width from the *previous* layout pass, one frame behind
  its actual rendered width (which reacts immediately to `cellSize`-driven
  `Layout.preferredWidth` on each cell) — a fast resize could catch that gap.
  Fixed in both `YearView.qml` and `MonthView.qml` (same architecture, same
  latent bug, not yet reported there) by binding the grid's `x` directly to
  `Math.round((parent.width - width) / 2)` instead of relying on
  `Layout.alignment`, so position and width update atomically in the same
  binding pass. MonthView's weekday-label row and day grid are now grouped
  into one nested `ColumnLayout` and centered as a single unit, so the two
  rows can't drift out of alignment with each other either.

## [0.12.3] - 2026-07-22

### Fixed
- **`CalendarCell` label/count font sizes are now fractions of the cell's own
  computed size** (`Math.min(width, height) * 0.18`/`0.22`), not a fixed
  multiple of `Theme.taskFontPixelSize`. The fixed multiple didn't track
  either window resize or font zoom, so the (also too-large, per feedback)
  counts could outgrow their square at a small window or high zoom instead
  of staying bounded inside it.

## [0.12.2] - 2026-07-22

### Fixed
- **MonthView's weekday columns were uneven widths** ("Fri" narrower, "Tue"/
  "Sat" wider) — each column's width was implicitly driven by that weekday
  abbreviation's own proportional-font text width (`Layout.fillWidth: true`
  alone doesn't force equal columns in `GridLayout`), not a shared value.
  Fixed by computing an explicit `cellSize` and applying it as
  `Layout.preferredWidth` uniformly to both the weekday-label row and every
  day cell.
- **Day/month cells are now square**, sized off whichever dimension (grid
  width ÷ 7, or remaining window height ÷ 6) is tighter, instead of
  stretching to fill both independently. Applied to both `MonthView.qml` and
  `YearView.qml` for consistency. The grid centers itself when the square
  size leaves leftover space in the other dimension.

## [0.12.1] - 2026-07-22

### Fixed
- **`CalendarCell` counts were too small and the done count read as gray, not
  green.** Font size doubled (`0.85×` → `1.7×` task font, now bold). Done/
  cancelled counts now use `Theme.checkIconColor`/`Theme.crossIconColor` (the
  same green-check/red-cross semantic tokens the task list's status icons
  use) instead of `Theme.doneColor`/`Theme.cancelledColor` — those are the
  muted strikethrough *text* color for the task list (deliberately gray for
  the "none" theme), correct there but not what a status-color count needed.

## [0.12.0] - 2026-07-22

### Added
- **MONTH view**: FilterBar's "Month" button now shows a real month calendar
  grid (`yata-src/qml/MonthView.qml`) instead of just a visual toggle —
  always 7 columns (Monday-first), regardless of window width; cells shrink
  rather than the grid reflowing. Each day cell shows active/done/cancelled
  counts (only nonzero ones). Prev/next arrows page between months (no
  bound — old months with data are reachable). Clicking a day switches to
  DAY view and scrolls the list to that day.
- **YEAR view**: FilterBar's "Year" button shows a 12-month grid, 4 columns x
  3 rows (`yata-src/qml/YearView.qml`), each cell showing that month's
  active/done/cancelled counts. Prev/next arrows page between years.
  Clicking a month switches to MONTH view showing that month.
- New shared `CalendarCell.qml` (day/month box: label + 3 status counts,
  clickable) and `PagerArrow.qml` (‹/› pagination arrow), used by both views.
- `models.py`: `monthCounts(year, month)` and `yearCounts(year)` (sparse
  per-day/per-month status tallies, `@Slot(..., result='QVariant')`) and
  `indexForDate(year, month, day)` (row index in the current day-grouped
  list, for MonthView's day-click-to-scroll navigation).

## [0.11.4] - 2026-07-22

### Changed
- **README screenshots regenerated** against the current UI/version, using
  the committed mock fixture (`tests/fixtures/mock_tasks.json`) and a real
  live-desktop capture (not the offscreen test harness, which can't render
  `MultiEffect` glow or a translucent window's real desktop backdrop) at
  991×511 — same size as the originals — matching each original's theme,
  grouping state, and hover/popup target as closely as the redesigned UI
  allows: `main-green.png`, `main-goldenrod.png`, `main-dark.png`,
  `main-yata.png`, `main_settings.png`.
- **`main_order.png` removed** (file + README reference): it documented the
  old "Order" toolbar dropdown, which no longer exists — that control was
  merged into FilterBar's inline MANUAL/ACTIVE/DONE/CANCEL buttons earlier
  this session, so there's no current equivalent popup to screenshot.

## [0.11.3] - 2026-07-22

### Changed
- README's Noun Project icon attribution now names the license (Creative
  Commons Attribution / CC BY) with a link to the Noun Project's licensing
  page.

## [0.11.2] - 2026-07-22

### Changed
- **Search lupe color**: now matches the visible "Search for task"
  placeholder text exactly — `TextField.placeholderTextColor` is now
  explicitly `Theme.mutedTextColor` (was left at the Basic style's
  unspecified default) and the icon's `tint` is set to that same value,
  rather than `Theme.textColor` (only what *typed* text uses, and visibly
  brighter than the placeholder).
- **FilterBar row tightened**, per a mockup comparison: `Main.qml`'s
  `ColumnLayout` spacing 4px → 2px (closer to the toolbar above it);
  `FilterBar.qml`'s `Flow` is now vertically centered in its row (was
  top-anchored with the padding all below it, reading off-center) and its
  root `Item`'s height padding trimmed 6px → 4px; `FilterButton` label text
  0.8× → 0.75× the task font; new `IconIndicator.sizeScale` property (default
  1.0, only the three FilterBar group icons set `0.9`, leaving Toolbar's
  search icon unaffected) makes the group icons proportionally smaller.

## [0.11.1] - 2026-07-22

### Changed
- **Search field icon**: the plain "🔍" Unicode glyph is replaced with a
  proper SVG icon (`resources/assets/noun-search-2353120.svg`, Noun Project,
  attribution stripped from the file and added to README same as the other
  three icons), rendered via `IconIndicator` and tinted `Theme.textColor`
  (not the muted indicator color the FilterBar group icons use).
- **`IconIndicator` now sizes its box to each icon's own aspect ratio**
  instead of forcing every icon into the same square. A forced square gave
  narrow icons (the arrow-up-down order icon) dead horizontal padding inside
  their box, which visually pushed the following button (MANUAL) further
  away than the calendar→DAY or eye→ACTIVE gaps, despite identical spacing.
  Box height stays fixed (scales with the task font); box width is now
  `height × (implicitWidth / implicitHeight)`, read back from the loaded
  image itself — self-correcting for any future icon swap, not a hardcoded
  per-icon ratio.

## [0.11.0] - 2026-07-22

### Added
- **Responsive FilterBar wrapping**: the Day/Month/Year, visibility-filter,
  and sort-order groups now live in a `Flow` (each group its own inner
  `RowLayout`, so it wraps as a whole unit) instead of one fixed `RowLayout`.
  As the window narrows: order wraps below day+visibility first, then
  visibility also wraps below day (leaving order beneath that) — three
  stacked rows at the narrowest width, instead of silently overflowing off
  the right edge as before.
- **Minimum window width**: `Main.qml`'s `Window.minimumWidth` is now
  `toolbar.actionButtonsWidth * 2` — twice the combined width of the
  ADD/RELOAD/THEME toolbar buttons (`Toolbar.qml`'s new
  `actionButtonsWidth` property), which itself scales with font zoom since
  the buttons' own widths do.
- **Search field magnifying-glass icon**: a small static "🔍" now sits inside
  the search `TextField`'s left edge (mirroring the existing right-side
  clear-"✕" pattern, but non-interactive), muted-colored like other
  indicator icons.

## [0.10.4] - 2026-07-22

### Changed
- **At least one of Active/Done/Cancelled must stay visible.** `models.py`'s
  `setShowActive`/`setShowDone`/`setShowCancelled` now reject (no-op) a
  `False` call that would leave all three hidden — enforced in the model
  layer, so the FilterBar button for the last remaining visible filter
  simply doesn't turn off on click (no dialog, no error). Two existing tests
  (`test_filter_state_persists_across_restart`,
  `test_filter_false_persists_correctly`) previously set all three to
  `False` in sequence, which is no longer a reachable state — updated to
  leave one visible; new `test_visibility_last_filter_cannot_be_hidden`
  covers the guard itself.

## [0.10.3] - 2026-07-22

### Fixed
- **FilterBar gaps didn't scale with font zoom**: the 8px button spacing and
  18px inter-group gap were fixed pixel values, so at smaller zoom levels
  (`Ctrl+-`) they looked proportionally wider next to the shrunk text (and
  proportionally tighter when zoomed in). Both are now computed from
  `Theme.taskFontPixelSize` (`FilterBar.qml`'s new `buttonSpacing`/
  `groupGap` properties, 8px/18px at the default 14px task font, scaling
  linearly with it) so the row's proportions stay consistent at any zoom.

## [0.10.2] - 2026-07-22

### Added
- **"Year" grouping button**, alongside Day/Month in FilterBar's first group.
  Mutually exclusive with both Day and Month (at most one active at a time;
  the active one can be switched off entirely) via a new
  `FilterBar.setGrouping(which, checked)` helper that replaced the previous
  pairwise Day/Month cross-clearing logic. Like Month, Year has no backend
  yet — `taskModel` only supports day-grouping — so it's local UI state only.

### Changed
- Replaced the calendar icon: `resources/assets/noun-calendar-999733.svg` →
  `noun-calendar-999730.svg` (same artist, different Noun Project icon).
  Same treatment as before — attribution text stripped, `viewBox` tightened
  to the drawing bounds, `%FILLCOLOR%` placeholder added — and
  `resources.qrc`/`README.md` updated to the new filename.
- FilterBar button spacing tightened from 10px to 8px.

## [0.10.1] - 2026-07-22

### Fixed
- **IconIndicator icons rendered oversized, uncentered, and solid black** on
  a live run (reported with screenshots) instead of small/muted/centered.
  Two separate bugs:
  - Sizing: `IconIndicator.qml` set plain `width`/`height`, which a
    `RowLayout` child silently overrides during its own positioning pass —
    the icon fell back to the SVG's native intrinsic size instead of the
    intended fixed square. Fixed by using `Layout.preferredWidth`/
    `Layout.preferredHeight` instead, the actual layout API for this.
    Centering was already correct once sizing was; it just had nothing sane
    to center before.
  - Color: `MultiEffect { colorization: 1.0; colorizationColor: ... }` did
    not reliably recolor the icons on a live run (rendered flat black),
    unlike this codebase's other `MultiEffect` uses (shadow/glow), which do
    work. Replaced with a Python-side fix: new `yata-src/icons.py`
    (`IconProvider`, exposed to QML as the `iconProvider` context property)
    reads each embedded SVG via `QFile` — same pattern `main.py` already
    uses for the app icon — and substitutes a `%FILLCOLOR%` placeholder now
    baked into each SVG's root `fill="..."` attribute, returning a colored
    `data:` URI. (QML's own `XMLHttpRequest` was tried first and rejected —
    Qt blocks it from reading `qrc:` resources unless the process-wide
    `QML_XHR_ALLOW_FILE_READ=1` escape hatch is set.)

## [0.10.0] - 2026-07-22

### Added
- **Icon-prefixed unified control bar**: FilterBar and OrderBar are merged
  into one row: `<calendar> DAY MONTH   <eye> ACTIVE DONE CANCEL   <arrows>
  MANUAL ACTIVE DONE CANCEL`. `OrderBar.qml` was deleted; its buttons moved
  into `FilterBar.qml`. Each group gets a static, non-clickable icon
  (`IconIndicator.qml`) recolored to `Theme.mutedTextColor` via `MultiEffect`
  colorization — an indicator, not a control, so it's deliberately muted and
  ignores taps. "Cancelled" labels shortened to "Cancel" in both groups.
- **New "Month" grouping toggle**, mutually exclusive with "Day" (activating
  one clears the other; either can be switched off entirely). Purely a local
  `FilterBar.qml` UI property for now — `taskModel` has no month-grouping
  concept yet, so it visually works but has no backend effect.
- Three Noun Project SVG icons (calendar, visibility/eye, arrow-up-down) added
  under `resources/assets/`, embedded via `resources.qrc`'s new `/icons`
  prefix (same mechanism as the app icon/font, so they survive the Nuitka
  standalone build). Their in-file "Created by ... from the Noun Project"
  attribution text was stripped (required for them to render cleanly at icon
  size) and each SVG's `viewBox` was tightened to its actual drawn bounding
  box (native paddings varied wildly) — required attribution was moved to
  README.md's Third-party notices instead.

### Changed
- **Application icon relocated** to `resources/assets/app-icon.png` (was
  `resources/icon.png`). Updated `yata-src/resources.qrc` and
  `install-desktop.sh` to the new path and regenerated `resources_rc.py`
  (byte-identical embedded PNG — same file, just moved).

## [0.9.35] - 2026-07-22

### Added
- **ORDER sub-toolbar**: the "Order" dropdown menu (Manual/Active first/Done
  first/Cancelled first) is now a second sub-toolbar, `OrderBar.qml`, below
  the existing DAY/ACTIVE/DONE/CANCELLED FilterBar — same toggle-pill visual
  style, reusing `taskModel.statusSortMode`. Layout is now:
  `ADD RELOAD THEME [Search]` / `DAY ACTIVE DONE CANCELLED` /
  `ORDER: MANUAL | FIRST: ACTIVE DONE CANCELLED`. The "Order" `ToolButton`
  and its dropdown `Menu` were removed from `Toolbar.qml` entirely — this is
  the only way to change sort order now.

### Changed
- Extracted the toggle-pill button (glow-on-active, shared visual language
  for both FilterBar and the new OrderBar) out of `FilterBar.qml`'s inline
  `component FilterButton` into its own file, `FilterButton.qml`, so both
  bars use the identical component instead of duplicating it.

### Fixed
- `tests/test_focus_behavior.py::test_click_other_task_steals_focus` used a
  hardcoded pixel offset to click the second task row, which broke once
  OrderBar shifted the list down. Replaced with `_task_row_center()`, which
  reads the live QML item tree for the actual delegate position — robust to
  future toolbar/sub-toolbar layout changes instead of needing another
  manual recalculation.

## [0.9.34] - 2026-07-22

### Changed
- **Task text / hover-buttons spacing**: `TaskDelegate.qml`'s task-text
  `Column` now has `Layout.rightMargin: 50` (on top of `mainRow`'s existing
  4px `RowLayout` spacing), so the done/cancel/reopen/delete buttons sit at
  least 50px away from the task text instead of hugging it.

## [0.9.33] - 2026-07-22

### Fixed
- **Task text vertical alignment on hover**: `TaskDelegate.qml`'s task-text
  column was top-aligned within its row, which reads oddly once a row grows
  taller than its collapsed height (e.g. from the 0.9.32 hover-wrap fix, or
  the DONE/CANCELED label row). Now `Layout.alignment: Qt.AlignVCenter`, so
  the text centers vertically as the row resizes; the hover action buttons
  (done/cancel/reopen/delete) keep their own `Qt.AlignTop`, unchanged.

## [0.9.32] - 2026-07-22

### Fixed
- **List hover "jumping"** (`claude-docs/freq/r-1.md`): hovering over a task row
  switches its text between wrapped/elided, which changes the row's height —
  previously this happened instantly, so every row below shifted under the
  pointer in the same frame and the mouse would end up over the wrong row,
  especially sweeping first-to-last. Fixed two ways: `ListView.spacing` in
  `Main.qml` is now `0` (was `2`, the tiny gap that made adjacent rows'
  expand/collapse compound into a bigger jump), and `TaskDelegate.qml`'s row
  `height` now has a `Behavior` (`NumberAnimation`, 120ms, `InOutQuad`) so the
  resize animates smoothly instead of snapping.

## [0.9.31] - 2026-07-21

### Fixed
- **Filter persistence**: all five filter/view settings — DAY on/off, ORDER mode,
  ACTIVE/DONE/CANCELLED visibility — are now saved to `QSettings` the moment they
  change and restored on next launch. Previously only the theme, opacity, zoom
  level, and zoom direction were persisted. The model reads its initial state from
  the `filters/` settings group on construction; each setter writes immediately so
  a crash or external kill cannot lose the last-changed value.

## [0.9.30] - 2026-07-20

### Added
- **Auto desktop integration**: on startup the app checks
  `~/.local/share/applications/yata.desktop` for an `X-AppVersion=` field. If
  the file is absent or its version is older than the running binary, the app
  installs (or updates) the `.desktop` entry and icon automatically — no manual
  `install-desktop.sh` run required after updates.
- `X-AppVersion=` field added to `resources/yata.desktop` template and
  `install-desktop.sh` (populated from `pyproject.toml` version at install time).

## [0.9.29] - 2026-07-20

### Changed
- **Toolbar**: removed the DAY button; renamed STATUS → ORDER.
- **New filter bar** below the main toolbar: small toggle buttons DAY / ACTIVE /
  DONE / CANCELLED. Default: ACTIVE, DONE, CANCELLED are on (tasks visible),
  DAY is off (no day grouping). DAY now lives here instead of the main toolbar.
  Hiding a status hides all tasks of that status from the list; toggling back on
  shows them again. Styled like task-item action icons (text with cyan glow on
  hover). Implemented as `FilterBar.qml`; backed by three new model properties
  (`showActive`, `showDone`, `showCancelled`) on `TaskListModel`.

## [0.9.28] - 2026-07-20

### Fixed
- **Popup menus clip text at larger font scales**: THEME and STATUS popup menus
  did not expand when `fontScale` was increased, causing long items like "Switch
  zoom direction" to be cut off. Qt Quick Controls 2 does not reactively
  re-derive a `Menu`'s `contentWidth` from `MenuItem.implicitWidth` changes
  triggered by a `font.pixelSize` update. Fixed by explicitly binding each
  menu's `width` to `Theme.taskFontPixelSize * N` so it scales in sync with
  every zoom step.

## [0.9.27] - 2026-07-19

### Changed
- **Ctrl+wheel zoom direction**: scroll up now zooms in, scroll down zooms out
  (was reversed). The `wheelZoomInverted` setting flips this if the old
  behaviour is preferred.

## [0.9.26] - 2026-07-19

### Fixed
- **Clicking another task while editing keeps focus**: clicking on a non-editing
  task row's text or background did not move keyboard focus (those items are
  non-interactive and don't accept focus), so the editing TextField silently
  kept focus and `onEditingFinished` never fired. Root cause: `ListView` is a
  `Flickable` which already has `activeFocus=true` as an ancestor of the focused
  TextField — calling `forceActiveFocus()` on it is a no-op. Fixed by adding a
  `TapHandler` on every non-editing task delegate that calls
  `root.forceActiveFocus()` on the clicked delegate itself (a sibling of the
  editing delegate in the contentItem, so `activeFocus=false` before the tap),
  which genuinely steals focus and triggers `onEditingFinished`.
- **Shortcut console warnings**: `sequence: StandardKey.ZoomIn/ZoomOut` bound
  only to one of the multiple platform key sequences, producing warnings.
  Changed to `sequences: [StandardKey.ZoomIn/ZoomOut]` to bind all of them.

### Added
- `tests/test_focus_behavior.py`: two new QML integration tests that exercise
  the auto-focus-on-new-task and click-other-task-steals-focus paths using
  `QTest.mouseClick` on the real (offscreen) QQuickWindow.

## [0.9.25] - 2026-07-19

### Fixed
- **Auto-focus on new task (root cause found and fixed)**: diagnostics showed
  that `forceActiveFocus()` was working, but Qt stole focus back in the same
  event-loop tick (during click-event teardown). This triggered
  `onEditingFinished` immediately, which auto-saved "Task name", set
  `text.length > 0`, and hid the TextField — so the 100 ms focus timer found
  an invisible field. Fix: `suppressAutoSave` flag on the TextField, set `true`
  in `Component.onCompleted` and cleared on the next `callLater` tick, blocks
  the spurious `onEditingFinished` from saving. The 100 ms timer then finds the
  still-visible field and grants sticky focus.

## [0.9.24] - 2026-07-19

### Changed
- **Auto-focus diagnostics + Add-button focus-policy fix**: added `[yata focus]`
  console logging throughout the new-task focus chain to identify exactly where
  it breaks. Also set `focusPolicy: Qt.NoFocus` on the Add toolbar button so it
  can no longer steal keyboard focus on click (the default `Qt.StrongFocus`
  policy was a likely cause of the regression).

## [0.9.23] - 2026-07-19

### Fixed
- **Auto-focus on new task**: clicking "Add" now immediately places the cursor
  in the new task's text field so the user can type the name right away.
  Root cause was the ToolButton's click-completion handler reclaiming focus
  after the model's `beginResetModel`/`endResetModel` cycle. Fixed by adding a
  `taskAdded(taskId)` signal to the model (emitted after the model is fully
  ready) and a 30 ms timer in Main.qml that finds the new delegate by ID and
  calls `activateFocus()` on it — safely past any click-handling side-effects.
- Click-outside-without-typing saves the task as "Task name" (pre-existing
  behaviour in `onEditingFinished`, preserved).

## [0.9.22] - 2026-07-18

### Fixed
- **Bottom-of-list fade visible on "none" theme**: `Theme.contentBackground` is
  `"transparent"` for the "none" theme, making the previous gradient invisible.
  Added a dark/light fallback colour (`#111827` dark, `#f9fafb` light) so the
  fade indicator is visible on all themes.

## [0.9.21] - 2026-07-18

### Fixed
- **Bottom-of-list fade**: replaced the non-working `MultiEffect` mask approach
  with a simple gradient `Rectangle` overlay (`transparent` → `Theme.contentBackground`)
  painted on top of the list. Hidden when scrolled to the end.

## [0.9.20] - 2026-07-18

### Added
- **Bottom-of-list fade effect**: when the task list overflows the window, the
  bottom 10% of the list fades linearly from full opacity to transparent,
  hinting that more tasks lie below. The fade disappears automatically when
  scrolled to the very end. Implemented as a `MultiEffect` gradient alpha mask
  on the ListView layer, so it works for all themes including the transparent
  "none" theme.

## [0.9.19] - 2026-07-18

### Changed
- **Completion label status-word color respects tint theme**: in "none" mode,
  `DONE` stays `#22c55e` (green) and `CANCELED` stays `#ef4444` (red); in each
  CRT tint, both use palette-tuned colors at matching luminance in the tint's
  hue (`labelDone`/`labelCancelled` entries added to each palette). New Theme
  properties `completedDoneLabelColor` / `completedCancelledLabelColor` expose
  the values.

## [0.9.18] - 2026-07-18

### Changed
- **Completion label rendering split into two elements**: `DONE`/`CANCELED` is a
  separate `Text` with colored glow (same principle as action buttons); the
  timestamp bracket is a second plain `Text` with no glow, colored like the
  task name (`Theme.doneColor`/`Theme.cancelledColor`).

## [0.9.17] - 2026-07-18

### Changed
- **Completion label coloring**: only the status word (`DONE` / `CANCELED`) is
  now rendered in bright green/red; the timestamp bracket adopts the same color
  as the task name (`Theme.doneColor` / `Theme.cancelledColor`). Implemented via
  `Text.StyledText` with an inline `<font color>` tag on the status word only.

## [0.9.16] - 2026-07-18

### Fixed
- **Completion label: timestamp now fully colored** — added `textFormat: Text.PlainText`
  so Qt applies the green/red `color` property uniformly across the entire
  `"DONE [...]"` / `"CANCELED [...]"` string instead of only the status word.
- **Completion label font size raised to 75%** of task font (was 50%) for better
  readability.

## [0.9.15] - 2026-07-18

### Fixed
- **Completion label now always shows for done/cancelled tasks**: previously the
  label was hidden for tasks that were finished before 0.9.14 (their
  `completed_at` was `""`). The label now renders for all non-active tasks;
  tasks without a recorded timestamp show just `DONE` or `CANCELED` (no date
  bracket), while tasks finished since 0.9.14 show the full
  `DONE [DD-MM-YYYY HH:MM]` form.

## [0.9.14] - 2026-07-18

### Added
- **Completion timestamp label on finished tasks**: tasks with status "done" or
  "cancelled" show a second line beneath the task text reading
  `DONE [DD-MM-YYYY HH:MM]` or `CANCELED [DD-MM-YYYY HH:MM]`. The timestamp
  records the last time the task was moved to that state (re-finishing after a
  reset updates it). The label is green for DONE, red for CANCELED, at half
  the task font size, with the same MultiEffect glow used by the action buttons.
- `completed_at` field added to `Task` (storage). Old task files without the
  field load cleanly (defaults to `""`).

### Removed
- **✓/✕ prefix icons** on done/cancelled tasks replaced by the new timestamp
  label (which conveys the same information with more context).

## [0.9.13] - 2026-07-18

### Added
- **VT323 font bundled with the app**: `resources/VT323-Regular.ttf` is
  compiled into `yata-src/resources_rc.py` via `pyside6-rcc` and registered
  at startup with `QFontDatabase.addApplicationFont(":/fonts/VT323-Regular.ttf")`.
  The font is now available in both `./run.sh` and the Nuitka single-file
  binary (`./build.sh` regenerates `resources_rc.py` before building).
  `yata-src/resources.qrc` declares the mapping.

## [0.9.12] - 2026-07-18

### Added
- **Ctrl+Wheel zooms font size**: scroll down = zoom in, scroll up = zoom out
  (matches the existing Ctrl+`+`/Ctrl+`-` shortcuts). A transparent overlay
  `Item` (z:999) intercepts Ctrl+Wheel before the ListView's Flickable can
  consume it for scrolling; unmodified wheel events propagate normally.
- **"Switch zoom direction" in Theme menu**: checkable item that inverts the
  wheel direction (scroll up = zoom in, scroll down = zoom out). Persisted in
  settings as `theme/wheelZoomInverted`.

## [0.9.11] - 2026-07-18

### Changed
- **Long tasks collapse to one line with ellipsis when not hovered**: task text
  now uses `wrapMode: NoWrap` + `elide: ElideRight` at rest, expanding to full
  word-wrap only when the row is hovered (or in edit mode). Row height adjusts
  automatically since it is bound to the layout's implicit height.

## [0.9.10] - 2026-07-18

### Changed
- **Neon cyan glow on task action buttons**: hovering over ✓, ✕, ↺, or 🗑
  triggers a neon cyan (`#00FFFF`) glow using `QtQuick.Effects.MultiEffect`
  (zero-offset shadow + blur). Cursor also becomes a pointer hand on hover.

## [0.9.9] - 2026-07-18

### Fixed
- **Popup menus affected by window opacity**: status, theme, context, and
  delete-confirmation menus (which render in Qt's `Overlay` layer) now always
  appear at 100% opacity regardless of the user's opacity setting. Previously
  `Window.opacity` was used for the translucency effect, which OS-level scaled
  the entire window including the Overlay, making menus invisible at very low
  opacity values. Fixed by moving the opacity binding from `Window` to a
  content-wrapper `Item`; the `Overlay` layer sits above that `Item` in the
  window tree and is not affected by its opacity.

### Changed
- **Links in task text are now clickable**: clicking a `[label](url)` link
  opens it in the default browser (`Qt.openUrlExternally`). The cursor changes
  to a pointer hand when hovering over a link.

## [0.9.8] - 2026-07-18

### Fixed
- **No keyboard focus after ADD**: `forceActiveFocus()` is now called both in
  `onVisibleChanged` (when the editing TextField becomes visible) and in
  `Component.onCompleted` with a `Qt.callLater` retry, ensuring the cursor
  and keyboard input land in the new task's field reliably.
- **Click-away should commit new task with "Task name"**: `onEditingFinished`
  (which fires on genuine focus loss — toolbar click, click outside the list,
  etc.) now saves the typed text if any, or the placeholder "Task name" if the
  field is empty and the task is new (model text still ""). Existing tasks
  whose text was cleared are silently cancelled so the original text is kept.
- **Enter key overwrote typed text with "Task name"** (regression from 0.9.7):
  `Keys.onReturnPressed` now sets `committedViaEnter = true` before calling
  `setText`. `onEditingFinished` checks this flag and returns early, preventing
  the spurious fire that `beginResetModel()` (inside `_recompute()`) triggers
  as focus loss when the delegate is rebuilt after the model mutation.
- Added offscreen QML integration tests (`tests/test_qml_integration.py`) that
  run with a live QML engine to catch delegate-lifecycle bugs.

## [0.9.7] - 2026-07-18

### Fixed
- **ADD still showed no new item (0.9.6 regression)**: root cause identified and
  properly fixed. Qt Quick's `onEditingFinished` fires on *focus loss*, not just
  Enter — so when `setText` or any other model mutation calls `_recompute()` →
  `beginResetModel()`, the delegate's TextField loses focus synchronously, firing
  `onEditingFinished`, which called `deleteTask()` on the brand-new empty task
  before the user ever saw it. Fix: replaced `onEditingFinished` with
  `Keys.onReturnPressed` (fires only on an actual Enter keypress, not on focus
  loss) and `Keys.onEscapePressed` (Escape explicitly cancels the new task).
  Also kept the `addTask()` empty-task cleanup from 0.9.5, which handles the
  "press ADD again without typing" case cleanly.

## [0.9.6] - 2026-07-18

### Fixed
- **ADD shows no new item**: the `onActiveFocusChanged` handler added in 0.9.5
  fired during the transient focus flicker that occurs when the ListView
  rebuilds all delegates after a model reset (`beginResetModel/endResetModel`
  inside `addTask()`). The newly created TextField would briefly lose focus
  before `forceActiveFocus()` in `Component.onCompleted` re-acquired it, and
  the handler deleted the task before the user ever saw it. Fixed by wrapping
  the delete check in `Qt.callLater`, which defers it by one event-loop tick
  so all synchronous focus transitions settle first.

## [0.9.5] - 2026-07-18

### Fixed
- **Phantom "Task name" on click-away**: pressing ADD then clicking elsewhere without
  pressing Enter left an empty task persisted to disk (appearing to display "Task name"
  from the placeholder). `onEditingFinished` only fires on Enter, not on focus loss.
  Added `onActiveFocusChanged` to the edit `TextField`: if the field loses focus while
  the model text is still empty (never committed), the task is deleted automatically.

## [0.9.4] - 2026-07-18

### Added
- **Delete button on hover row**: trash bin icon (🗑) appended to the per-task
  action buttons visible on hover. Tapping it opens a modal confirmation dialog
  ("Delete task?" / "This action cannot be undone.") before calling
  `taskModel.deleteTask()`.

## [0.9.3] - 2026-07-18

### Fixed
- **Markdown link color** (again): `Text.linkColor` is unreliable even with
  `StyledText` on the Qt version in use — links were rendering in the normal
  text color. The `mdToHtml()` converter in `TaskDelegate` now embeds the
  color directly via `<font color="...">` inside each generated `<a>` tag,
  bypassing `linkColor` entirely. The binding passes `Theme.linkColor` as an
  explicit argument so QML's dependency tracker re-evaluates when the theme
  changes.

## [0.9.2] - 2026-07-18

### Fixed
- **Markdown link color** was still rendering as Qt's default blue regardless of
  `Theme.linkColor`, because Qt silently ignores `Text.linkColor` when
  `textFormat` is `Text.MarkdownText` (documented as "not well-defined" for
  non-StyledText formats). Fixed by switching to `Text.StyledText` with a
  `mdToHtml()` JS function on `TaskDelegate` that converts the markdown subset
  YATA uses — `**bold**`, `*italic*`, `~~strike~~`, `` `code` ``, `[label](url)` —
  to their HTML equivalents. `linkColor` is honoured by StyledText and the cyan
  `#22d3ee` / `#0369a1` colours from 0.9.1 now actually apply.

## [0.9.1] - 2026-07-18

### Changed
- **Opacity control** in the theme menu is now a draggable `Slider` (was a
  `ProgressBar` you had to click to get an edit field). The current
  percentage is shown as `"Opacity: XX%"` in a label above the slider and
  updates live while dragging.
- **Markdown link color** for the plain ("none") tint is now a vivid cyan
  (`#22d3ee` dark / `#0369a1` light) instead of the previous blue
  (`#60a5fa` / `#1d4ed8`), which was hard to read over gray backgrounds.
- **Theme menu bottom padding** fixed: the invisible `MenuSeparator` and
  Quit `MenuItem` (only shown when `showQuit: true`, i.e. the background
  right-click menu) now collapse to `height: 0` when hidden, rather than
  leaving blank space below the Tint submenu.

## [0.9.0] - 2026-07-17

### Added
- DPI awareness: `QGuiApplication.setHighDpiScaleFactorRoundingPolicy(PassThrough)`
  is set before the app is constructed (`yata-src/main.py`), so pixel sizes
  scale correctly with each monitor's actual reported scale factor.
- Font zoom: `Ctrl+=`/`Ctrl+-` (via `StandardKey.ZoomIn`/`ZoomOut`) grow/shrink
  `AppSettings.fontScale` (0.5x–2.0x, persisted), and `Ctrl+0` resets it.
  `Theme.taskFontPixelSize` derives from this scale, and every task-list size
  (day headers, status/hover icons) ratios off it as before; toolbar buttons
  and the search field get an explicit matching `font.pixelSize` since Qt
  Quick Controls don't expose a generic `Item`-level `font` property to
  inherit from.
- Window opacity is now a single user-configurable setting
  (`AppSettings.opacityPercent`, 5–100% integer, persisted, default 65)
  instead of a value baked into each theme tint. Set via a small progress
  bar in the theme menu — click it to switch to an editable integer field.
  Applies to the whole window; Menu popups are unaffected since Qt Quick
  Controls parents them into the window's Overlay layer, not the opacity'd
  root `Window` item.
- **New `yata-src/qml/ThemeMenu.qml`**, replacing the theme menu previously
  duplicated verbatim between `Main.qml` and `Toolbar.qml`. Layout: opacity
  row, RESET button (restores default opacity + font scale), Dark
  theme/Light theme, Tint submenu. Clicking "Dark theme" or "Light theme"
  now also forces the tint to plain (`themeTint = "none"`) — the Tint
  submenu's own "None" entry was removed, since Dark/Light now cover that
  look directly. The 4 CRT tints still ignore Dark/Light mode, but do follow
  the new global opacity and font-size settings.
- Markdown hyperlinks get a theme-aware `Theme.linkColor` (a legible
  light/dark-tuned blue for the plain look, each CRT tint's own accent
  color otherwise) — the previous default Qt link blue (`#0000FF`) was
  unreadable on dark backgrounds.
- Toolbar: reordered to ADD, DAY, STATUS, RELOAD, THEME, then the search
  field (now last, filling the remaining width). The `+` button is now
  labeled ADD. New RELOAD button re-reads `tasks.json` from disk via a new
  `TaskListModel.reloadTasks()` slot, for picking up externally-edited task
  files.
- The always-visible status icon (✓/✕ in front of done/cancelled tasks) is
  now the same size as the hover-only action icons (both
  `Theme.taskFontPixelSize * 2`), rather than a smaller fixed ratio.

## [0.8.1] - 2026-07-16

### Added
- `tests/fixtures/mock_tasks.json`: a 21-task, 3-day mock dataset for
  visually spot-checking day-grouping, status-sort, markdown rendering and
  long-text word wrap — day 1 has 15 tasks (6 active, 6 done, 3
  cancelled), day 2 has 5 done tasks, day 3 has 1 cancelled task. One
  day-1 task is 779 characters and exercises bold, italic, strikethrough,
  inline code and a link, all in the markdown subset `Text.MarkdownText`
  renders. `tests/test_mock_fixture.py` asserts the dataset's shape
  (task/day counts, per-day status breakdown, the long task's length and
  markdown) so it can't silently drift from this description.
- `BUILD.md`: documented how to point a real run of the app at this
  fixture via a throwaway `XDG_DATA_HOME`, without touching
  `~/.local/share/yata/tasks.json`. Verified live (2026-07-16): ran
  `./run.sh` with the fixture copied into a temp `XDG_DATA_HOME` — app
  launched cleanly, and the fixture file was confirmed byte-identical
  afterward (loading never triggers a save).

## [0.8.0] - 2026-07-16

### Added
- `build.sh`: packages the whole application into a single standalone
  executable, `dist/yata-X.Y.Z` (version read from `pyproject.toml`), via
  `pyside6-deploy` (bundled with PySide6, drives Nuitka under the hood).
  `nuitka` and `patchelf` are new `build` dependency-group entries (`uv add
  --group build`) so `pyside6-deploy` doesn't fall back to a raw `pip
  install` of them at build time. `pyside6-deploy`'s own qmlimportscanner
  step auto-detects and bundles `yata-src/qml/` and the Qt QML plugins the
  app actually uses. Documented in `BUILD.md`; `dist/`,
  `yata-src/deployment/` and `yata-src/pysidedeploy.spec` (build-time
  scratch files pyside6-deploy writes next to `main.py`) added to
  `.gitignore`.

## [0.7.0] - 2026-07-16

### Fixed
- On X11, the window now actually sits below other app windows (like the
  spec's "resting on the desktop, above icons" requirement), and stays
  there even once it has keyboard focus (e.g. via focus-follows-mouse).
  Previous attempts used Qt's `Qt.WindowStaysOnBottomHint`, which on
  GNOME/Mutter maps to `_NET_WM_WINDOW_TYPE_DESKTOP` and renders the window
  invisible (below the desktop icons layer itself) rather than merely
  below other windows — so that hint was dropped entirely back in 0.1.1.
  New `yata-src/x11_stacking.py` instead sends a raw EWMH
  `_NET_WM_STATE_BELOW` client message directly (via `python-xlib`, new
  dependency), leaving the window type as the default NORMAL. `main.py`
  calls `enable_always_below()` once the main window is shown (deferred via
  `QTimer.singleShot(0, ...)` so the platform window is actually mapped
  first) and it also reasserts the BELOW state on every `activeChanged`
  (focus) event, defensively, in case any WM ever clears it on activation.
  No-ops outside X11 (`QGuiApplication.platformName() != "xcb"`) — Wayland
  gives ordinary applications no equivalent stacking control, so on
  GNOME's default Wayland session the app still behaves like a normal
  window (documented in README.md's Known limitation section).
  Verified live on this machine's real GNOME/Mutter X11 session: `xprop`
  showed `_NET_WM_STATE_BELOW` and `_NET_WM_STATE_FOCUSED` set
  simultaneously, confirming the window stayed below while focused.

## [0.6.2] - 2026-07-15

### Changed
- The hover-only task-row action icons (check/done, cross/cancel, reopen)
  are now twice as large (`font.pixelSize: Theme.taskFontPixelSize * 2`,
  28px) — they previously had no explicit size (default font size) and
  were hard to hit precisely. Enlarged all three for visual consistency
  since they share a row and interaction style, even though the request
  named only the done/cancel pair.

## [0.6.1] - 2026-07-15

### Changed
- Day-section headers (and any other place a day is labeled) no longer show
  "Today" or "Yesterday" — `models.py`'s `day_label()` now always returns
  the full formatted date (`"%A, %d %B %Y"`), even for the current or prior
  day.

## [0.6.0] - 2026-07-15

### Changed
- The 4 CRT tints (green, goldenrod, white, black) now render the window at
  65% opacity, same as the "none" tint (previously they were fully opaque,
  1.0). `Theme.qml`'s `windowOpacity` is now `0.65` in every tint's palette
  entry.

## [0.5.2] - 2026-07-15

### Fixed
- Ctrl+C in the terminal didn't close the app. Qt's event loop runs
  entirely in C++ and never hands control back to the Python interpreter,
  so Python's default/custom SIGINT handling never actually got to run.
  `main.py` now installs a SIGINT handler that calls `app.quit()`, plus a
  200ms no-op `QTimer` whose only job is to periodically wake the
  interpreter so a pending signal is actually delivered.

## [0.5.1] - 2026-07-15

### Fixed
- The check/cross hover action icons on the right of a task row could
  render underneath the list's scrollbar thumb, since the scrollbar is an
  overlay (it doesn't reserve its own width in the layout). `Main.qml`'s
  `ListView` now exposes a `rowWidth` (its width minus the scrollbar's
  width when visible), and both `TaskDelegate` rows and the day-section
  header bind their width to it instead of the raw `listView.width`.

## [0.5.0] - 2026-07-15

### Removed
- The "blue" (DOS blue screen) tint. `THEME_TINTS` is now
  `("none", "green", "goldenrod", "white", "black")`.

### Added
- A small check/cross status icon now appears in front of non-active tasks:
  green check for done, red cross for cancelled (in the "none" tint). Under
  a CRT tint, these reuse that tint's own done/cancelled colors instead of
  literal green/red, so they stay tint-native (check reads brighter than
  cross in every tint, by the existing palette design).
- More left margin for task rows when "Day" grouping is on, so they read as
  nested under their day header instead of flush with it.
- More padding inside every menu item (theme menu, status-sort menu, task
  delete menu), so item text no longer looks stuck to the menu's edges.

### Changed
- Day-section header font size is now always 1.5x the task text size
  (`Theme.taskFontPixelSize`, 14px, is the new shared base — task text and
  the edit field now bind to it explicitly instead of relying on each
  control's own default).
- Day-grouped view now respects the active status-sort mode *within* each
  day (previously status sort was silently ignored whenever day grouping
  was on).
- Manual drag-to-reorder is now enabled while grouped by day (previously
  disabled entirely in that view). Dragging a task onto a different day's
  section reassigns that task to the target day (keeping its original time
  of day) in addition to repositioning it — so drag can move tasks between
  days, not just within one.

## [0.4.0] - 2026-07-15

### Changed
- "None (plain)" tint now uses Noto Sans (was the system default font) and
  renders the whole window at 65% opacity (was fully opaque) — the other
  five CRT tints are unaffected (still their own monospace font, still
  fully opaque). `Theme.qml`'s palette entries gained `fontFamily` and
  `windowOpacity`, and `Main.qml`'s root `Window` now binds
  `opacity: Theme.windowOpacity`.
- Toolbar button captions (DAY, STATUS, THEME) now render uppercase in
  every theme, via `font.capitalization: Font.AllUppercase` (the underlying
  text/tooltips are unchanged, only the rendered case).

### Added
- Generated a ~2-month mock task dataset (114 tasks, varied lengths,
  statuses weighted realistically by age, some intentionally empty days) to
  visually spot-check list/day-grouped views. Written to the real
  `~/.local/share/yata/tasks.json` used by the app; any pre-existing file
  was backed up alongside it first (`tasks.json.bak-<timestamp>`), not
  committed to the repo (it's local runtime data, not source).

## [0.3.0] - 2026-07-15

### Changed
- Reworked theming (`Theme.qml`) so tint affects far more than the border:
  active/done/cancelled task colors, content background wash, buttons,
  fields and the app font are all tint-driven now.
- Each of the five named tints now recreates a specific old CRT/terminal
  display instead of being a simple accent-color swap: **blue** = DOS blue
  screen (navy background, white/cyan text), **green** = classic green
  phosphor terminal, **goldenrod** = amber phosphor terminal, **white** =
  paperwhite CRT (white phosphor on near-black), **black** = teletype paper
  (dark ink on cream paper — the inverse of the others). All five use a
  monospace font and a translucent tint-colored background wash (the window
  itself stays technically transparent, per spec).
- Added a 6th tint, **"none"**, and made it the default (previously
  defaulted to "blue"). It's the explicit safe/plain option: no color wash,
  no monospace font, no done/cancelled color distinction — exactly the
  look the app had before this change, still following the light/dark
  toggle. `THEME_TINTS` in `settings.py` gained this entry.
- Both theme menus (toolbar "Theme" button and background right-click menu)
  gained a "None (plain)" entry in the Tint submenu.

## [0.2.0] - 2026-07-15

### Added
- "Theme" button at the right edge of the toolbar, opening the same
  light/dark + tint menu previously only reachable via right-clicking the
  window background (that background menu still works too).

### Changed
- Search field is now about half as wide as before (shares the toolbar's
  flexible space equally with an invisible spacer instead of claiming all
  of it), making room for the new theme button.

## [0.1.2] - 2026-07-15

### Fixed
- Quitting the app (e.g. via the system application bar's Quit action, or
  the background right-click menu's Quit item) printed a wall of
  `TypeError: Cannot read property ... of null` to stderr. Cause: `main.py`
  created `task_model`/`app_settings` before `engine`, and Python's
  function-local cleanup on return tore them down before the QML engine, so
  the engine's own teardown (destroying windows/bindings) read from
  already-dead context properties. Fixed by explicitly `del engine` right
  after `app.exec()` returns, forcing QML teardown to happen first while
  `task_model`/`app_settings` are still alive.

## [0.1.1] - 2026-07-15

### Fixed
- Window was invisible when actually run on a GNOME/Mutter desktop (X11),
  even though the process started fine. Root cause:
  `Qt.WindowStaysOnBottomHint` places the window below the desktop
  background layer on Mutter, not just below other app windows. Removed the
  hint; the app now shows as a normal frameless window. Updated
  `README.md`'s known-limitations section accordingly.

## [0.1.0] - 2026-07-15

### Added
- Initial YATA application, built from `docs/instructions.md`.
- Python backend (`yata-src/`): `storage.py` (Task model + JSON persistence),
  `models.py` (`TaskListModel` exposed to QML: add/edit/delete tasks, status
  changes, manual drag reordering, search, group-by-day, sort-by-status),
  `settings.py` (`AppSettings`: window geometry persisted per monitor layout,
  first-run centering at 20% screen width / 9:16 aspect ratio, theme mode +
  tint persistence), `main.py` entry point.
- QML UI (`yata-src/qml/`): frameless/transparent/bordered always-on-bottom
  window (`Main.qml`), toolbar with add/group-by-day/sort-by-status/search
  (`Toolbar.qml`), task rows with Markdown rendering, hover icons
  (done/cancel/reopen), inline editing, and drag-to-reorder
  (`TaskDelegate.qml`), and a `Theme` singleton (light/dark + 5 tints).
- Right-click context menus: theme + quit (background), delete task (task
  row) — the two interactions the spec implied but didn't describe a control
  for.
- Test suite (`tests/`): 24 pytest tests covering storage, model logic, and
  settings/geometry behavior.
- Project scaffolding: `pyproject.toml` (uv-managed), `run.sh`, `BUILD.md`,
  `README.md`, `.gitignore`.

### Known limitations
- `Qt.WindowStaysOnBottomHint` only works on X11; Wayland (GNOME's default
  session) does not let regular applications request that window layering.
