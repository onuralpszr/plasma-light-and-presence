// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>

#include "kcm.h"

#include <KPluginFactory>

#include <QQmlEngine>

K_PLUGIN_CLASS_WITH_JSON(LightAndPresenceKcm, "kcm_lightandpresence.json")

LightAndPresenceKcm::LightAndPresenceKcm(QObject *parent, const KPluginMetaData &metaData)
    : KQuickManagedConfigModule(parent, metaData)
    , m_settings(new LightAndPresenceSettings(this))
    , m_daemon(new DaemonClient(this))
{
    qmlRegisterAnonymousType<LightAndPresenceSettings>("io.github.onuralpszr.lightandpresence.kcm", 1);
    qmlRegisterAnonymousType<DaemonClient>("io.github.onuralpszr.lightandpresence.kcm", 1);
    setButtons(Apply | Default);
}

LightAndPresenceSettings *LightAndPresenceKcm::settings() const
{
    return m_settings;
}

DaemonClient *LightAndPresenceKcm::daemon() const
{
    return m_daemon;
}

void LightAndPresenceKcm::save()
{
    KQuickManagedConfigModule::save();
    // The daemon also watches the file; this makes the change immediate.
    m_daemon->reload();
}

#include "kcm.moc"
