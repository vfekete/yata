# YATA - Yet Another Todo Application

A minimal always-on-desktop todo list for GNOME/Ubuntu: a borderless,
transparent, vertical list of one-line tasks that sits on the desktop like a
sticky note.

See `docs/instructions.md` for the full specification.

## Features

- Add, edit, cancel, mark done, re-open and delete tasks
- Task text supports Markdown (bold, italic, ...)
- Drag and drop to reorder tasks (grip icon on hover)
- Group the list by day (with a bigger day-heading font and indented tasks),
  or sort with a chosen status first — status sort also applies within each
  day when both are active
- Non-active tasks show a small check (done) or cross (cancelled) icon in
  front of their text, colored green/red in the plain theme or tint-native
  colors under a CRT tint
- Realtime text search
- Drag and drop to reorder tasks (grip icon on hover) — works in day-grouped
  view too, and dragging a task onto a different day's section reassigns it
  to that day
- Window position/size is remembered per monitor layout; first launch
  centers the window at 20% of the screen width with a 9:16 aspect ratio
- Theming via the "Theme" button (toolbar) or the right-click background
  menu: light/dark mode plus a choice of tints. The default tint, "None", is
  a safe/plain look (Noto Sans font, follows the light/dark toggle). The
  other four (green, goldenrod, white, black) each recreate a specific old
  CRT/terminal display — green phosphor, amber phosphor, paperwhite
  monitor, and teletype paper — with a monospace font and tint-appropriate
  colors for active/done/cancelled tasks, borders, buttons and fields.
  Every tint, including "None", renders the window at 65% opacity
- Toolbar button captions render in capitals (DAY, STATUS, THEME) in every
  theme

## Usage notes

- The window has no title bar; drag it by pressing on empty toolbar space
- Use the toolbar's "Theme" button, or right-click the background, for
  theme options; the background menu also has Quit
- Double-click a task to edit its text
- Right-click a task for the option to delete it permanently

## Quick start

```sh
./run.sh
```

See `BUILD.md` for setup and test instructions.

## Known limitation

On X11, the window stays below other app windows (and above the desktop
icons layer) via a direct `_NET_WM_STATE_BELOW` EWMH request
(`yata-src/x11_stacking.py`), not Qt's `Qt.WindowStaysOnBottomHint` — that
hint maps to `_NET_WM_WINDOW_TYPE_DESKTOP` on GNOME/Mutter, which places the
window below the desktop background layer itself (invisible), rather than
merely beneath other app windows.

On **Wayland** (GNOME's default session), there is no equivalent for
ordinary applications — Wayland compositors don't let regular toolkit
windows request a stacking layer at all, so on Wayland the app behaves like
a normal window instead (visible and usable, but not pinned beneath
others). Revisit if a GNOME-Wayland-compatible way to achieve the intended
layering is found.
