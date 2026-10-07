# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>

# The Python modules are private to the daemon, so they live in the
# package's data directory instead of the system site-packages.
set(PLASMA_SENSORD_PYTHON_DIR "${KDE_INSTALL_FULL_DATADIR}/plasma-sensord")

configure_file(plasma-sensord.in ${CMAKE_CURRENT_BINARY_DIR}/plasma-sensord @ONLY)
install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/plasma-sensord DESTINATION ${KDE_INSTALL_BINDIR})

install(DIRECTORY plasma_sensord
        DESTINATION ${KDE_INSTALL_DATADIR}/plasma-sensord
        FILES_MATCHING PATTERN "*.py"
        PATTERN "__pycache__" EXCLUDE)

configure_file(plasma-sensord.service.in ${CMAKE_CURRENT_BINARY_DIR}/plasma-sensord.service @ONLY)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/plasma-sensord.service DESTINATION ${KDE_INSTALL_SYSTEMDUSERUNITDIR})
