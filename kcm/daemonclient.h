// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>

#pragma once

#include <QObject>
#include <QVariantMap>

class QDBusServiceWatcher;

/**
 * Live view of the plasma-sensord daemon on the session bus.
 *
 * All daemon properties are mirrored in `values` (keys as on D-Bus, such as
 * "Lux" or "PresenceAvailable") and kept current from PropertiesChanged.
 */
class DaemonClient : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool running READ running NOTIFY runningChanged)
    Q_PROPERTY(QVariantMap values READ values NOTIFY valuesChanged)

public:
    explicit DaemonClient(QObject *parent = nullptr);

    bool running() const;
    QVariantMap values() const;

    Q_INVOKABLE void resetOffset();
    Q_INVOKABLE void reload();
    Q_INVOKABLE void startService();

Q_SIGNALS:
    void runningChanged();
    void valuesChanged();

private Q_SLOTS:
    void onPropertiesChanged(const QString &interface, const QVariantMap &changed, const QStringList &invalidated);

private:
    void setRunning(bool running);
    void fetchAll();
    void call(const QString &method);

    QDBusServiceWatcher *m_watcher;
    bool m_running = false;
    QVariantMap m_values;
};
