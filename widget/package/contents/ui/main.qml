// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>

// Light & Presence: front end for the plasma-light-and-presence user service
// (io.github.onuralpszr.LightAndPresence on the session bus).
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PC3
import org.kde.plasma.extras as PlasmaExtras
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCMUtils
import org.kde.plasma.workspace.dbus as DBus

PlasmoidItem {
    id: root

    readonly property string service: "io.github.onuralpszr.LightAndPresence"
    readonly property string objectPath: "/io/github/onuralpszr/LightAndPresence"
    // Shipped inside the widget package, so they do not depend on the icon theme
    readonly property url iconOn: Qt.resolvedUrl("../icons/io.github.onuralpszr.lightandpresence-symbolic.svg")
    readonly property url iconOff: Qt.resolvedUrl("../icons/io.github.onuralpszr.lightandpresence-off-symbolic.svg")
    readonly property url iconColor: Qt.resolvedUrl("../icons/io.github.onuralpszr.lightandpresence.svg")

    // --- service state ---------------------------------------------------
    // The watcher only reports registration events; a service that was
    // already running when the widget loaded never triggers one. Ask the bus.
    DBus.DBusServiceWatcher {
        id: watcher
        busType: DBus.BusType.Session
        watchedService: root.service
        onRegisteredChanged: root.checkRunning()
    }

    Timer {
        interval: 5000
        repeat: true
        running: true
        triggeredOnStart: true
        onTriggered: root.checkRunning()
    }

    Timer {
        id: startCheck
        interval: 1500
        onTriggered: root.checkRunning()
    }

    DBus.Properties {
        id: props
        busType: DBus.BusType.Session
        service: root.running ? root.service : ""
        path: root.objectPath
        iface: root.service
    }

    property bool running: false
    readonly property var p: props.properties
    readonly property bool autoOn: running && p.AutoBrightnessEnabled === true
    readonly property bool paused: running && p.Paused === true
    readonly property bool sensorMissing: running && p.LightSensorAvailable === false
    readonly property bool presenceAvailable: running && p.PresenceAvailable === true
    readonly property bool presenceOn: presenceAvailable && p.PresenceEnabled === true
    readonly property real lux: running && p.Lux !== undefined ? p.Lux : 0
    readonly property real brightness: running && p.Brightness !== undefined ? p.Brightness : 0
    readonly property real target: running && p.Target !== undefined ? p.Target : 0
    readonly property real offset: running && p.Offset !== undefined ? p.Offset : 0

    function checkRunning() {
        DBus.SessionBus.asyncCall({
            service: "org.freedesktop.DBus",
            path: "/org/freedesktop/DBus",
            iface: "org.freedesktop.DBus",
            member: "NameHasOwner",
            arguments: [root.service],
        }, reply => { root.running = reply.value === true },
           () => { root.running = false })
    }

    function call(member, args) {
        DBus.SessionBus.asyncCall({
            service: root.service,
            path: root.objectPath,
            iface: root.service,
            member: member,
            arguments: args || [],
        })
    }

    function startService() {
        DBus.SessionBus.asyncCall({
            service: "org.freedesktop.systemd1",
            path: "/org/freedesktop/systemd1",
            iface: "org.freedesktop.systemd1.Manager",
            member: "StartUnit",
            arguments: ["plasma-light-and-presence.service", "replace"],
        }, () => startCheck.start(), () => startCheck.start())
    }

    function openSettings() {
        KCMUtils.KCMLauncher.openSystemSettings("kcm_lightandpresence")
    }

    // --- helpers -----------------------------------------------------------
    function luxText(v) {
        return v >= 100 ? i18n("%1 lx", Math.round(v)) : i18n("%1 lx", v.toFixed(1))
    }

    function luxWord(v) {
        if (v < 10) return i18n("Dark")
        if (v < 50) return i18n("Dim")
        if (v < 300) return i18n("Indoor")
        if (v < 1000) return i18n("Bright indoor")
        if (v < 10000) return i18n("Bright")
        return i18n("Daylight")
    }

    // 0..1 on a log scale up to 10000 lx, like the brightness curve
    function luxFraction(v) {
        return Math.min(1, Math.log(v + 1) / Math.LN10 / 4)
    }

    function offsetText(v) {
        if (Math.abs(v) < 0.5) return i18nc("no brightness preference", "Default")
        return v > 0 ? i18n("+%1%", Math.round(v)) : i18n("-%1%", Math.round(-v))
    }

    function statusText() {
        if (!running) return i18n("Service not running")
        if (sensorMissing) return i18n("No ambient light sensor")
        if (!autoOn) return i18n("Off")
        if (paused) return i18n("Paused while the screen is dimmed")
        return i18n("Following ambient light")
    }

    function presenceText() {
        switch (p.PresenceState) {
        case "present": return i18n("You are here")
        case "looking-away": return i18n("Looking away")
        case "away": return i18n("Away")
        case "disabled": return i18n("Off")
        default: return i18n("Unknown")
        }
    }

    // --- panel -------------------------------------------------------------
    Plasmoid.icon: autoOn ? iconOn : iconOff
    Plasmoid.status: running ? PlasmaCore.Types.ActiveStatus : PlasmaCore.Types.PassiveStatus
    toolTipMainText: i18n("Light & Presence")
    toolTipSubText: !running ? i18n("Service not running")
                  : !autoOn ? i18n("Automatic brightness off, screen at %1%", Math.round(brightness))
                  : i18n("%1 (%2), screen at %3%", luxText(lux), luxWord(lux), Math.round(brightness))

    PlasmaCore.Action {
        id: configureAction
        text: i18n("Configure Light & Presence…")
        icon.name: "configure"
        onTriggered: root.openSettings()
    }

    Component.onCompleted: Plasmoid.setInternalAction("configure", configureAction)

    compactRepresentation: MouseArea {
        hoverEnabled: true
        onClicked: root.expanded = !root.expanded

        Kirigami.Icon {
            anchors.fill: parent
            source: root.autoOn ? root.iconOn : root.iconOff
            isMask: true
            color: Kirigami.Theme.textColor
            active: parent.containsMouse
        }
    }

    // --- popup -------------------------------------------------------------
    component Card: Rectangle {
        default property alias content: inner.data
        radius: Kirigami.Units.cornerRadius
        color: Qt.alpha(Kirigami.Theme.textColor, 0.06)
        implicitHeight: inner.implicitHeight + Kirigami.Units.largeSpacing * 2
        implicitWidth: inner.implicitWidth + Kirigami.Units.largeSpacing * 2
        Layout.fillWidth: true
        ColumnLayout {
            id: inner
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.smallSpacing
        }
    }

    component Caption: PC3.Label {
        font.pointSize: Kirigami.Theme.smallFont.pointSize
        font.capitalization: Font.AllUppercase
        font.letterSpacing: 1
        opacity: 0.65
        elide: Text.ElideRight
        Layout.fillWidth: true
    }

    component Note: PC3.Label {
        wrapMode: Text.WordWrap
        font: Kirigami.Theme.smallFont
        opacity: 0.65
        Layout.fillWidth: true
    }

    fullRepresentation: PlasmaExtras.Representation {
        id: popup
        // The panel sizes popups from these hints; without a height the
        // popup collapses to the header.
        Layout.minimumWidth: Kirigami.Units.gridUnit * 20
        Layout.preferredWidth: Kirigami.Units.gridUnit * 22
        Layout.minimumHeight: popup.header.implicitHeight + popup.footer.implicitHeight
                              + body.implicitHeight + Kirigami.Units.largeSpacing * 2
        Layout.preferredHeight: Layout.minimumHeight

        header: PlasmaExtras.PlasmoidHeading {
            RowLayout {
                anchors.fill: parent
                spacing: Kirigami.Units.largeSpacing

                Kirigami.Icon {
                    source: root.iconColor
                    implicitWidth: Kirigami.Units.iconSizes.medium
                    implicitHeight: Kirigami.Units.iconSizes.medium
                }
                ColumnLayout {
                    spacing: 0
                    Layout.fillWidth: true
                    Kirigami.Heading {
                        level: 3
                        text: i18n("Light & Presence")
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    PC3.Label {
                        text: root.statusText()
                        font: Kirigami.Theme.smallFont
                        opacity: 0.7
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
                PC3.Switch {
                    enabled: root.running && !root.sensorMissing
                    checked: root.autoOn
                    onToggled: root.call(checked ? "EnableAutoBrightness" : "DisableAutoBrightness")
                    PC3.ToolTip.text: i18n("Adjust brightness to the ambient light")
                    PC3.ToolTip.visible: hovered
                }
            }
        }

        footer: PlasmaExtras.PlasmoidHeading {
            position: PC3.ToolBar.Footer
            RowLayout {
                anchors.fill: parent
                Item { Layout.fillWidth: true }
                PC3.ToolButton {
                    icon.name: "configure"
                    text: i18n("Configure…")
                    onClicked: root.openSettings()
                }
            }
        }

        ColumnLayout {
            id: body
            anchors.fill: parent
            anchors.margins: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.largeSpacing

            // service not running
            Card {
                visible: !root.running
                RowLayout {
                    spacing: Kirigami.Units.largeSpacing
                    Layout.fillWidth: true
                    Kirigami.Icon {
                        source: "dialog-warning"
                        implicitWidth: Kirigami.Units.iconSizes.medium
                        implicitHeight: Kirigami.Units.iconSizes.medium
                    }
                    PC3.Label {
                        text: i18n("The Light & Presence service is not running.")
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
                PC3.Button {
                    icon.name: "media-playback-start"
                    text: i18n("Start Service")
                    onClicked: root.startService()
                }
                Note {
                    text: i18n("To start it at every login, run: systemctl --user enable --now plasma-light-and-presence")
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }
            }

            // live values
            RowLayout {
                visible: root.running
                spacing: Kirigami.Units.largeSpacing
                Layout.fillWidth: true

                Card {
                    Layout.preferredWidth: 1
                    Caption { text: i18n("Ambient light") }
                    Kirigami.Heading {
                        level: 1
                        text: root.luxText(root.lux)
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    PC3.Label {
                        text: root.luxWord(root.lux)
                        opacity: 0.8
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    PC3.ProgressBar {
                        from: 0
                        to: 1
                        value: root.luxFraction(root.lux)
                        Layout.fillWidth: true
                    }
                }

                Card {
                    Layout.preferredWidth: 1
                    Caption { text: i18n("Screen") }
                    Kirigami.Heading {
                        level: 1
                        text: i18n("%1%", Math.round(root.brightness))
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    PC3.Label {
                        text: root.autoOn ? i18n("Target %1%", Math.round(root.target)) : i18n("Manual")
                        opacity: 0.8
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    PC3.ProgressBar {
                        from: 0
                        to: 100
                        value: root.brightness
                        Layout.fillWidth: true
                    }
                }
            }

            // preference
            Card {
                visible: root.running
                RowLayout {
                    Layout.fillWidth: true
                    Caption { text: i18n("Preference") }
                    PC3.Label {
                        text: root.offsetText(root.offset)
                        font.bold: true
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing
                    PC3.Label { text: i18n("Darker"); opacity: 0.7 }
                    PC3.Slider {
                        id: prefSlider
                        from: -30
                        to: 30
                        stepSize: 1
                        enabled: root.autoOn
                        Layout.fillWidth: true
                        // follow the service unless the user is dragging
                        Binding on value {
                            value: root.offset
                            when: !prefSlider.pressed
                        }
                        onMoved: root.call("SetOffset", [value])
                    }
                    PC3.Label { text: i18n("Brighter"); opacity: 0.7 }
                    PC3.ToolButton {
                        icon.name: "edit-undo"
                        enabled: root.autoOn && Math.abs(root.offset) >= 0.5
                        onClicked: root.call("ResetOffset")
                        PC3.ToolTip.text: i18n("Reset to the default curve")
                        PC3.ToolTip.visible: hovered
                    }
                }
                Note {
                    text: i18n("Changing the brightness yourself also adjusts this after a few seconds.")
                }
            }

            // presence
            Card {
                visible: root.running
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.largeSpacing
                    ColumnLayout {
                        spacing: 0
                        Layout.fillWidth: true
                        Caption { text: i18n("Presence") }
                        PC3.Label {
                            visible: root.presenceAvailable
                            text: root.presenceText()
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                    PC3.Switch {
                        enabled: root.presenceAvailable
                        checked: root.presenceOn
                        onToggled: root.call(checked ? "EnablePresence" : "DisablePresence")
                        PC3.ToolTip.text: i18n("Dim, lock and wake the screen based on presence")
                        PC3.ToolTip.visible: hovered
                    }
                }
                Note {
                    visible: !root.presenceAvailable
                    text: i18n("No supported presence sensor was found on this system.")
                }
            }

            Item { Layout.fillHeight: true }
        }
    }
}
