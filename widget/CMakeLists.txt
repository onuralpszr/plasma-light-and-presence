# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>

# A pure QML applet: install the package directory as it is.
install(DIRECTORY package/
        DESTINATION ${KDE_INSTALL_DATADIR}/plasma/plasmoids/io.github.onuralpszr.lightandpresence)

# The widget loads its icons from its own package, so the panel icon does not
# depend on the icon theme.
install(FILES ${CMAKE_SOURCE_DIR}/data/icons/io.github.onuralpszr.lightandpresence.svg
              ${CMAKE_SOURCE_DIR}/data/icons/io.github.onuralpszr.lightandpresence-symbolic.svg
              ${CMAKE_SOURCE_DIR}/data/icons/io.github.onuralpszr.lightandpresence-off-symbolic.svg
        DESTINATION ${KDE_INSTALL_DATADIR}/plasma/plasmoids/io.github.onuralpszr.lightandpresence/contents/icons)
