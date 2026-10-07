# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org>

# The Python modules are private to the daemon, so they live in the
# package's data directory instead of the system site-packages.
set(LIGHT_AND_PRESENCE_PYTHON_DIR "${KDE_INSTALL_FULL_DATADIR}/plasma-light-and-presence")

configure_file(plasma-light-and-presence.in ${CMAKE_CURRENT_BINARY_DIR}/plasma-light-and-presence @ONLY)
install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/plasma-light-and-presence DESTINATION ${KDE_INSTALL_BINDIR})

install(DIRECTORY light_and_presence
        DESTINATION ${KDE_INSTALL_DATADIR}/plasma-light-and-presence
        FILES_MATCHING PATTERN "*.py"
        PATTERN "__pycache__" EXCLUDE)

configure_file(plasma-light-and-presence.service.in ${CMAKE_CURRENT_BINARY_DIR}/plasma-light-and-presence.service @ONLY)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/plasma-light-and-presence.service DESTINATION ${KDE_INSTALL_SYSTEMDUSERUNITDIR})
