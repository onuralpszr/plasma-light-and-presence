// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>

#pragma once

#include <KQuickManagedConfigModule>

#include "daemonclient.h"
#include "plasmasensordsettings.h"

class PlasmaSensordKcm : public KQuickManagedConfigModule
{
    Q_OBJECT
    Q_PROPERTY(PlasmaSensordSettings *settings READ settings CONSTANT)
    Q_PROPERTY(DaemonClient *daemon READ daemon CONSTANT)

public:
    PlasmaSensordKcm(QObject *parent, const KPluginMetaData &metaData);

    PlasmaSensordSettings *settings() const;
    DaemonClient *daemon() const;

    void save() override;

private:
    PlasmaSensordSettings *m_settings;
    DaemonClient *m_daemon;
};
