# Changelog

All notable changes to YATA are documented in this file.

The version scheme is `X.Y.Z`:
- `X` — major changes
- `Y` — minor changes
- `Z` — bugfixes, trivial changes, or changes unrelated to code (e.g. documentation)

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
