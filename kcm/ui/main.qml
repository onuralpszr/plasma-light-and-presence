// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    id: root

    readonly property var settings: kcm.settings
    readonly property var daemon: kcm.daemon
    readonly property var values: daemon.values
    readonly property bool running: daemon.running
    readonly property bool presenceUsable: running && values.PresenceAvailable === true
    readonly property bool autoOn: settings.autoBrightnessEnabled
    readonly property bool presenceOn: presenceUsable && settings.presenceEnabled

    function luxText(v) {
        return v >= 100 ? i18n("%1 lx", Math.round(v)) : i18n("%1 lx", v.toFixed(1))
    }

    function offsetText(v) {
        if (Math.abs(v) < 0.5) {
            return i18nc("no learned brightness adjustment", "None")
        }
        return v > 0 ? i18n("%1% brighter", Math.round(v)) : i18n("%1% darker", Math.round(-v))
    }

    function brightnessText() {
        const now = Math.round(values.Brightness || 0)
        if (!values.AutoBrightnessEnabled) {
            return i18n("%1% (manual)", now)
        }
        if (values.Paused) {
            return i18n("%1% (paused while the screen is dimmed)", now)
        }
        return i18n("%1% (target %2%)", now, Math.round(values.Target || 0))
    }

    function presenceText() {
        switch (values.PresenceState) {
        case "present": return i18n("Present")
        case "looking-away": return i18n("Present, looking away")
        case "away": return i18n("Away")
        case "disabled": return i18n("Not in use")
        default: return i18n("Unknown")
        }
    }

    component SecondsSpinBox: QQC2.SpinBox {
        editable: true
        textFromValue: (value, locale) => i18np("%1 second", "%1 seconds", value)
        valueFromText: (text, locale) => parseInt(text) || from
    }

    component PercentSpinBox: QQC2.SpinBox {
        editable: true
        textFromValue: (value, locale) => i18nc("percentage", "%1%", value)
        valueFromText: (text, locale) => parseInt(text) || from
    }

    header: ColumnLayout {
        spacing: 0

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !root.running
            type: Kirigami.MessageType.Warning
            position: Kirigami.InlineMessage.Position.Header
            text: i18n("The Light & Presence service is not running. Settings are saved, but nothing is applied until it runs. To start it at every login, run: systemctl --user enable --now plasma-light-and-presence")
            actions: Kirigami.Action {
                icon.name: "media-playback-start"
                text: i18n("Start Service")
                onTriggered: root.daemon.startService()
            }
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: root.running && root.values.LightSensorAvailable === false
            type: Kirigami.MessageType.Information
            position: Kirigami.InlineMessage.Position.Header
            text: i18n("No ambient light sensor was found. Check that iio-sensor-proxy is installed and running.")
        }
    }

    Kirigami.FormLayout {
        id: form

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: i18n("Current State")
        }

        QQC2.Label {
            Kirigami.FormData.label: i18n("Ambient light:")
            text: root.running ? root.luxText(root.values.Lux || 0) : i18n("Unknown")
        }

        QQC2.Label {
            Kirigami.FormData.label: i18n("Screen brightness:")
            text: root.running ? root.brightnessText() : i18n("Unknown")
        }

        RowLayout {
            Kirigami.FormData.label: i18n("Learned adjustment:")
            spacing: Kirigami.Units.smallSpacing

            QQC2.Label {
                text: root.running ? root.offsetText(root.values.Offset || 0) : i18n("Unknown")
            }
            QQC2.Button {
                icon.name: "edit-reset"
                text: i18n("Reset")
                enabled: root.running && Math.abs(root.values.Offset || 0) >= 0.5
                onClicked: root.daemon.resetOffset()
            }
        }

        QQC2.Label {
            Kirigami.FormData.label: i18n("Presence:")
            visible: root.presenceUsable
            text: root.presenceText()
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: i18n("Ambient Light")
        }

        QQC2.CheckBox {
            text: i18n("Adjust screen brightness to the ambient light")
            checked: root.settings.autoBrightnessEnabled
            onToggled: root.settings.autoBrightnessEnabled = checked
            KCM.SettingStateBinding {
                configObject: root.settings
                settingName: "AutoBrightnessEnabled"
            }
        }

        PercentSpinBox {
            Kirigami.FormData.label: i18n("Lowest brightness:")
            from: 1
            to: 100
            value: root.settings.minPercent
            onValueModified: root.settings.minPercent = value
            KCM.SettingStateBinding {
                configObject: root.settings
                settingName: "MinPercent"
                extraEnabledConditions: root.autoOn
            }
        }

        PercentSpinBox {
            Kirigami.FormData.label: i18n("Highest brightness:")
            from: 1
            to: 100
            value: root.settings.maxPercent
            onValueModified: root.settings.maxPercent = value
            KCM.SettingStateBinding {
                configObject: root.settings
                settingName: "MaxPercent"
                extraEnabledConditions: root.autoOn
            }
        }

        QQC2.ComboBox {
            Kirigami.FormData.label: i18n("Responsiveness:")
            model: [i18nc("responsiveness", "Slow"), i18nc("responsiveness", "Normal"), i18nc("responsiveness", "Fast")]
            currentIndex: root.settings.responsiveness
            onActivated: index => root.settings.responsiveness = index
            KCM.SettingStateBinding {
                configObject: root.settings
                settingName: "Responsiveness"
                extraEnabledConditions: root.autoOn
            }
        }

        QQC2.CheckBox {
            text: i18n("Show the brightness indicator on automatic changes")
            checked: root.settings.showOsd
            onToggled: root.settings.showOsd = checked
            KCM.SettingStateBinding {
                configObject: root.settings
                settingName: "ShowOsd"
                extraEnabledConditions: root.autoOn
            }
        }

        QQC2.Label {
            Layout.maximumWidth: Kirigami.Units.gridUnit * 22
            text: i18n("When you change the brightness yourself, the new level is remembered as your preference after a few seconds.")
            wrapMode: Text.WordWrap
            font: Kirigami.Theme.smallFont
            opacity: 0.7
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: i18n("Presence")
        }

        QQC2.Label {
            Layout.maximumWidth: Kirigami.Units.gridUnit * 22
            visible: !root.presenceUsable
            text: i18n("No supported presence sensor was found on this system.")
            wrapMode: Text.WordWrap
        }

        QQC2.CheckBox {
            text: i18n("Use the presence sensor")
            checked: root.settings.presenceEnabled
            onToggled: root.settings.presenceEnabled = checked
            KCM.SettingStateBinding {
                configObject: root.settings
                settingName: "PresenceEnabled"
                extraEnabledConditions: root.presenceUsable
            }
        }

        RowLayout {
            Kirigami.FormData.label: i18n("When you leave:")
            enabled: root.presenceUsable
            QQC2.CheckBox {
                id: dimAway
                text: i18n("Dim the screen after")
                checked: root.settings.dimWhenAway
                onToggled: root.settings.dimWhenAway = checked
                KCM.SettingStateBinding {
                    configObject: root.settings
                    settingName: "DimWhenAway"
                    extraEnabledConditions: root.presenceOn
                }
            }
            SecondsSpinBox {
                from: 5
                to: 600
                value: root.settings.dimAwaySeconds
                onValueModified: root.settings.dimAwaySeconds = value
                KCM.SettingStateBinding {
                    configObject: root.settings
                    settingName: "DimAwaySeconds"
                    extraEnabledConditions: root.presenceOn && root.settings.dimWhenAway
                }
            }
        }

        RowLayout {
            enabled: root.presenceUsable
            QQC2.CheckBox {
                text: i18n("Lock the screen after")
                checked: root.settings.lockWhenAway
                onToggled: root.settings.lockWhenAway = checked
                KCM.SettingStateBinding {
                    configObject: root.settings
                    settingName: "LockWhenAway"
                    extraEnabledConditions: root.presenceOn
                }
            }
            SecondsSpinBox {
                from: 10
                to: 1800
                value: root.settings.lockAwaySeconds
                onValueModified: root.settings.lockAwaySeconds = value
                KCM.SettingStateBinding {
                    configObject: root.settings
                    settingName: "LockAwaySeconds"
                    extraEnabledConditions: root.presenceOn && root.settings.lockWhenAway
                }
            }
        }

        QQC2.CheckBox {
            Kirigami.FormData.label: i18n("When you return:")
            text: i18n("Wake the screen (the lock screen stays in place)")
            checked: root.settings.wakeOnReturn
            onToggled: root.settings.wakeOnReturn = checked
            KCM.SettingStateBinding {
                configObject: root.settings
                settingName: "WakeOnReturn"
                extraEnabledConditions: root.presenceOn
            }
        }

        RowLayout {
            Kirigami.FormData.label: i18n("When you look away:")
            enabled: root.presenceUsable
            QQC2.CheckBox {
                text: i18n("Dim the screen after")
                checked: root.settings.dimWhenLookingAway
                onToggled: root.settings.dimWhenLookingAway = checked
                KCM.SettingStateBinding {
                    configObject: root.settings
                    settingName: "DimWhenLookingAway"
                    extraEnabledConditions: root.presenceOn
                }
            }
            SecondsSpinBox {
                from: 5
                to: 300
                value: root.settings.lookAwaySeconds
                onValueModified: root.settings.lookAwaySeconds = value
                KCM.SettingStateBinding {
                    configObject: root.settings
                    settingName: "LookAwaySeconds"
                    extraEnabledConditions: root.presenceOn && root.settings.dimWhenLookingAway
                }
            }
        }

        PercentSpinBox {
            Kirigami.FormData.label: i18n("Dimmed brightness:")
            from: 0
            to: 90
            value: root.settings.dimLevelPercent
            onValueModified: root.settings.dimLevelPercent = value
            KCM.SettingStateBinding {
                configObject: root.settings
                settingName: "DimLevelPercent"
                extraEnabledConditions: root.presenceOn
            }
        }

        QQC2.CheckBox {
            text: i18n("Do not dim or lock while an application blocks it (videos, presentations)")
            checked: root.settings.respectInhibitors
            onToggled: root.settings.respectInhibitors = checked
            KCM.SettingStateBinding {
                configObject: root.settings
                settingName: "RespectInhibitors"
                extraEnabledConditions: root.presenceOn
            }
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: i18n("Light Sensor")
        }

        QQC2.SpinBox {
            Kirigami.FormData.label: i18n("Ignore readings above:")
            editable: true
            from: 1000
            to: 200000
            stepSize: 1000
            value: root.settings.maxLux
            onValueModified: root.settings.maxLux = value
            textFromValue: (value, locale) => i18n("%1 lx", value)
            valueFromText: (text, locale) => parseInt(text) || from
            KCM.SettingStateBinding {
                configObject: root.settings
                settingName: "MaxLux"
            }
        }

        SecondsSpinBox {
            Kirigami.FormData.label: i18n("Spike filter window:")
            from: 1
            to: 30
            value: root.settings.spikeWindowSeconds
            onValueModified: root.settings.spikeWindowSeconds = value
            KCM.SettingStateBinding {
                configObject: root.settings
                settingName: "SpikeWindowSeconds"
            }
        }

        QQC2.Label {
            Layout.maximumWidth: Kirigami.Units.gridUnit * 22
            text: i18n("Some light sensors report short bursts of impossible values. Those readings are ignored, and short spikes within the window are filtered out.")
            wrapMode: Text.WordWrap
            font: Kirigami.Theme.smallFont
            opacity: 0.7
        }
    }
}
