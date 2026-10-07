// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>

#pragma once

#include <KQuickManagedConfigModule>

#include "daemonclient.h"
#include "lightandpresencesettings.h"

class LightAndPresenceKcm : public KQuickManagedConfigModule
{
    Q_OBJECT
    Q_PROPERTY(LightAndPresenceSettings *settings READ settings CONSTANT)
    Q_PROPERTY(DaemonClient *daemon READ daemon CONSTANT)

public:
    LightAndPresenceKcm(QObject *parent, const KPluginMetaData &metaData);

    LightAndPresenceSettings *settings() const;
    DaemonClient *daemon() const;

    void save() override;

private:
    LightAndPresenceSettings *m_settings;
    DaemonClient *m_daemon;
};
