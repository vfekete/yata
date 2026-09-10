# Changelog

All notable changes to YATA are documented in this file.

The version scheme is `X.Y.Z`:
- `X` — major changes
- `Y` — minor changes
- `Z` — bugfixes, trivial changes, or changes unrelated to code (e.g. documentation)

## [0.45.0] - 2026-09-10

### Changed
- **Zoom (Ctrl+scroll/Ctrl+=/Ctrl+-/Ctrl+0) is now generic, host-owned
  window state, not a plugin-specific feature.** Explicit request: it
  "does not work" while the window list was showing, since zoom input
  handling lived entirely inside `plugins/simple_task_list/qml/
  TaskListContent.qml` — a `Shortcut`/`WheelHandler` pair that only
  existed within the plugin's own (now sometimes-hidden) content, so it
  had no effect while `YatasView` was active instead. Moved the input
  handling to `Main.qml` (host chrome), which now owns Ctrl+scroll/
  Ctrl+=/Ctrl+-/Ctrl+0 unconditionally, regardless of what's currently
  showing — "it is possible that in the future more global buttons will
  be added and zoom in/out functionality to their content will be
  expected", so this needed to be a real host-level mechanism, not
  something bolted onto one plugin.
- New `zoomLevel`/`wheelZoomInverted` properties on `yata-src/settings.py`'s
  host-owned `AppSettings` (persisted per-window, default `zoomLevel`
  `1.0` — "zoom level should be 1 per window", explicit request) — this
  is the formal host↔plugin zoom API: a plugin reads `hostSettings.
  zoomLevel` off the same globally-shared context property `hostSettings.
  borderColor` already used, and decides entirely on its own what to do
  with it. `plugin_api.py`'s own module docstring now documents this
  explicitly, since it's contract-level even though the actual channel is
  a QML context property rather than a new `PluginContent` field.
  `plugins/simple_task_list/settings.py`'s `TaskListSettings` no longer
  has `fontScale`/`wheelZoomInverted` at all — `ThemeImpl.qml`'s
  `taskFontPixelSize` now reads `hostSettings.zoomLevel` directly, the
  plugin's own choice to apply it to its font size. `ThemeMenu.qml`'s
  Reset item and "Switch zoom direction" toggle rebind to the same
  host-owned properties, no UI relocation needed (host settings are
  already reachable from any plugin's own QML). No migration of existing
  per-window zoom preferences off the old plugin-owned value — zoom
  simply starts fresh at the new default for existing windows going
  forward, a deliberate simplification.

### Fixed
- Verified live: Ctrl+=, Ctrl+0, and Ctrl+wheel all correctly change
  `hostSettings.zoomLevel` whether the plugin's own content or the host's
  `YatasView` is currently showing, `wheelZoomInverted` correctly flips
  scroll direction, and the plugin's own font size genuinely reflects the
  host-provided value end to end. New `tests/test_zoom.py`. Fixed
  `scripts/capture_screenshots.py`'s `_build_window()`, which still set
  the old plugin-owned `fontScale`/`wheelZoomInverted` fields.

## [0.44.3] - 2026-09-10

### Fixed
- **More live-feedback polish on the window-management view**, following
  up on 0.44.1/0.44.2:
  - The "Y" chrome icon's pushed/active look used a solid accent-colored
    fill that read visibly lighter than the lock/close icon boxes — now
    its background always matches theirs exactly (`chromeBoxColor`, hover-
    reactive only); "active" is communicated purely by the persistent
    glow, and the glyph itself stays visible at all times.
  - **Fixed a real visual bug**: locking the window (plain or auto-lock)
    while the window list was showing still visibly bled the glass-lock's
    frosted tint through underneath/around its content, even though
    blur/input-blocking were already correctly bypassed in 0.44.2 —
    `YatasView` had no opaque background of its own, so the (still-
    rendering, just now-hidden-behind-it) tint scrim showed through. Gave
    it its own solid background, same color the lock/close icons and the
    tag-rename field already use. New regression test asserts this
    background is genuinely fully opaque, not just present.
  - The ADD button and search field had solid near-black backgrounds
    that didn't match how these looked before the move — that opaque
    `chromeBoxColor` convention is right for icon buttons floating
    directly on the bare window frame (lock/close/tag), but the plugin's
    own toolbar buttons/fields (the actual "before" look) use translucent
    white overlays instead. Added `chromeFieldColor`/`chromeHoverColor`
    chrome constants matching `ThemeImpl.qml`'s own "none"-tint dark
    values exactly (`Qt.rgba(1,1,1,0.10)`/`Qt.rgba(1,1,1,0.08)`) and
    switched the ADD button (transparent at rest, translucent overlay on
    hover — matching the plugin toolbar buttons' own convention exactly),
    the search field, and the row hover/rename-field backgrounds to use
    them instead.
  - Verified every color value directly via live property inspection
    (not just screenshots, which can't reliably show glow effects
    offscreen).

## [0.44.2] - 2026-09-10

### Fixed
- **The window-management view ("Y" icon) was still subject to the glass
  lock** — while the window was locked or auto-locked (and not hovered),
  opening the window list showed it blurred and its buttons/rows didn't
  react to clicks, since `YatasView` lived inside `frostedContent`
  alongside the plugin's own content, sharing the same blur layer and
  input-blocking overlay. Window management is host-owned admin
  functionality, not something the lock is meant to protect — explicit
  request: it must show and stay fully usable no matter the lock state.
  `YatasView` now lives as a later sibling of `contentOverlay`
  (`contentBlocker`) instead of nested inside `frostedContent`, so it
  paints on top of the blur/tint/blocker and wins input delivery over
  `contentBlocker` (Qt Quick hands pointer events to the topmost item
  first) — no change needed to `contentBlocker` itself. Verified live
  (both plain "locked" and "auto-locked" while not hovered): double-
  click-to-rename works correctly with the window fully locked. New
  `tests/test_yatas_host.py::
  test_yatas_view_stays_visible_and_usable_while_locked` (confirmed it
  fails against the pre-fix code, passes after).

## [0.44.1] - 2026-09-10

### Changed
- **Follow-up polish on the new host-owned window-management view (0.44.0),
  from live feedback after actually seeing it on screen:**
  - The "Y" chrome icon's glyph was a distracting near-white — now the
    icon uses the window's own border color (falling back to the same
    default `#64748b` every other chrome accent uses) when off, and goes
    fully transparent when the view is active (the lit accent-colored box
    itself is the "on" indicator, so the glyph doesn't need to compete
    with it).
  - Removed the Active/Deleted visibility and sort-order controls
    entirely — just the plain list of windows now, search included. Every
    window (open, closed, or soft-deleted) shows together; each row's own
    button set already makes clear which category it's in.
  - "+ New Window" is now "Add" (bold, all-caps) — matching the plugin's
    own toolbar ADD button's look, for consistency across the host/plugin
    boundary.
  - The search field gained the same static "lupe" (magnifying glass)
    icon the plugin's own search field has, and the delete/purge
    confirmation dialogs' OK/Cancel buttons — previously plain, unstyled
    `QtQuick.Controls` buttons that stood out against the dark chrome
    panel — now use the same Rectangle+Text+hover-glow styling as every
    other chrome button. The content wash background behind the view no
    longer follows whatever tint the plugin's own content happens to be
    set to (a real, previously-unnoticed inconsistency: opening the
    window list while a non-default plugin tint was active showed it
    against that tint's own background) — it's fixed/transparent, the
    same "none" tint default every other chrome element already commits
    to regardless of plugin.
  - Verified the "Y" icon's color-switch logic directly (live property
    inspection, not just a screenshot) — confirmed correct even where an
    offscreen screenshot couldn't reliably show the glow effect actually
    rendering (a known, already-documented limitation of this project's
    offscreen test rendering, not a functional issue).

## [0.44.0] - 2026-09-10

### Changed
- **Window management ("YATAS": the window list, rename, show/hide,
  soft-delete/recreate, purge, and per-window border color) moved out of
  `plugins/simple_task_list/` and into host chrome.** r-9.md's step 4
  initially carried it into the plugin along with everything else, but
  window management is inherently the master application's own job (r-9's
  own original framing: "main window layouter... group window action
  executioner"), not any one plugin's — it must stay available no matter
  which plugin a window happens to be running. New `yata-src/qml/
  YatasView.qml`/`YatasRow.qml` (recycled from the plugin's own, now
  removed), toggled by a new "Y" chrome icon in `Main.qml` (placeholder
  glyph, sitting left of the lock icon) instead of the plugin toolbar's
  old "Yatas" button. Clicking it swaps `Main.qml`'s content area between
  the plugin's `Loader` and this new host-owned view — the `Loader` stays
  loaded (just hidden), so switching back is instant and loses no
  in-progress plugin state.
- Styled off `Main.qml`'s own fixed chrome palette (`chromeTextColor`/
  `chromeAccentColor`/`chromeBoxColor()`/...), not any plugin's `Theme` —
  same "chrome must look the same regardless of plugin" principle
  `Main.qml`'s border/lock/close/title already follow. New
  `yata-src/qml/HostDialogWindow.qml` (a chrome-styled twin of the
  plugin's own `DialogWindow.qml`) backs the also-relocated
  `DeleteWindowDialog.qml`/`PurgeWindowDialog.qml` — kept separate from
  the plugin's Theme-coupled version (still used by its own
  `NoteDialog.qml`) rather than shared across the host/plugin ownership
  boundary.
- "Add a new window" moved from the plugin toolbar's dual-purpose ADD
  button (context-sensitive: task normally, window while YATAS was
  active) into a dedicated button inside the new host view itself — the
  plugin's ADD button is unconditionally "add task" again. Still clones
  the creating window's own theme/zoom onto the new window (unchanged
  requirement), reading `appSettings.*` off the same shared `QQmlContext`
  the host chrome always had access to.
- The host view keeps its own small search field (word on this: dropped
  the *shared* field the plugin toolbar used to relay into it, per
  explicit decision — simpler than plumbing a cross-boundary relay for a
  feature that no longer shares a toolbar at all) and the same Active/
  Deleted visibility+sort toggles as before, now built from a small
  inline chrome-styled toggle component rather than the plugin's own
  `FilterButton.qml`.
- Verified live (offscreen `QTest`, real construction path): the plugin
  toolbar no longer has a Yatas button and its ADD button always adds a
  task; the "Y" icon correctly swaps content and back with plugin state
  intact; the add-window button clones theme onto a real new window;
  double-click-to-rename enters edit mode; the full delete → recreate →
  delete → purge round trip works end to end through the new host
  dialogs. New `tests/test_yatas_host.py`. Also fixed
  `scripts/capture_screenshots.py`'s multiwindow scenario, which drove
  the old plugin-level "yatas" grouping mode directly and would have
  silently done nothing once that mode was removed — now sets the host's
  own `yatasActive` property instead.

## [0.43.2] - 2026-09-10

### Fixed
- **r-9.md step 6: the packaged standalone binary (`build.sh`) couldn't
  actually launch** — `pyside6-deploy`'s QML auto-detection only finds
  files reachable via `yata-src/qml/Main.qml`'s own *static* QML imports;
  a plugin's content, loaded at runtime through a `Loader` whose `source`
  is a plain Python-computed `QUrl` string, is invisible to that scan. The
  plugin's `.py` files were correctly bundled (Nuitka follows the static
  import graph for those), but its `.qml` files were silently left out —
  confirmed live: the built binary launched, then immediately failed with
  `QQmlComponent: Component is not ready` / `ThemeImpl.qml ... No such
  file or directory` the moment it tried to load the plugin's own content.
  `build.sh` now also bundles each registered plugin's `qml_import_dir` as
  a Nuitka onefile data directory (`--include-data-dir`, the recursive
  equivalent of the `--include-data-files` already used for `x-loader`),
  generated from `plugins_registry.AVAILABLE_PLUGINS` rather than
  hardcoded to `simple_task_list` — a future plugin needs no `build.sh`
  change, just `qml_import_dir` set on its own `Plugin` entry. Verified by
  actually running the packaged binary (isolated `XDG_DATA_HOME`/
  `XDG_CONFIG_HOME`, no real data touched): failed with the error above
  before this fix, launched and ran cleanly with zero errors after.
  Documented in `BUILD.md` ("Build a standalone binary", "Project
  layout").

## [0.43.1] - 2026-09-10

### Fixed
- **`main.py`'s `APP_VERSION` had drifted from `pyproject.toml`'s version**
  (stuck at `0.41.0` across the 0.42.0-0.43.0 steps 4/5 work) — the same
  class of drift already fixed once before, in 0.38.4.
  `_ensure_desktop_entry` uses `APP_VERSION` to decide whether an
  already-installed desktop entry needs a resync on upgrade, so a stale
  value could make a newer build look "already current" to that check.
  `build.sh` has its own version-match gate that would have caught this at
  build time, but that's the last possible moment — added
  `tests/test_main.py::test_app_version_matches_pyproject_version` so a
  future drift fails `pytest` immediately instead.

## [0.43.0] - 2026-09-10

### Changed
- **r-9.md step 5: cross-window task drag&drop now routes through the
  plugin's own hooks.** `WindowManager.moveTaskToWindow()` previously
  reached into each window's registry entry by the hardcoded key
  `"task_model"` and called `TaskListModel.take_task`/`insert_task`
  directly — the last place `WindowManager` still assumed every plugin is
  `simple_task_list`. It now calls `plugin_content.take_item(task_id)` /
  `plugin_content.insert_item(item, target_index)` instead (the
  `plugin_api.PluginContent` hooks introduced in step 1 and already wired
  by `plugins/simple_task_list/plugin.py` to those same two model methods
  — unused by `WindowManager` until now). A window whose plugin leaves
  either hook `None` (a plugin with no concept of movable items) makes the
  move a no-op, same as a missing window entry — no crash.
- The `"task_model"` registry entry itself is unchanged and still set
  (`main.py`'s `register_window(..., task_model=...)`) — it's genuinely
  useful `simple_task_list`-specific convenience access for tests/tooling
  (`scripts/capture_screenshots.py`, several test fixtures), just no
  longer something `WindowManager`'s own logic depends on.
- Verified live (offscreen, real windows built through the real
  `plugin.py create_content()` path, not just the unit-level `FakeWindow`
  tests): confirmed each window's registered `plugin_content.take_item`/
  `insert_item` really are the same bound methods as its `task_model`'s
  own `take_task`/`insert_task`, and that a task dragged from one real
  window to another still moves correctly (data intact) through the new
  routing. Added `tests/test_window_manager.py::
  test_move_task_to_window_is_a_no_op_when_either_plugin_lacks_the_hooks`
  for the new graceful-degradation path.

## [0.42.2] - 2026-09-10

### Fixed
- **Dragging a task onto another window stopped showing that window's own
  drop placeholder/list reflow**, another regression from 0.42.0's step 4
  QML move. `TaskListContent.qml`'s `Connections{target: windowManager}`
  handler for `taskDragHoverChanged` read the bare `Window.window` attached
  property to convert the broadcast global drag position into local list
  coordinates — before step 4 this code lived directly inside `Main.qml`
  (the `Window`'s own QML document), where the bare form happened to
  resolve; once it moved into a separately `Loader`-loaded file, it
  silently resolved to `null` from inside that `Connections` function body,
  throwing and aborting the handler before `dragHoverActive`/
  `dragHoverIndex` were ever set. Main.qml's own independent host-side
  border highlight (a separate listener on the same signal) kept working
  fine throughout, which is what let this slip past the initial
  live-testing pass. Fixed by qualifying it as `contentRoot.Window.window`
  — the same pattern `TaskDelegate.qml`'s own `onCentroidChanged` already
  used for exactly this reason. Added `tests/test_cross_window_drag.py`
  (verified it fails against the pre-fix code with the exact same error,
  and passes after).

## [0.42.1] - 2026-09-10

### Fixed
- **Double-click-to-rename on the window's tag label silently stopped
  working**, a regression from 0.42.0's step 4 change that gave the tag
  label a second job (drag-to-move handle, since the plugin's own Toolbar
  no longer spans host-owned space). The new `MouseArea.onPressed:
  Window.startSystemMove()` handed the pointer grab to the window manager
  the instant the first click of a double-click landed, eating the second
  click before the sibling `TapHandler.onDoubleTapped` ever saw it.
  Confirmed live: the identical gesture renamed the tag correctly on the
  pre-step-4 code, and failed the moment the drag handle was added.
  Replaced the `MouseArea` with a `DragHandler` (`target: null`,
  `onActiveChanged: if (active) root.startSystemMove()`) — Qt's own
  recommended pattern for this exact coexistence, since a `DragHandler`
  only goes active once the press has moved past Qt's drag threshold, so a
  plain double-click (no movement in between) never triggers it. Added
  `tests/test_tag_rename.py` (verified it fails against the pre-fix code
  and passes after).

## [0.42.0] - 2026-09-10

### Changed
- **r-9.md step 4: the plugin's own QML content now loads through a
  `Loader`, not inline in `Main.qml`.** `Main.qml` is now a thin ~540-line
  host shell owning only what the master application actually controls:
  border color, the lock state machine + glass/blur effect, the close
  button, and the window title (tag display + rename). Everything else —
  toolbar, filters, the task list, calendar views, links/notes, and the
  whole theme system — moved into `plugins/simple_task_list/qml/
  TaskListContent.qml`, loaded via `Main.qml`'s `contentLoader` from a new
  `pluginContentUrl` context property (`plugin_api.PluginContent.
  qml_source`). Host chrome now uses fixed dark-mode/"none"-tint colors
  instead of the plugin's `Theme` — a different plugin could look
  completely different, and the host chrome must not depend on it.
- `plugin_api.PluginContent` gained `theme_qml_source` (the plugin's own
  Theme QML file, built by the host before `qml_source` — cross-file QML
  id lookup can't reach across separate documents, so this stays a
  host-loaded context property) and `Plugin.qml_import_dir` (added to the
  `QQmlEngine`'s import path so a plugin's own QML files can reference
  each other by bare type name).
- **Settings split**: `yata-src/settings.py`'s `AppSettings` now keeps only
  host-owned keys (window geometry, `borderColor`, `lockState`). The
  content-facing five (`themeMode`, `themeTint`, `opacityPercent`,
  `fontScale`, `wheelZoomInverted`) moved to new `plugins/simple_task_list/
  settings.py` (`TaskListSettings`), backed by `plugin_data.py`'s versioned
  envelope in its own file, with a one-time migration off the old shared
  QSettings keys for existing installs. `main.py`'s window construction
  passes the window's raw legacy `QSettings` through to the plugin once,
  for that migration only.
- `plugin_api.PluginContent` also gained two informational lifecycle hooks
  a plugin may set (`on_lock_state_changed`, `on_window_closing`) — neither
  can veto the transition, they just let a plugin react. Unused by
  `simple_task_list` today.

### Fixed
- **The plugin's own settings object (`appSettings`/`TaskListSettings`,
  and in principle any other plugin `context_properties` value) could be
  garbage-collected shortly after a window was built**, since nothing kept
  a Python reference to `plugin_content` past `_make_window()`'s own return
  — unlike `task_model`, which was already protected via an explicit
  `register_window(task_model=...)` kwarg. Confirmed live: every
  `appSettings.*` QML binding (theme mode/tint, opacity, font scale,
  wheel-zoom) started reading back `null` the moment the event loop got a
  chance to run garbage collection. `main.py`'s `_make_window()` now also
  passes `plugin_content=plugin_content` to `register_window()`, keeping
  the whole `PluginContent` (and every QObject it references) alive for
  the window's lifetime — same pattern already used for
  `theme_component`/`main_component`.
- `scripts/capture_screenshots.py` (README screenshot regeneration) still
  called the pre-step-4 `_make_window()` signature (a raw `TaskStore` +
  `AppSettings` pair) and would have failed outright the next time someone
  ran it. Updated `_build_window()` to build a real `PluginContent` via
  `plugins_registry` (matching `main.py`'s own `window_factory`/
  `restore_factory` split of host- vs. plugin-owned settings), and added
  the same per-plugin `engine.addImportPath()` registration `main()` does.
- Verified live: full test suite (241 tests) green; a real, on-screen
  `main.py` launch (isolated `XDG_DATA_HOME`/`XDG_CONFIG_HOME`, no real
  data touched) ran for several seconds with zero QML console errors;
  `capture_screenshots.py --scenario main-green` produces a correctly
  rendered, visually unchanged screenshot.

## [0.41.0] - 2026-09-10

### Changed
- **r-9.md step 3: window creation now routes through the plugin
  registry.** New `yata-src/plugins_registry.py` (`build_registry()`,
  `AVAILABLE_PLUGINS`, `get()`) statically registers
  `plugins/simple_task_list`, filtering out any plugin whose declared
  `min_api_version` this host's `plugin_api.API_VERSION` can't satisfy.
  New `plugins/simple_task_list/plugin.py` exposes `PLUGIN`/
  `create_content()`, building the same `TaskListModel`/`TaskStore` pair
  as before behind the `Plugin.create_content(window_id, tasks_path,
  settings)` contract, plus `take_item`/`insert_item` hooks (wired for
  `WindowManager.moveTaskToWindow` to adopt in step 5).
- `main.py`'s `_make_window`/`window_factory`/`restore_factory` no longer
  construct `TaskListModel`/`TaskStore` directly — they ask the registry
  for the window's plugin (`WindowRegistry.get_plugin`) and set whatever
  context properties `create_content()` returns. QML is completely
  unaffected (still binds `taskModel` etc. exactly as before) — no `.qml`
  file was touched by this step.
- `plugin_api.PluginContent.qml_source` is now optional (`None` by
  default): it isn't consumed anywhere until step 4 moves QML into a
  plugin-owned `Loader`.
- Verified live (mocked `XDG_DATA_HOME`/`XDG_CONFIG_HOME`, not real data):
  multi-window creation via YATAS, theme-cloning onto the new window, and
  full restore of both windows (tags, theme, content) across an app
  restart — all unchanged from before this step.

## [0.40.0] - 2026-09-10

### Changed
- **r-9.md step 2: task-list code relocated into `plugins/simple_task_list/`.**
  `yata-src/models.py`/`storage.py` moved to
  `plugins/simple_task_list/{model.py,storage.py}` (all imports across
  `main.py`, tests, and `scripts/capture_screenshots.py` updated
  accordingly; repo root added to `sys.path` in `main.py`/
  `tests/conftest.py` so the `plugins` package resolves).
  `window_registry.py` gains its own `data_dir()` (previously imported
  from `storage.py`) — host code depending on a plugin's internals would
  be backwards, so `plugins/simple_task_list/storage.py` keeps its own
  private copy for its legacy-default-window fallback instead.
- **`tasks.json` now uses `plugin_data.py`'s versioned block envelope.**
  `TaskStore` reads/writes through it (`model_version`/`api_version` both
  `"1.0"` for now); a pre-existing bare-JSON-array file (every file that
  existed before this change) still loads correctly and is transparently
  upgraded to the enveloped format on its next save — verified against
  real task data, not just tests.
- Fixed a bug in `plugin_data.write_block()` found while testing this:
  it crashed (`AttributeError`) writing into a file that predates the
  envelope entirely (a bare list, e.g. old `tasks.json`), since it assumed
  any existing file content was already a dict. Now treats non-dict
  existing content as "no envelope yet" and starts a fresh one.
- The `AppSettings`/theme/filter settings split into a plugin-owned
  versioned file (also planned for this step) is deferred to step 4,
  when the QML that reads those properties moves into the plugin package
  anyway — splitting the Python object now would need a throwaway
  QML-compatibility shim in the meantime for no benefit.

## [0.39.1] - 2026-09-10

### Added
- `plugin_api.Plugin` gains a required `copyright` string field (e.g.
  `"(C) 2026, Vladimir Fekete, MIT License"`) — every plugin declares its
  own copyright/license notice as part of its registration.

## [0.39.0] - 2026-09-10

### Added
- **First groundwork for r-9.md's plugin-capable window architecture** —
  purely additive, no behavior change yet:
  - `window_registry.py` entries now carry a `plugin` field (which plugin
    owns a window's content), defaulting every existing/new entry to
    `"simple_task_list"` via the same upgrade-safe pattern already used for
    `open`/`deleted`.
  - New `yata-src/plugin_api.py`: the `Plugin`/`PluginContent` contract a
    future plugin package implements, plus an `API_VERSION` constant the
    host bumps only on an incompatible contract change.
  - New `yata-src/plugin_data.py`: a versioned data-block envelope for
    plugin-owned files. A plugin only ever reads the newest block whose
    `model_version`/`api_version` floors it satisfies, and only ever writes
    the block matching its own current floors — any block it can't read
    (e.g. left by a newer plugin/API version, then downgraded) is skipped,
    never deleted, so nothing is ever silently lost across a
    plugin/host version change.
  - Nothing in the app wires either of these in yet — `simple_task_list`
    isn't a real plugin package yet, and `tasks.json`/settings storage are
    unchanged. That's the next step.

## [0.38.4] - 2026-09-09

### Fixed
- **Close ("X") button could stay stuck looking disabled on windows that
  were not the last one open** — e.g. 2 of 4 windows disabled at startup.
  `WindowManager.openWindowCount` (see 0.38.3 below) is a `Property`
  notified only by `windowsChanged`, but `register_window()` never emitted
  it. At startup, windows are registered one at a time; each window's
  `Main.qml` reads `openWindowCount` once, at the moment it's constructed
  — so a window registered early (while the live count was still <= 1)
  never got notified once later windows joined, and its close button
  stayed dimmed even with several windows open. `register_window()` now
  emits `windowsChanged` too, so every already-open window's binding
  re-evaluates against the true count as each new window registers.
  (`createWindow()`'s own now-redundant emit — it calls the factory, which
  calls `register_window()` — was removed to avoid a double emit.)

## [0.38.3] - 2026-09-09

### Fixed
- **Close ("X") button looked fully interactive even on the only open
  window**, where clicking it is already a safe no-op
  (`WindowManager.closeWindow`'s own "at least one must stay open" guard)
  — it just didn't LOOK disabled: full brightness, hover color change,
  pointer cursor. Added `WindowManager.openWindowCount` (a real reactive
  `Property`, notified by the same `windowsChanged` every mutator already
  emits — a plain `windowManager.listWindows().length` inside a QML
  binding would NOT update reactively, per the exact same gotcha already
  documented on `getBorderColor`/`listWindows`) and a
  `root.canCloseThisWindow` in `Main.qml` bound to it. The close icon's
  `MouseArea` is now `enabled: root.canCloseThisWindow` (so hover/click
  stop reaching it entirely once it's the last window) and its background
  box dims to 0.35 opacity to match.

### Testing
- New `tests/test_window_manager.py` cases for `openWindowCount` tracking
  and emitting `windowsChanged`.
- New live-QML `tests/test_close_window_button.py` case
  (`test_close_button_looks_disabled_once_it_is_the_only_window`) checking
  the button's actual `opacity`/`MouseArea.enabled`/`containsMouse` after
  closing down to one window — verified to fail without the fix before
  trusting it green.

## [0.38.2] - 2026-09-09

### Fixed
- **Toggling a status sort back off (no move involved) still reshuffled
  the list**: 0.38.1 fixed this for the case where a task is actually
  moved while sorted, but clicking the "Active" (or Done/Cancel) button a
  SECOND time — to turn the sort off directly, with no move at all — had
  the identical bug: `setStatusSortMode("")` just cleared the flag and let
  the stale pre-sort manual order resurface. "Visibility [filters] is not
  order" — turning ordering off must not itself look like a reorder.
  Extracted the rebase logic from `_reposition` into a shared
  `_rebase_manual_order()`, now also called from `setStatusSortMode()`
  when clearing an active sort back to `""`.

### Testing
- New `tests/test_models.py` case (`test_toggling_status_sort_off_directly_
  freezes_the_sorted_order_too`) and a live-QML companion in
  `tests/test_task_order_controls.py` (`test_toggling_active_sort_off_
  live_freezes_the_sorted_order`) pin the exact reported scenario. Both
  deliberately verified to fail without the fix before trusting them
  green.

## [0.38.1] - 2026-09-09

### Fixed
- **Order-control icons**: the "^"/"v" ASCII characters added in 0.38.0
  were meant as illustrative shorthand in r-7.md, not a literal spec —
  replaced with real icons (`resources/assets/move_up.svg`/`move_down.svg`,
  simple filled triangles, recolored via the same `iconProvider.
  coloredSvgUri()` pipeline as every other themed icon in this app) sized
  noticeably bigger and with a clear vertical gap between them, so they're
  easy to spot and tell apart at a glance.
- **Reordering while a status sort is active reshuffled to the wrong
  order**: selecting e.g. "Active" first (so actives sort to the top),
  then moving one active task, correctly switched ordering back to Manual
  but the list jumped to show Done/Cancelled tasks first instead of
  keeping Active-first with just that one move applied — because the
  underlying manual order (`self._tasks`) had never been touched while the
  sort was active, so clearing the sort resurfaced whatever unrelated
  manual order existed from before the sort was ever turned on. "Moving a
  task means the CURRENT order is now manual," not "reshuffle to some
  other order." Fixed in `TaskListModel._reposition()` (replacing
  `_switch_to_manual_if_needed`): when a sort is active, the manual order
  is now rebased to match what's currently visible — with the requested
  move already applied — before the sort is cleared; tasks hidden by
  search/visibility filters keep their existing relative position. Shared
  by both `moveTask` (drag&drop) and `_move_by_one` (the up/down buttons).
- **Month/Year: ordering sub-toolbar hover-glowed and let drag-through move
  the window**: the group was correctly shaded via `opacity`, but disabling
  it via a plain `enabled: false` excludes an item from hit-testing
  entirely rather than making it inert, so presses/hover fell through to
  whatever's behind it — here, the FilterBar's own full-width "drag empty
  space to move the window" MouseArea. Fixed with an enabled/hoverEnabled
  `MouseArea` (`orderBlocker`) stacked on top of the group instead, the
  same "claims hover/press away from what's underneath" idiom the glass
  lock's `contentBlocker` (Main.qml) already uses.

### Testing
- New `tests/test_models.py` cases pin the exact reported scenario (mixed
  Active/Done/Cancelled tasks, Active-sort selected, move one active task,
  assert the FULL resulting order — not just that the sort mode reset) for
  both `moveTaskUp`/`moveTaskDown` and `moveTask`.
- `tests/test_task_order_controls.py` gained a live QML test for the
  Month/Year blocker (hover claimed away from the Active button, click
  doesn't reach it either) and its icon-lookup helper was updated for real
  `Image` icons instead of text glyphs. Deliberately verified this test
  actually fails without the fix (temporarily reverted `orderBlocker` to
  `enabled: false`, confirmed red, restored) before trusting it green.

## [0.38.0] - 2026-09-09

### Changed
- **Task ordering rework (r-7.md)**: no more separate "Manual" button in
  the ordering sub-toolbar — `TaskListModel.statusSortMode`'s existing
  `""`/`"active"`/`"done"`/`"cancelled"` string already meant exactly
  "Manual" for `""`, so only the UI needed to change. FilterBar's
  Active/Done/Cancel sort buttons now toggle (tapping the already-active
  one clears back to `""`, i.e. Manual — same pattern already used by the
  Yatas Active/Deleted group) instead of always selecting their own value
  on tap; they're disabled (not hidden) during Month/Year, which have no
  per-task order for this to apply to.
- `TaskDelegate.qml`'s old "⋮⋮" drag-handle glyph is replaced by explicit
  "^"/"v" buttons (each disabled at its end of the list) — moving a task
  either way, or by dragging (still works from anywhere on the row, now
  including while a status sort is active), switches ordering back to
  Manual. New `TaskListModel.moveTaskUp`/`moveTaskDown` methods (a shared
  `_move_by_one`, deliberately not reusing `moveTask`'s "insert after
  target" convention tuned for drag&drop's drop-below-row placeholder,
  since up/down always means "exactly one visible position" — reusing it
  as-is is off-by-one for the "up" direction specifically, confirmed while
  implementing this) and a shared `_switch_to_manual_if_needed()` used by
  both the new methods and `moveTask`. `canReorder` no longer factors in
  `statusSortMode` (only an active search still blocks reordering) — an
  active sort no longer blocks a manual move, it's switched off by it.
- `README.md`'s reordering/sort-order bullets updated to match.

### Testing
- 12 new `tests/test_models.py` cases (moveTaskUp/moveTaskDown swap
  behavior, boundary no-ops, day-group reassignment, status-sort reset on
  an actual move vs. a same-index no-op drop, and `canReorder` no longer
  tied to an active sort) plus a new `tests/test_task_order_controls.py`
  running a real offscreen QML engine (same construction pattern as
  test_lock_feature.py/test_close_window_button.py) confirming the "^"/"v"
  buttons and the FilterBar toggle wiring actually work against the
  compiled QML, not just the Python model. That integration test
  deliberately does NOT chain a real synthetic FilterBar click into a real
  synthetic row-button click in the same test — doing so during
  development reproducibly hit an offscreen-QPA event-timing artifact
  (confirmed independent of this feature's own logic via direct signal-
  tracing) where the second click's TapHandler silently never fired;
  the combinatorial "resets to manual" behavior is instead covered
  directly and reliably at the Python level.

## [0.37.8] - 2026-09-08

### Changed
- `README.md` promo images: switched from fixed pixel `width`/`height` to
  percentage `width` only (`background_dark.png` 17%, `demo.gif` 76%,
  summing to 93% so they can never exceed the container). This ends the
  0.37.3-0.37.7 back-and-forth of guessing a fixed pixel size that fits
  GitHub's actual (apparently narrower-than-assumed, and never directly
  observable from here) content column: percentage widths mathematically
  cannot wrap regardless of that column's real size, and the 17:76 ratio
  matches each image's real aspect ratio closely enough that both render
  at close to the same height as each other. Trade-off: the actual
  on-screen height now scales with the reader's browser width instead of
  being a fixed pixel value.

## [0.37.7] - 2026-09-08

### Fixed
- `README.md` promo images: reverted the 0.37.6 size-up (380px height,
  ~847px combined width) — confirmed on the actual rendered GitHub page to
  wrap onto two lines, same as the original 480px-height attempt (0.37.3,
  ~1070px). Back to the 280px-height size (112x280 / 512x280, ~624px
  combined) confirmed working in 0.37.4/0.37.5 — the real safe width
  ceiling sits somewhere between 624px and 847px, narrower than assumed.

## [0.37.6] - 2026-09-08

### Fixed
- `README.md` promo images were sized too small (280px height, ~624px
  combined width) relative to GitHub's actual README content column
  (roughly 1000-1050px), leaving large empty margins on both sides under
  `<p align="center">`. The earlier 480px-height attempt (0.37.3, ~1070px
  combined) had wrapped onto two lines because it slightly exceeded that
  same column width — so 1000-1050px is the real ceiling to stay under, not
  a narrow-viewer-only concern. Sized up to 380px height, comfortably
  under it: `background_dark.png` is now 152x380, `demo.gif` is now
  695x380 (combined ~847px).

## [0.37.5] - 2026-09-08

### Fixed
- `README.md` audit for content that had gone stale relative to the actual
  app (nothing here touches code, docs only):
  - **Features section** was missing several shipped features entirely:
    the independent Active/Done/Cancelled visibility filter (separate from
    status-sort), the hold-to-note feature on done/cancel icons (r-6.md),
    the glass-lock feature (r-8.md, Unlocked/Auto-locked/Locked), each
    window's own close ("✕") button, and per-window custom border/glow
    color (r-4.md). Also merged two near-duplicate "drag and drop to
    reorder" bullets into one, and fixed the "toolbar captions" bullet,
    which cited `DAY`/`STATUS` as toolbar captions when they're actually
    filter-bar captions (and didn't mention `LINKS`/`YATAS`, which are).
  - **Quick start**: `./run.sh` no longer says the startup splash is
    "not... wired into this yet" — it's been wired in since 0.7.0-era
    work; corrected to describe the actual current behavior and mention
    `run-yata.sh` as the no-splash alternative.
  - **AI-assisted development**: was pinned to a specific, now-outdated
    model (`claude-sonnet-4-6`) despite ongoing work happening under newer
    ones since — generalized to "Claude, Anthropic's AI model" so it
    doesn't need editing every time the model changes.
  - Checked all attribution/copyright content (Noun Project icon credits,
    VT323 font license, ChatGPT-generated-artwork notice, `LICENSE`
    copyright holder/year) against `resources/assets/` and found no gaps
    or mismatches — no changes needed there.

## [0.37.4] - 2026-09-08

### Fixed
- `README.md` promo images were stacking one above the other instead of
  staying side-by-side: at height 480, `demo.gif`'s wide 640x350 aspect
  ratio alone needs ~878px of width, and combined with
  `background_dark.png`'s ~192px that's ~1070px total — wider than most
  README content columns (GitHub's included), so the second image wrapped
  onto its own line regardless of the table-vs-`<p>` question fixed in
  0.37.3. Shrunk the fixed height from 480 to 280 (a size both images
  comfortably fit within a single row at): `background_dark.png` is now
  112x280, `demo.gif` is now 512x280 (combined ~624px).

## [0.37.3] - 2026-09-08

### Fixed
- `README.md` promo images: the `<table>` wrapper around
  `background_dark.png`/`demo.gif` is gone — GitHub's own CSS forces
  visible `<table>`/`<td>` borders regardless of a `border="0"` attribute,
  so removing the table was the only reliable fix. Replaced with two plain
  `<img>` tags in a `<p align="center">`. Also gave both images an
  explicit `width` *and* `height` (not height alone): several renderers
  (VS Code's Markdown preview included) apply an `img { height: auto }`
  rule that silently overrides a lone `height` attribute and re-derives it
  from width instead, which was why `background_dark.png` (a tall 372x929
  portrait image) was rendering at roughly 2x the height of `demo.gif`
  (a wide 640x350 image) even though both had `height="480"`. Widths were
  back-computed per image from its real aspect ratio at height 480:
  `background_dark.png` → 192x480, `demo.gif` → 878x480.

## [0.37.2] - 2026-09-08

### Changed
- `README.md`: replaced the 6-screenshot gallery table with a 2-up
  `docs/promo/background_dark.png` (the dark-theme loader splash) +
  `docs/promo/demo.gif` layout, both `<img>`s height-capped at 480px with
  no explicit width so aspect ratio is preserved. Copied
  `resources/loader-assets/background_dark.png` into the new
  `docs/promo/` directory (alongside the already-placed `demo.gif`) rather
  than referencing the resources copy in place, keeping promo assets
  together.

## [0.37.1] - 2026-09-08

### Changed
- `scripts/mock-env-init.sh` now also snapshots every window's *settings*
  file (`yata.conf` / `instances/<id>.conf` — position, size, theme, tint,
  border color, opacity, font scale) before doing anything, alongside the
  existing tasks.json backup. The script itself still never edits these
  files, but restoring now puts back whatever they looked like before —
  so freely repositioning/recoloring/zooming windows for a screenshot,
  then running the script again and choosing restore, reverts that too,
  not just the mock task data.

## [0.37.0] - 2026-09-08

### Added
- `scripts/mock-env-init.sh`: swaps the real `~/.local/share/yata` task data
  for `tests/fixtures/mock_tasks.json` in place, for taking manual/
  interactive README screenshots of the real, already-configured app
  (window positions/sizes/themes/tags untouched — only each window's
  `tasks.json` content is replaced). Unlike `scripts/capture_screenshots.py`
  (fully isolated throwaway `XDG_DATA_HOME`/`XDG_CONFIG_HOME`, never touches
  real files), this one mutates real files on purpose, so it backs up every
  `tasks.json` it's about to overwrite (including "didn't exist yet") under
  `.mock-backup/` before touching anything, and refuses to guess if that
  backup is already present from an earlier run — it asks whether to
  refresh the mock data again or restore the real data instead. Deleted
  windows (`windows.json` `deleted: true` entries) are left alone.

## [0.36.0] - 2026-09-08

### Added
- **`x-loader` logo animation, visual PoC**: a small bright flare now orbits
  the logo's ring while the splash holds fully visible, restoring the
  original design intent ("the ring stays put while only a highlight
  travels around it") that got dropped when the loader went through its
  PySide6 → C++/Qt6 → pure-X11 rewrites chasing startup latency instead.
  New `x-loader/spinner.h`/`spinner.c`: `spinner_render(sp, pixels, width,
  height, rshift, gshift, bshift, t)` takes a loop progress `t` in
  `[0.0, 1.0)` (0.0 and the limit as t→1.0 are visually identical, so it
  loops with no seam) and alpha-blends the flare directly into the
  already-fade-blended pixel buffer — only the small area around the
  flare's current position is touched, the rest of the static background
  picture is left untouched. Deliberately not a generic reusable spinner:
  ring center/orbit radius are hardcoded to this exact artwork's geometry,
  with only the flare's own color varying per theme.
- `effects.c` wires it in: `fade_set_spinner()` attaches one to a
  `FadeEffect`, `fade_render()` draws it every frame on top of the fade's
  own blend using its own independent 2-second-per-lap clock. New
  `fade_needs_frequent_wakeups()` (deliberately kept separate from
  `fade_is_animating()`, so the existing socket-mode 2-minute-deadline
  check isn't affected by whether a spinner happens to be attached) tells
  `main.c`'s `select()` loop to keep waking every 16ms while holding fully
  visible with a spinner attached, instead of blocking indefinitely — the
  hold is when the flare is actually seen, so it can't be allowed to
  freeze there.
- Flare geometry/color constants (`RING_CENTER_X_FRAC`,
  `RING_CENTER_Y_FRAC`, `FLARE_RADIUS_FRAC`, and the per-theme `flareR/G/B`
  values in `spinner_create()`) were hand-tuned live against the real
  artwork after this landed, by the user directly, not re-verified here —
  see spinner.c's own current values.
- **Scope note**: the feature work itself touched only `x-loader/`
  (`spinner.h`/`.c`, `effects.h`/`.c`, `main.c`, `Makefile`) per explicit
  instruction to work only on the loader; not run/screenshotted here
  either, per explicit instruction that visual verification would be done
  by hand via `run-loader.sh`. `yata-src/main.py`'s `APP_VERSION` was
  bumped to `0.36.0` to match afterward, on request, once this entry's
  version bump was already in place — `build.sh`'s own version-consistency
  check now passes again.

## [0.35.0] - 2026-09-08

### Changed
- **The packaged build is now a genuine single file** — direct follow-up
  to 0.34.0's two-file layout ("would it be possible to put it into single
  binary? simply for the user convenience"). `x-loader` now ships *inside*
  `dist/yata-X.Y.Z` itself instead of alongside it as a `-loader` sibling:
  - `build.sh` passes it to Nuitka as an onefile data file
    (`--include-data-files=.../x-loader/x-loader=x-loader-loader`),
    injected into the `[nuitka] extra_args` of a `pysidedeploy.spec`
    generated via `pyside6-deploy --init` specifically to get a chance to
    add that flag before the real compile runs (a plain `pyside6-deploy -f
    --name ...` with no spec file, as before, auto-generates and discards
    one with no such opportunity).
  - At startup, `yata-src/main.py`'s `_maybe_launch_bundled_loader()` finds
    the self-extracted copy via `__nuitka_binary_dir` — a name Nuitka
    injects into `builtins` (not a module global) pointing at the onefile
    bootstrap's private per-run extraction directory, confirmed directly
    against Nuitka's own runtime source (`CompiledCodeHelpers.c` seeds it
    for standalone/onefile EXE mode) and empirically verified live with a
    minimal onefile probe binary before wiring it into the real build.
    Chmods the extracted file executable itself (onefile extraction
    doesn't promise the source file's own exec bit survived) rather than
    relying on it. A no-op, same as before, when not compiled or when
    `YATA_LOADER_SOCKET` is already set externally (`run.sh`'s dev-mode
    orchestration).
  - This supersedes 0.34.0's sibling-file approach (and the earlier,
    briefly-considered-then-rejected idea of embedding it via Qt resources
    instead) — no more second file to keep track of or ship together.
  - `tests/test_desktop_integration.py` updated: the sibling-file tests
    replaced with equivalents that monkeypatch `builtins.__nuitka_binary_dir`
    instead of writing a fake sibling file next to a fake `sys.argv[0]`; a
    new test confirms the extracted file gets chmodded executable even
    when it wasn't already. All 194 tests still pass.
  - **Verified against a real build, not just the probe**: ran `./build.sh`
    to completion (2m49s) and launched the resulting single
    `dist/yata-0.34.0` file (isolated `XDG_*` dirs) — confirmed the
    bundled loader really does self-extract to a Nuitka onefile temp
    directory (`/tmp/onefile_<pid>_<time>_<random>/x-loader-loader`,
    observed directly via `ps`) and launch from there (first seen ~523ms
    in, gone by ~1795ms — a zombie/defunct process still shows up in `ps`
    output after it's actually exited, which produced one misleadingly
    "still there" reading before filtering `ps`'s `stat=` column caught
    it), with the app window and process both still present and running
    afterward. This build predates this entry's own version bump
    (0.34.0 → 0.35.0, done immediately after to record the change) — same
    code, cosmetic version-label difference only, not re-verified a second
    time under the new number since the mechanism doesn't depend on it.

## [0.34.0] - 2026-09-07

### Changed
- **`build.sh` rewritten around a single primary distributable binary**,
  replacing the previous two-binary scheme where the *loader* was the file
  a user ran (looking for an `-app` sibling) — a layout left over from the
  now-removed `loader-src`/`loader-cpp`. Now:
  - `dist/yata-X.Y.Z` — the app itself (`pyside6-deploy`/Nuitka, as
    before). This is the one file to run, and what a desktop entry's
    `Exec=` points at.
  - `dist/yata-X.Y.Z-loader` — `x-loader`, compiled fresh via plain `make`
    (no Nuitka needed for a 10KB-of-code Xlib program). The app binary
    finds and launches this sibling itself at startup (new
    `yata-src/main.py`'s `_maybe_launch_bundled_loader`, detected via
    Nuitka's own `__compiled__` module marker so `uv run` dev mode is
    unaffected) — reusing the exact same socket protocol `run.sh` already
    uses for a source checkout, just self-orchestrated instead of
    shell-scripted. No new IPC code needed, no Nuitka onefile
    data-embedding tricks either — it's the same sibling-file-lookup
    pattern (`sys.argv[0]`-relative) this codebase's `_compute_exec_cmd`
    already used for the old scheme, just with the roles inverted.
  - **Considered and rejected: embedding x-loader's compiled bytes inside
    yata's own Qt resources** for a literal single-file result — x-loader
    already bakes its two background images in as raw RGBA at compile time
    (by design, for zero runtime decoding), making the binary itself
    ~2.8MB; re-embedding that whole blob a second time through
    `pyside6-rcc`'s byte-array encoding would have bloated the tracked
    `resources_rc.py` by several more MB for no real benefit over a plain
    sibling file, which the existing `_ensure_desktop_entry`/`Exec=`
    machinery already handles as "one thing to run."
  - `build.sh` now also **checks `yata-src/main.py`'s `APP_VERSION`
    against `pyproject.toml`'s version** before building, exiting with an
    error on mismatch rather than silently shipping a binary whose
    desktop-entry-resync gate is stale — this exact drift had actually
    happened (`APP_VERSION` was stuck at `"0.9.32"`, last touched long
    before the version scheme settled on `pyproject.toml`'s `X.Y.Z`, while
    `pyproject.toml` had moved on to `0.33.0`); fixed by bumping
    `APP_VERSION` to match here. Also checks `resources/assets/app-icon.png`
    exists and is non-empty before starting the multi-minute build.
  - `_compute_exec_cmd`'s compiled-binary branch simplified to match: no
    more "-app" suffix stripping / sibling-swap logic, since the packaged
    binary now points `Exec=` at itself and handles launching its own
    splash sibling internally.
- **Verified with a real build**, not just reviewed: ran `./build.sh` to
  completion (2m41s; previous dist/ artifacts on this machine, `yata-0.28.0`
  through `yata-0.30.0`, predate the splash work entirely and only proved
  the plain `pyside6-deploy` pipeline itself, not this new layout).
  Launched the real `dist/yata-0.34.0` binary (isolated `XDG_*` dirs) and
  confirmed, against the real Nuitka onefile output rather than just unit
  tests: the `-loader` sibling actually gets found and launched (first
  seen ~489ms in, gone by ~1724ms — the extra latency vs. dev-mode's ~36ms
  is plausibly onefile self-extraction happening before any Python code,
  including `_maybe_launch_bundled_loader`, can even run), the app window
  is still there and the app still running once the splash exits, and a
  freshly generated `~/.local/share/applications/yata.desktop` has
  `Exec=` pointing directly at the binary itself (no sibling-swap) with
  `X-AppVersion=0.34.0` matching `pyproject.toml`.

## [0.33.0] - 2026-09-07

### Added
- **`x-loader` process-orchestration**: `run.sh` now actually launches the
  splash alongside YATA and wires them together over a private Unix domain
  socket (`YATA_LOADER_SOCKET`, generated fresh per run under
  `$XDG_RUNTIME_DIR` — falls back to `/tmp` if unset), replacing the
  keypress/click-driven dismissal that was the only way to close it until
  now. Protocol is two tiny newline-delimited messages, x-loader as the
  server and YATA (`yata-src/main.py`'s new `_connect_to_loader`/
  `_send_loader_message`) as the client:
  1. YATA connects (retrying for up to ~1s in case it wins the race against
     the loader's own socket bind, which happens as early in `main()` as
     possible specifically to make that unlikely) and sends `starting` —
     currently just a handshake with no effect on the loader's state
     machine, a hook for later (e.g. resetting the timeout, showing
     progress text).
  2. Once every window this launch opens has actually been shown (same
     `app.processEvents()` idiom the old `YATA_LOADER_PID`/`SIGUSR1`
     mechanism used, now removed as fully obsolete), YATA sends `running`
     and closes its end.
  3. The loader (`x-loader/main.c`'s new socket-mode branch, alongside its
     existing X connection in the same non-blocking `select()` loop) fades
     out and exits the instant it sees `running`; after 2 minutes with no
     `running` (`LOADER_TIMEOUT_MS`); or immediately if YATA's end closes
     without ever sending it (e.g. a crash) — all three funnel into the
     same `fade_start_out()` call. A `running` that arrives mid fade-in is
     honored as soon as the fade-in itself finishes, rather than causing a
     visible pop.
  4. Socket-driven runs skip the standalone preview's "hold fully hidden
     until a second click" step entirely (`effects.c`'s new
     `fade_set_auto_close`) — once faded out there's no user left to click,
     so it just exits.
  - `run.sh --backup`/`-b` and `-h`/`--help` skip the splash entirely
    (`main.py` returns before opening any window for either), rather than
    leaving it on screen for up to 2 minutes waiting for a `running` that's
    never coming.
  - `run-loader.sh` (standalone preview, no socket) is unaffected — same
    click-to-dismiss behavior as before.
  - `build.sh` (packaging) remains broken, still referencing the removed
    `loader-src/` — unrelated follow-up, not touched here.

## [0.32.0] - 2026-09-07

### Added
- **New application logo** (`resources/assets/app-icon.png`, ChatGPT-generated,
  steered/iterated on by the author) — replaces the previous icon everywhere
  it was used (window icon, desktop entry, hicolor icon cache). `APP_VERSION`
  bumped so existing installations' desktop entry/icon cache actually
  refresh on next launch (`_ensure_desktop_entry`'s own version check).
- **Startup loader/splash, in progress — now a pure-X11 preview (`x-loader/`)**:
  a small, independent program meant to be shown while the real YATA app
  loads, most useful for masking the packaged single-file binary's slower
  startup. Went through three implementations before landing here:
  1. A PySide6 prototype (fade in/out, an orbiting highlight on the logo's
     ring, a `YATA_LOADER_PID`+`SIGUSR1` readiness protocol so it only
     fades out once YATA has actually shown every window it's going to
     open, sibling-`-app`-binary auto-detection for the packaged case) —
     worked, but Python interpreter + Qt-for-Python's own init cost turned
     out to be big enough to defeat the entire point of a splash meant to
     mask slow startup: reported live at ~9s with no fade-in visible at
     all, then ~30s+ even after removing a `QtQuick.Effects` `MultiEffect`
     glow that was the first suspect.
  2. A from-scratch rewrite in C++ against a real Qt6 install (CMake,
     same design/protocol, POSIX signals via the standard Qt
     self-pipe→`QSocketNotifier` bridge) — ruled out "Python" as the cause,
     but not Qt itself: still measured 26-53s before a window even
     appeared, including from an `-O3`+LTO Release build with link-time
     optimization on, which ruled out "unoptimized code" too.
  3. **`x-loader/`**: plain C against only Xlib/Xinerama, no Qt/Python/UI
     toolkit at all, and no image-decoding library either — the two
     background PNGs (`resources/loader-assets/`, used verbatim from the
     design mockup: logo, wordmark, "Loading...", and the "SMALL STEPS. BIG
     PROGRESS." tagline are all part of that artwork already) are
     pre-decoded to raw RGBA and embedded as plain C byte arrays at build
     time (`x-loader/generate_assets.sh`, `xxd -i`), so the running program
     never parses/decodes anything — just opens the display and blits
     pixels. Measured live: ~19ms from process start to the window actually
     appearing on screen (X11 window-mapped wall clock), confirming Qt's
     own init was the real cost all along, not this app's code, its
     language, or its optimization level.
  - Matches the desktop's own light/dark preference by default (same
    `gsettings get org.gnome.desktop.interface color-scheme` check all
    three implementations used), `--light`/`--dark` force one regardless.
    Run via `./run-loader.sh` (builds via `make` if needed).
  - **Fade in/out, real transparency** (`x-loader/effects.h`/`effects.c`):
    fades in over 250ms, holds fully visible until a keypress/mouse click,
    fades out over 250ms, holds fully hidden until a second
    keypress/mouse click, and only then actually exits. Input during
    either active fade is ignored — only the two static "holding" states
    react to it — which also incidentally fixes a real bug reported live:
    launching from a shell (`./x-loader --light`, Enter to run it) could
    dismiss the splash immediately, the Enter keystroke landing on the
    window right as it was mapped, mid fade-in.
    Uses a real 32-bit ARGB visual (`XMatchVisualInfo`) with premultiplied
    per-pixel alpha, so a compositor genuinely blends the fade against
    whatever is actually behind the window — confirmed live by screenshotting
    the root window (not the splash window itself, which only ever holds
    its own uncomposited pixels) mid-fade and seeing real desktop content
    show through. Falls back to blending toward the image's own top-left
    pixel color if no ARGB visual is found (no compositor, or a minimal X
    setup without one). Repacking ~346,000 pixels/frame this way still
    measures well under 1ms, so no SIMD or external library was needed to
    hit 60fps. Driven by a non-blocking main loop (`select()` on the X
    connection, timed while animating, blocking indefinitely while
    holding) rather than blocking in `XNextEvent`, so the animation can
    advance between events instead of waiting on user input to make
    progress.
  - **Not yet feature-complete**: no process-orchestration (launching YATA
    and waiting for a real readiness signal to trigger the fade-out,
    instead of waiting for a keypress/click) — that's still the plan, just
    not built yet. `run.sh` is accordingly just `run-yata.sh` for now (no
    splash in the real launch flow), and `build.sh` (packaging) still
    references the removed `loader-src/` and is left broken pending this
    follow-up work — both deliberate, not oversights. No automated tests
    yet either (the two Qt prototypes each had one — PySide6's via pytest,
    the C++ one's verified manually — but `x-loader/` hasn't gotten there
    yet).

## [0.31.2] - 2026-09-06

### Fixed
- **The glass lock's frost/blur bled upward past the top border** into the
  tag-label/border area while locked or auto-locked — user feedback: "the
  upper part goes over the border. Make it end at border." Root cause:
  `frostedContent` (the layered `Item` that gets blurred) spanned the *full*
  window content area with no inset, while the visible border line sits
  `tagLabelBg.height / 2` further down (same as the wash `Rectangle`
  underneath it and `windowBorder`'s own inset) — and `MultiEffect`'s
  `autoPaddingEnabled: true` deliberately lets the blur spread beyond an
  item's own bounds for quality, spilling it into that gap above the border.
  Fixed by inset-ing `frostedContent` itself by the same `tagLabelBg.height /
  2` margin (removing the now-redundant duplicate margin from the wash
  `Rectangle` inside it) and adding `clip: true`, so the blurred/padded
  render is hard-clipped exactly at the border line instead of fading past
  it.

## [0.31.1] - 2026-09-06

### Changed
- **Lock and close icons now have a hover-on/hover-off effect**, so they
  read as action items rather than static pictures: on hover, each icon's
  background box brightens slightly and gets a glow (the same shadow-glow
  recipe used for every other hoverable icon in this app, e.g. YatasRow's
  show/color buttons), fading back on hover-off. The glow targets the BOX's
  own rounded-rect shape rather than the icon glyph inside it — deliberately,
  since the lock icon swaps between 3 differently-shaped SVGs
  (locked/auto-locked/unlocked, outline vs filled) and glowing each one's own
  silhouette would look inconsistent between them; the box shape never
  changes, so the effect looks identical regardless of which icon is
  currently showing.

## [0.31.0] - 2026-09-06

### Added
- **Classic "✕" close-window button**, next to the lock icon on the top
  border ("Order of the icons on the right side is now: LOCK CLOSE"). Sits
  in the outermost/rightmost position, on the same solid background box
  style as the lock icon (and the tag label), with a small transparent gap
  (`root.lockCloseIconGap`, scales with font zoom) between the two boxes so
  they read as two separate controls rather than one merged one. Clicking it
  calls `WindowManager.closeWindow(windowId)` — the same method YatasView's
  own SHOW toggle already uses — so it's a no-op on the last remaining open
  window (the existing "at least one window must stay visible" guard,
  inherited for free rather than reimplemented), and otherwise hides the
  window without touching its tasks/settings, reopenable later from YATAS.
  New `tests/test_close_window_button.py` (2 tests, a real two-window setup
  confirming both the close and the no-op-on-last-window cases).

## [0.30.0] - 2026-09-04

### Added
- **Task row hover background now follows this window's custom color**
  (r-4.md, assigned via the YATAS list) instead of a generic grey, for the
  "none" tint — a subtle tinted wash (10% alpha) rather than the flat
  grey/white `Theme.hoverColor` overlay used everywhere else. Falls back to
  the original grey when no custom color is assigned (there's no "window
  color" to use otherwise), and CRT/terminal tints are untouched by explicit
  request — each already tints its own hover color to its own phosphor
  color. New `TaskDelegate.rowHoverColor`/`effectiveBorderColor` properties;
  the alpha (10%) was picked by comparing live screenshots of a saturated
  color (red) and a calmer one (blue) at 18%/12%/10% — 18% read as a fairly
  vivid solid-pink band for red, 10% stayed clearly recognizable without
  looking like a flat color block for either. New
  `tests/test_task_row_hover_color.py`.

## [0.29.4] - 2026-09-04

### Fixed
- **A "locked" (not auto-locked) window still reacted to hover** — row
  highlighting and hover-revealed action icons in the task list/LinksView/
  YatasView still responded to the mouse, immediately after 0.29.3 fixed
  hover being broken everywhere. Clicking was already correctly blocked;
  only the hover reaction was wrong. Fixed by making `contentBlocker` (the
  `MouseArea` that already blocks clicks while locked) also `hoverEnabled`
  while enabled, so it claims hover away from the rows underneath exactly
  like it already claims clicks — but scoped specifically to plain
  `"locked"`, not `"auto-locked"`: auto-locked's own `enabled`-ness (while
  not yet hovering) depends on `contentHoverHandler` — nested underneath
  `contentBlocker` in the z-stack — detecting the mouse's arrival, so
  claiming hover there too created a deadlock (confirmed live: auto-locked
  got stuck locked forever, since the very hover that should disable the
  blocker could never reach the handler that would notice it). New
  regression tests `test_task_row_hover_suppressed_while_locked` and
  `test_auto_locked_hover_unlock_not_deadlocked_by_hover_blocking` in
  `tests/test_lock_feature.py` cover both the fix and the deadlock it must
  not reintroduce.

## [0.29.3] - 2026-09-04

### Fixed
- **The glass lock silently broke hover everywhere in the content area** —
  task row highlighting/hover-action-icons, and the same row-hover mechanism
  in LinksView/YatasView, stopped reacting to the mouse while unlocked or
  auto-locked (auto-locked's own hover-to-unlock still worked, so the window
  correctly unblurred, but nothing *inside* it responded to hover anymore).
  Root cause: `contentHoverHandler` (added to detect "mouse is inside the
  content area" for auto-locked) lived in a sibling `Item` stacked on top of
  `contentColumn`. Confirmed via a minimal reproduction: an `Item` with an
  enabled `HoverHandler` placed above another item in the same z-stack —
  even with no `MouseArea`/grab at all — exclusively claims hover and blocks
  it from ever reaching anything underneath, contradicting `HoverHandler`'s
  own "non-exclusive, siblings can all respond" documentation (that
  non-exclusivity turned out to only apply to multiple handlers on the *same*
  item, not separate items competing in a z-stack). Fixed by nesting
  `contentHoverHandler` as a child *inside* `contentColumn` instead of a
  sibling overlay above it — a second minimal reproduction confirmed a
  HoverHandler nested as a parent of items that have their own HoverHandlers
  lets every one of them update independently and correctly, unlike sibling
  stacking. `contentBlocker` (the actual click-blocking `MouseArea`) stays
  exactly where it was — it never had a hover component, so it was never
  part of this bug.
  New regression test `test_task_row_hover_still_works_while_unlocked` in
  `tests/test_lock_feature.py`.

## [0.29.2] - 2026-09-04

### Changed
- **Glass lock polish**, three explicit follow-up requests:
  1. The lock icon now sits on its own solid background box (same
     color/radius as the window tag label's box) instead of directly on the
     border line — previously `windowBorder`'s stroke ran straight through
     the icon, making it hard to see, especially when the border color was
     close to the icon's own color.
  2. Blur/unblur transition shortened from 1 second to 250ms.
  3. The frosted-glass tint now uses `Theme.effectiveGlowColor` (this
     window's effective accent color — a CRT/terminal tint's own phosphor
     color, this window's custom border color if set, or the theme's default
     accent) instead of a fixed white, so it reads as "this window's own
     tint, frosted" rather than a generic haze.

### Fixed
- **The glass lock's blur was too weak and too narrow.** User feedback after
  0.29.0: task text was still readable through the blur, and the plain
  background rectangle behind the toolbar/list stayed crisp since only the
  toolbar+list column itself had the effect — "I expected everything will be
  blurred (together with background)". Fixed by wrapping the background wash
  *and* the toolbar/list in a single layered `Item` (`frostedContent`) so one
  `MultiEffect` blur pass covers the whole panel, raised `blurMax` from `5` to
  `48` (confirmed live: `5` left text fully legible, `48` reads as genuine
  illegible smudges), and added a translucent white scrim on top (fading in
  with the same 1-second `blurAmount` transition) for a "frosted glass" haze
  rather than a plain blurred screenshot look. This is a live GPU-rendered
  layer, not a snapshot, so it can't go stale or reveal anything crisp while
  the window is moved or resized — confirmed live across several simulated
  window moves while locked.
  User also asked whether Qt/the OS could blur the *real desktop* behind the
  window (true compositor "backdrop blur", updating as the window moves) —
  answered directly rather than attempting it: neither Qt nor GNOME/Mutter
  (this app's target compositor) support that for a normal window without a
  shell extension outside the app's control, and it wouldn't actually serve
  the "prevent reading task text" goal anyway (it would show the real
  desktop, not obscure the task list). Went with the frosted-own-content
  approach above instead.
  Along the way, fixed a real bug introduced during this rework: the
  auto-locked hover/re-lock boundary (`contentOverlay`) was first widened to
  match the new full-panel blur target, which made the *entire window* count
  as "hovering content" (nothing was left "inside the window but not
  hovering"), making auto-locked impossible to ever leave unlocked-until-you-
  hover — reverted to the narrower `contentColumn` bounds (matching the
  actual interactive area) while the blur itself stays scoped to the wider
  panel; these are two independent concerns. Positioning `contentOverlay`
  against the now-nested `contentColumn` also surfaced two QML gotchas along
  the way: `anchors.fill: contentColumn` throws at runtime once `contentColumn`
  is no longer a direct sibling ("Cannot anchor to an item that isn't a parent
  or sibling"), and the `mapToItem()`-based x/y fallback tried next silently
  froze at a stale `(0, 0)` because a native method's return value isn't
  tracked as a live QML binding dependency the way a plain property read is —
  settled on reading `contentColumn.x`/`.y` directly instead, valid here
  specifically because `frostedContent` sits at `(0, 0)` with no margin
  relative to the same parent.

## [0.29.0] - 2026-09-04

### Added
- **"The glass lock" (r-8.md)**: a small lock icon on the top border (mirrors
  the window tag label's own margin, but on the right) cycles a per-window,
  persisted 3-state privacy lock — click to advance unlocked → auto-locked →
  locked → back to unlocked. Each state has its own icon (ChatGPT-generated
  SVGs in `resources/assets/lock_*.svg`, recolored to match the window
  border like every other toolbar icon):
  - **unlocked**: normal, no restrictions.
  - **locked**: content (toolbar, filter bar, task list — and the
    right-click theme menu) permanently blurred and completely unresponsive
    to the mouse. Only the lock icon itself stays live, so a locked window
    can always be unlocked again.
  - **auto-locked**: same as locked by default, but automatically and
    temporarily unlocks (unblurs, becomes fully interactive) while the mouse
    is actually inside the content area, or while another window's task drag
    is hovering over it — reverting the instant the mouse leaves. Actively
    typing a task's description keeps it unlocked regardless of mouse
    position (checked live via `Window.activeFocusItem`, not a snapshot), so
    finishing an edit while the mouse happens to be elsewhere doesn't yank
    the content away mid-thought.
  - Blur/unblur animates over 1 second (`MultiEffect`'s `blur`/`blurMax: 5`
    on the toolbar+list, driven by a `Behavior`-animated property), rather
    than snapping instantly.
  - New `AppSettings.lockState` (`settings.py`), persisted per window under
    `theme/lockState` alongside the rest of a window's settings, same
    `sync()`-on-every-change guarantee as every other setting here.
  - New `tests/test_lock_feature.py`: a real (offscreen) QML engine +
    `QTest.mouseClick`/`mouseMove` integration suite covering the icon's
    click-cycle, toolbar/menu blocking, hover-based auto-unlock/relock, the
    cross-window drag-hover override, and the task-editing exception — not
    just the Python-side persistence (already covered in
    `tests/test_settings.py`'s new `lockState` tests).

## [0.28.2] - 2026-09-03

### Fixed
- **Window position/size could come back wrong after a GNOME "Shutdown" and
  login (but not after a plain app restart within the same session).** Root
  cause: `monitor_signature()` joined screens in whatever order
  `QGuiApplication.screens()` happened to return them, and that order isn't
  guaranteed stable across a full session restart — the same physical
  monitors can enumerate differently depending on output-detection timing at
  login, even though the layout hasn't actually changed (confirmed directly:
  two orderings of the identical monitor set produced two different
  signature strings). `_load_geometry()` treated any signature mismatch as
  "monitor layout changed" and discarded the saved geometry for
  `first_run_geometry()`'s small centered box — and since `_save_geometry()`
  always rewrites x/y/width/height together, the very next unrelated
  geometry nudge (e.g. `Main.qml`'s `ensureMinimumWidth()`, which runs on
  every startup) would bake that wrong box in permanently, overwriting the
  real saved position for good. Every restored window computes the same
  signature, so this could misplace all of them onto the same spot at once.
  Fixed two ways: `monitor_signature()` now sorts its per-screen entries so
  pure reordering no longer counts as a layout change, and a genuine
  mismatch now clamps the saved geometry into whatever screen space is
  currently available (new `_clamp_geometry_to_virtual_desktop`) instead of
  discarding it for the unrelated default — so a window keeps its saved
  position/size whenever it still fits, and only shrinks/moves the minimum
  needed amount when it doesn't.

## [0.28.1] - 2026-08-25

### Added
- **`-h` / `--help`**: prints the list of command-line options (now just
  `-b`/`--backup`) and exits, without starting the app — argparse's
  built-in help action, previously suppressed via `add_help=False`.

## [0.28.0] - 2026-08-25

### Added
- **`--backup` / `-b` command-line flag**: instead of starting the app,
  zips YATA's whole config and data directories (every window's
  settings/tasks, not just the default window's) into a timestamped
  `yb-<date>-<time>.zip` in the current directory. Colliding filenames
  (e.g. running it twice in the same minute) get a `-1`, `-2`, ...
  suffix rather than being overwritten.

## [0.27.1] - 2026-08-10

### Changed
- Status-line icon spacing (note/reopen icons in `TaskDelegate.qml`)
  hand-tuned by the user: added a reusable `Theme.nonActiveActionIconGap`
  constant (`ThemeImpl.qml`) for the small gap after each icon, and a
  dedicated spacer `Item` between the timestamp and the note icon instead
  of padding the timestamp text itself. Icon wrappers are now vertically
  centered against their own height (matched to `completedStatus`'s
  implicit height) rather than anchored to `completedStatus`'s own
  `verticalCenter`.

## [0.27.0] - 2026-08-10

### Changed
- **Reopen (↺) button moved** from the task row's hover-action buttons to
  the status line, right of the note icon, for `DONE`/`CANCELED` tasks —
  always visible there (like the note icon), not just on row hover.
- **Task row hover-buttons for `DONE`/`CANCELED` tasks now show only
  DELETE** — the ✓/✕ (mark done/cancelled) icons are hidden for
  non-active tasks, since they no longer make sense once a task is
  already closed. Active tasks keep ✓/✕/🗑 as before.

## [0.26.6] - 2026-08-10

### Changed
- Status-line note icon (`TaskDelegate.qml`) hand-tuned by the user: made
  larger (full `taskFontPixelSize` instead of `* 0.75`) and nudged to a
  visually correct position.
- Widened the gap between the status word and the timestamp (status
  label's trailing padding now measures 5 spaces instead of 1).

## [0.26.5] - 2026-08-10

### Changed
- **Status-line `DONE`/`CANCELED` label now has a fixed width** (sized to
  fit the longer of the two words), so the timestamp that follows lines
  up at the same horizontal position across rows regardless of status.
- **Removed the `[` `]` brackets around the completion timestamp** —
  it now reads as a plain `dd-mm-yyyy HH:MM`.

## [0.26.4] - 2026-08-10

### Changed
- **The status-line note icon (`TaskDelegate.qml`) is now always visible**
  on completed/cancelled tasks, not just once a note has been added —
  clicking it now opens the note editor to add a first note, not only to
  view/edit an existing one.
- **Layout reordered** to `STATUS [TIMESTAMP]  NOTE_BUTTON` (was `STATUS
  NOTE_BUTTON [TIMESTAMP]`) — the icon now comes last, with a bigger gap
  before it than the status→timestamp gap, per explicit request.
- **Vertical alignment fixed** — the icon read as sitting higher than the
  status/timestamp text even though its own bounding box was centered;
  anchored directly to `completedStatus`'s own `verticalCenter` instead of
  its own wrapper's, sidestepping whatever asymmetry is in the icon
  artwork's bounding box (same lesson as tuning `HoldToNoteButton`'s icon
  earlier this session).

## [0.26.3] - 2026-08-10

### Changed
- **HoldToNoteButton's note icon/ring tuned by hand** — the icon felt too
  "stuffed" inside the ring at its previous size, and the empirical
  horizontal-offset nudge (added to compensate for the icon's own
  asymmetric artwork) wasn't needed once the icon was simply made smaller
  (`boxSize * 0.80`, plain `anchors.centerIn` instead of an offset). Ring
  stroke widened from 2px to 3px to read more clearly at the new size.

## [0.26.2] - 2026-08-09

### Fixed
- **After Cancel in the NOTE dialog, the DONE/CANCEL button needed to be
  pressed twice** — the first press after closing the dialog silently did
  nothing, and only the second responded normally. Root cause: `NoteDialog`
  (a real separate top-level window, modal to the row's own window) can
  steal the pointer grab mid-hold before the real mouse-up ever reaches the
  row's `TapHandler`, permanently stuck-orphaning its internal `pressed`
  state — confirmed via direct property inspection, and confirmed that
  merely disabling/re-enabling the handler (0.26.1's fix for the *visual*
  symptom) does not clear this, since Qt doesn't discard a disabled
  handler's grab bookkeeping. Fixed by wrapping the `TapHandler` in a
  `Loader` and fully destroying and recreating it (not just disabling)
  once the dialog closes, which does yield a genuinely fresh handler with
  no grab history. (A `Loader` has no implicit size of its own, so it also
  needed an explicit `anchors.fill: parent` — otherwise the recreated
  handler silently stopped receiving any events at all, having no real
  hit-test area.)

## [0.26.1] - 2026-08-09

### Fixed
- **HoldToNoteButton's icon wasn't centered in its progress ring** — the
  note icon's own artwork (a paperclip loop above a page stack, tightly
  cropped to its ink) isn't visually symmetric within its bounding box,
  reading as shifted left even when geometrically centered. Nudged right
  empirically until it read as centered live.
- **The ✓/✕/🗑 action icons weren't vertically aligned on the same row** —
  `HoldToNoteButton`'s box size no longer matched a plain `Text` glyph's
  own natural size (was a hardcoded formula), so it sat at a different
  height than `reopenBtn`/`deleteBtn` despite all sharing one top-aligned
  `Row`. Now sized off its own `glyphText`'s `implicitWidth`/
  `implicitHeight` directly, matching a sibling `Text` glyph exactly. This
  also revealed a second bug: `HoldToNoteButton`'s box is no longer
  reliably square (glyphs differ in width), so the note icon's own
  height-based sizing could overflow past the ring's diameter for a
  narrower glyph — fixed by bounding it to a square sized off
  `Math.min(width, height)` instead.
- **The DONE/CANCEL icon stayed stuck on the glowing note icon + full ring
  after pressing Cancel in the NOTE dialog** (task correctly stayed
  unchanged, but the button never reverted). Root cause: the dialog is a
  real separate top-level window that can steal the pointer grab mid-hold,
  so the real mouse-up sometimes never reaches the row's own `TapHandler`
  — its `pressed` property stayed stuck `true` after the dialog closed.
  Fixed by tracking hold state manually (`isHeld`) instead of reading
  `TapHandler.pressed` live: set `false` the instant `onLongPressed` fires
  (before the dialog even opens), so a later stuck/stray `pressed` value
  has nothing left to affect. Confirmed live via direct property
  inspection, not just visually.

## [0.26.0] - 2026-08-09

### Added
- **Task closure notes** (r-6.md): an optional markdown note can now be
  attached when marking a task DONE or CANCELLED, explaining the reason
  for the state change.
  - A normal quick click on the ✓/✕ icon still behaves exactly as before
    (instant status change, no note). Press-and-hold instead swaps the
    icon for a Note icon with a circular progress ring filling around it
    (`HoldToNoteButton.qml`); releasing before the ring fills does
    nothing at all. Holding to completion opens a "NOTE" dialog
    automatically (no release needed) with a markdown textbox and
    OK/CANCEL — OK attaches the note and applies the status change,
    CANCEL applies neither.
  - Completed tasks with a note show a small Note icon (hover-glow, like
    the other task action icons) between the STATE word and the
    timestamp — clicking it opens a mini markdown editor in place of the
    task list (`NoteEditorView.qml`), pre-filled and directly editable,
    with an always-visible OK/CANCEL footer. While it's open, the
    calendar/visibility/order sub-toolbar is disabled; switching to
    LINKS/YATAS and back restores the editor (with any unsaved edits
    intact) instead of the plain task list.
  - New `Task.note` field (`storage.py`), `TaskListModel.setNote`/
    `noteFor` (`models.py`), and the `notes` icon asset (Noun Project,
    attribution added to README).

## [0.25.4] - 2026-08-01

### Fixed
- **0.25.3's YATAS list name color didn't actually update when a color was
  picked** without closing and reopening the list first. Root cause: the
  binding called `windowManager.getBorderColor(windowId)` directly inside a
  QML property expression — a plain method call doesn't register as a
  tracked dependency for QML's binding engine, so it silently never
  re-evaluated after its first read, no matter how many times the
  underlying value actually changed. Fixed by making `borderColor` a real
  property on each row instead, sourced from `windowManager.listWindows()`
  (now includes each window's `borderColor`) via `modelData` — the same
  already-reactive mechanism the tag/open/deleted fields use, which
  correctly update today.

### Testing
- Discovered and fixed a real test-isolation gap while adding coverage for
  this: a new test's bare `AppSettings()` (the same `QSettings("yata",
  "yata")` 2-arg constructor the real app uses) leaked its written
  `borderColor` into an unrelated, later-running test in the same pytest
  process — monkeypatching `XDG_CONFIG_HOME` per-test didn't prevent it.
  Switched to an explicit-path `QSettings(..., IniFormat)`, sidestepping
  env-var-based resolution entirely. Confirmed via repeated full-suite runs
  (including reversed file order) that the leak is gone; the real
  `~/.config/yata`/`~/.local/share/yata` files were never actually at risk
  (confirmed via mtime, unchanged throughout).

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
