import QtQuick
import QtQuick.Effects

// DONE/CANCEL action icon (r-6.md) — a quick click still behaves exactly
// like the plain Text glyph it replaces (instant status change, no note).
// Press-and-hold swaps the glyph for the Note icon with a circular
// progress ring filling around it; holding it to completion opens
// NoteDialog automatically (no release needed) to attach an optional
// markdown note before the status change is applied. Releasing partway
// through a hold does nothing at all — not a fallback to the instant
// action — per explicit request.
//
// Qt's TapHandler.tapped() fires for ANY press+release completed before
// longPressThreshold, regardless of how long that hold actually was — it
// does not by itself distinguish a genuine quick click from a deliberate
// hold released early, so tapped() can't be wired directly to the instant
// action (that would violate "release before the ring fills does
// nothing"). Instead this tracks its own press-start timestamp and only
// treats a release within clickThresholdMs of pressing as a real click;
// anything held longer than that but released before holdDurationMs is a
// silently-aborted hold. longPressThreshold's own onLongPressed still
// fires automatically at the full hold duration, while still pressed,
// exactly matching "once the circle is filled, dialog window appears".
Item {
    id: root
    required property string taskId
    required property string targetStatus  // "done" | "cancelled"
    required property string glyph  // "✓" | "✕"
    required property color idleColor
    required property string note  // pre-fills the dialog if reopened

    readonly property int holdDurationMs: 700
    readonly property int clickThresholdMs: 200
    property real pressStartMs: 0
    // Manually tracked rather than reading the TapHandler's own pressed
    // live — see the Loader below for why that alone isn't reliable once
    // NoteDialog has been involved.
    property bool isHeld: false

    implicitWidth: glyphText.implicitWidth
    implicitHeight: glyphText.implicitHeight

    HoverHandler { id: hh; cursorShape: Qt.PointingHandCursor }
    // Loader-wrapped rather than a plain inline TapHandler: NoteDialog (a
    // real separate top-level Window, modal to this one) can steal the
    // pointer grab mid-hold before the real mouse-up ever reaches this
    // handler — confirmed live via direct property inspection that
    // th.pressed then stays stuck true PERMANENTLY, surviving even
    // `enabled = false` held across the dialog's whole lifetime (Qt
    // doesn't discard a disabled handler's internal grab bookkeeping, it
    // just pauses event delivery to it). The observable symptom: the next
    // real press+release is silently "absorbed" as the phantom
    // true→false transition that never happened, so it does nothing, and
    // only the SECOND press behaves normally. Destroying and recreating
    // the handler via Loader.active toggling — not just disabling it —
    // gives a genuinely fresh QQuickTapHandler with no grab history at
    // all, which `enabled` toggling does not.
    Loader {
        id: tapLoader
        // A bare Loader has no implicit size of its own (PointerHandlers,
        // unlike Items, contribute nothing to implicit size either) — it
        // defaults to 0x0, which silently breaks hit-testing for whatever
        // it loads. Anchored to root's own full bounds so the loaded
        // TapHandler actually covers the same area it would if declared
        // directly inline.
        anchors.fill: parent
        active: true
        sourceComponent: TapHandler {
            id: th
            target: root
            acceptedButtons: Qt.LeftButton
            longPressThreshold: root.holdDurationMs / 1000
            onPressedChanged: {
                if (pressed) {
                    root.pressStartMs = Date.now()
                    root.isHeld = true
                } else {
                    root.isHeld = false
                }
            }
            onTapped: {
                if (Date.now() - root.pressStartMs < root.clickThresholdMs)
                    taskModel.setStatus(root.taskId, root.targetStatus)
                // else: released mid-hold, before the ring filled — nothing happens.
            }
            onLongPressed: {
                root.isHeld = false
                noteDialog.openFor(root.taskId, root.targetStatus, root.note)
            }
        }
    }

    Text {
        id: glyphText
        anchors.centerIn: parent
        visible: !root.isHeld
        text: root.glyph
        color: hh.hovered ? Theme.effectiveGlowColor : root.idleColor
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize * 2
        layer.enabled: hh.hovered
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Theme.effectiveGlowShadowColor
            shadowBlur: 1.0
            shadowHorizontalOffset: 0
            shadowVerticalOffset: 0
            shadowOpacity: 1.0
            shadowScale: 1.05
        }
    }

    Image {
        id: noteGlyph
        anchors.centerIn: parent
        visible: root.isHeld
        // Square box bounded by the SMALLER of width/height, not height
        // alone: root's own box is no longer guaranteed square (its size
        // now matches glyphText's own implicit size, which differs by
        // glyph — "✓" is narrower than it is tall). Sizing off height
        // alone let the icon overflow past the ring's own diameter
        // (Math.min(width,height)-based) for any narrower glyph — caught
        // live, the icon visibly spilled outside the ring on one side.
        // PreserveAspectFit centers the actual artwork within this square
        // automatically, respecting its own aspect ratio with no manual
        // implicitWidth/implicitHeight ratio math needed.
        readonly property int boxSize: Math.round(Math.min(parent.width, parent.height) * 0.7)
        // vfe: Icon inside looked too stuffed, so I shrinked it a little bit
        width: boxSize * 0.80
        height: boxSize * 0.80
        fillMode: Image.PreserveAspectFit
        smooth: true
        source: root.isHeld ? iconProvider.coloredSvgUri("notes", Theme.effectiveGlowColor.toString()) : ""
        layer.enabled: root.isHeld
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Theme.effectiveGlowShadowColor
            shadowBlur: 1.0
            shadowHorizontalOffset: 0
            shadowVerticalOffset: 0
            shadowOpacity: 1.0
            shadowScale: 1.05
        }
    }

    // Circular "waiter" that fills clockwise from the top as the hold
    // progresses toward holdDurationMs — timeHeld is a real Qt property
    // updated at least once per rendered frame while pressed (see
    // TapHandler docs), so binding progress directly to it drives a live
    // ring with no separate Timer/NumberAnimation needed.
    Canvas {
        id: ring
        anchors.fill: parent
        visible: root.isHeld
        // tapLoader.item, not the bare "th" id — th now lives inside
        // tapLoader's sourceComponent (a separate component scope, see
        // its own comment), so it isn't a directly-reachable sibling id
        // from here anymore.
        property real progress: tapLoader.item ? Math.max(0, Math.min(1, tapLoader.item.timeHeld / (root.holdDurationMs / 1000))) : 0
        onProgressChanged: requestPaint()
        onVisibleChanged: if (visible) requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.lineWidth = 3
            ctx.strokeStyle = Theme.effectiveGlowColor
            ctx.beginPath()
            ctx.arc(width / 2, height / 2, Math.min(width, height) / 2 - 2,
                     -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * progress)
            ctx.stroke()
        }
    }

    NoteDialog {
        id: noteDialog
        onVisibleChanged: if (!visible) {
            // The dialog stealing the pointer grab mid-hold doesn't just
            // leave the VISUAL state stuck (isHeld already guards against
            // that above) — Qt's own internal TapHandler grab can be
            // orphaned too: confirmed live via direct property inspection
            // that th.pressed stays stuck true PERMANENTLY afterward,
            // surviving even `enabled = false` held across the dialog's
            // entire lifetime — Qt doesn't discard a disabled handler's
            // grab bookkeeping, it only pauses event delivery. Observable
            // symptom: the next real press+release was silently absorbed
            // as the phantom true→false transition that never fired, so
            // it did nothing at all, and only the SECOND press behaved
            // normally. Toggling tapLoader.active fully destroys and
            // recreates the TapHandler (not just disables it), which
            // guarantees a genuinely fresh handler with no grab history.
            tapLoader.active = false
            tapLoader.active = true
        }
    }
}
