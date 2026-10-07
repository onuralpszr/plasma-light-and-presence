# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>

kcmutils_add_qml_kcm(kcm_lightandpresence SOURCES kcm.cpp daemonclient.cpp)

kconfig_add_kcfg_files(kcm_lightandpresence lightandpresencesettings.kcfgc GENERATE_MOC)

target_compile_definitions(kcm_lightandpresence PRIVATE TRANSLATION_DOMAIN="kcm_lightandpresence")

target_link_libraries(kcm_lightandpresence PRIVATE
    Qt::Core
    Qt::DBus
    Qt::Qml
    KF6::ConfigCore
    KF6::ConfigGui
    KF6::CoreAddons
    KF6::I18n
    KF6::KCMUtilsQuick
)

install(FILES lightandpresencesettings.kcfg DESTINATION ${KDE_INSTALL_KCFGDIR})
