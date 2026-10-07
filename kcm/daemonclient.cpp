// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>

#include "daemonclient.h"

#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QDBusMessage>
#include <QDBusPendingCallWatcher>
#include <QDBusPendingReply>
#include <QDBusServiceWatcher>

using namespace Qt::StringLiterals;

static const QString s_service = u"io.github.onuralpszr.LightAndPresence"_s;
static const QString s_path = u"/io/github/onuralpszr/LightAndPresence"_s;
static const QString s_interface = u"io.github.onuralpszr.LightAndPresence"_s;
static const QString s_propertiesInterface = u"org.freedesktop.DBus.Properties"_s;

DaemonClient::DaemonClient(QObject *parent)
    : QObject(parent)
    , m_watcher(new QDBusServiceWatcher(s_service, QDBusConnection::sessionBus(), QDBusServiceWatcher::WatchForOwnerChange, this))
{
    connect(m_watcher, &QDBusServiceWatcher::serviceRegistered, this, [this] {
        setRunning(true);
    });
    connect(m_watcher, &QDBusServiceWatcher::serviceUnregistered, this, [this] {
        setRunning(false);
    });

    QDBusConnection::sessionBus().connect(s_service,
                                          s_path,
                                          s_propertiesInterface,
                                          u"PropertiesChanged"_s,
                                          this,
                                          SLOT(onPropertiesChanged(QString, QVariantMap, QStringList)));

    // The watcher reports changes only; ask whether the daemon is already up.
    setRunning(QDBusConnection::sessionBus().interface()->isServiceRegistered(s_service));
}

bool DaemonClient::running() const
{
    return m_running;
}

QVariantMap DaemonClient::values() const
{
    return m_values;
}

void DaemonClient::setRunning(bool running)
{
    if (running) {
        fetchAll();
    } else if (!m_values.isEmpty()) {
        m_values.clear();
        Q_EMIT valuesChanged();
    }
    if (m_running != running) {
        m_running = running;
        Q_EMIT runningChanged();
    }
}

void DaemonClient::fetchAll()
{
    QDBusMessage msg = QDBusMessage::createMethodCall(s_service, s_path, s_propertiesInterface, u"GetAll"_s);
    msg << s_interface;
    auto *watcher = new QDBusPendingCallWatcher(QDBusConnection::sessionBus().asyncCall(msg), this);
    connect(watcher, &QDBusPendingCallWatcher::finished, this, [this](QDBusPendingCallWatcher *call) {
        QDBusPendingReply<QVariantMap> reply = *call;
        call->deleteLater();
        if (reply.isError()) {
            return;
        }
        m_values = reply.value();
        Q_EMIT valuesChanged();
    });
}

void DaemonClient::onPropertiesChanged(const QString &interface, const QVariantMap &changed, const QStringList &invalidated)
{
    Q_UNUSED(invalidated)
    if (interface != s_interface) {
        return;
    }
    for (auto it = changed.cbegin(); it != changed.cend(); ++it) {
        m_values.insert(it.key(), it.value());
    }
    Q_EMIT valuesChanged();
}

void DaemonClient::call(const QString &method)
{
    QDBusConnection::sessionBus().asyncCall(QDBusMessage::createMethodCall(s_service, s_path, s_interface, method));
}

void DaemonClient::resetOffset()
{
    call(u"ResetOffset"_s);
}

void DaemonClient::reload()
{
    if (m_running) {
        call(u"Reload"_s);
    }
}

void DaemonClient::startService()
{
    QDBusMessage msg = QDBusMessage::createMethodCall(u"org.freedesktop.systemd1"_s,
                                                      u"/org/freedesktop/systemd1"_s,
                                                      u"org.freedesktop.systemd1.Manager"_s,
                                                      u"StartUnit"_s);
    msg << u"plasma-light-and-presence.service"_s << u"replace"_s;
    QDBusConnection::sessionBus().asyncCall(msg);
}
