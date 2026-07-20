# Changelog

All notable changes to YATA are documented in this file.

The version scheme is `X.Y.Z`:
- `X` — major changes
- `Y` — minor changes
- `Z` — bugfixes, trivial changes, or changes unrelated to code (e.g. documentation)

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
