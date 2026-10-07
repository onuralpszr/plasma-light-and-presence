// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>

#include "kcm.h"

#include <KPluginFactory>

#include <QQmlEngine>

K_PLUGIN_CLASS_WITH_JSON(PlasmaSensordKcm, "kcm_plasmasensord.json")

PlasmaSensordKcm::PlasmaSensordKcm(QObject *parent, const KPluginMetaData &metaData)
    : KQuickManagedConfigModule(parent, metaData)
    , m_settings(new PlasmaSensordSettings(this))
    , m_daemon(new DaemonClient(this))
{
    qmlRegisterAnonymousType<PlasmaSensordSettings>("org.plasmasensord.kcm", 1);
    qmlRegisterAnonymousType<DaemonClient>("org.plasmasensord.kcm", 1);
    setButtons(Apply | Default);
}

PlasmaSensordSettings *PlasmaSensordKcm::settings() const
{
    return m_settings;
}

DaemonClient *PlasmaSensordKcm::daemon() const
{
    return m_daemon;
}

void PlasmaSensordKcm::save()
{
    KQuickManagedConfigModule::save();
    // The daemon also watches the file; this makes the change immediate.
    m_daemon->reload();
}

#include "kcm.moc"
