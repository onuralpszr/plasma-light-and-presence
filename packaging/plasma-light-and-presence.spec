Name:           plasma-light-and-presence
Version:        0.1.0
Release:        2%{?dist}
Summary:        Ambient light brightness and presence sensing for KDE Plasma

License:        Apache-2.0
URL:            https://github.com/onuralpszr/plasma-light-and-presence
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildRequires:  cmake
BuildRequires:  desktop-file-utils
BuildRequires:  extra-cmake-modules
BuildRequires:  gcc-c++
BuildRequires:  kf6-rpm-macros
BuildRequires:  python3-devel
BuildRequires:  systemd-rpm-macros
BuildRequires:  cmake(Qt6Core)
BuildRequires:  cmake(Qt6DBus)
BuildRequires:  cmake(Qt6Qml)
BuildRequires:  cmake(Qt6Quick)
BuildRequires:  cmake(KF6Config)
BuildRequires:  cmake(KF6CoreAddons)
BuildRequires:  cmake(KF6I18n)
BuildRequires:  cmake(KF6KCMUtils)

# Daemon
Requires:       python3-dbus
Requires:       python3-gobject
Requires:       iio-sensor-proxy
# org.kde.ScreenBrightness
Requires:       powerdevil
# loginctl
Requires:       systemd
# Settings page and widget
Requires:       kf6-kcmutils
Requires:       kf6-kirigami
Requires:       plasma-workspace
Requires:       hicolor-icon-theme

# The xps-ptl-tools prototype shipped the same feature under another name.
Obsoletes:      xps-ptl-tools < 1.0
# Published briefly under its first name
Obsoletes:      plasma-sensord < 0.1.1

%description
plasma-light-and-presence adjusts the screen brightness of a KDE Plasma session
from the ambient light sensor, and can react to human presence when the
hardware has a usable presence sensor: dim the screen when you leave, lock it
when you stay away, and wake it to the lock screen when you return.

It consists of a user service, a "Light & Presence" page in System Settings
and a Plasma widget. The service is not enabled automatically; README.md
explains how each user can enable it.

%prep
%autosetup -p1

%build
%cmake_kf6
%cmake_build

%install
%cmake_install
%py_byte_compile %{python3} %{buildroot}%{_datadir}/plasma-light-and-presence

%check
desktop-file-validate %{buildroot}%{_kf6_datadir}/applications/kcm_lightandpresence.desktop

%post
%systemd_user_post plasma-light-and-presence.service

%preun
%systemd_user_preun plasma-light-and-presence.service

%postun
%systemd_user_postun_with_restart plasma-light-and-presence.service

%files
%license LICENSE
%doc README.md
%{_bindir}/plasma-light-and-presence
%{_datadir}/plasma-light-and-presence/
%{_userunitdir}/plasma-light-and-presence.service
%{_kf6_qtplugindir}/plasma/kcms/systemsettings/kcm_lightandpresence.so
%{_kf6_datadir}/applications/kcm_lightandpresence.desktop
%{_kf6_datadir}/config.kcfg/lightandpresencesettings.kcfg
%{_kf6_datadir}/plasma/plasmoids/io.github.onuralpszr.lightandpresence/
%{_datadir}/icons/hicolor/scalable/apps/io.github.onuralpszr.lightandpresence.svg
%{_datadir}/icons/hicolor/scalable/apps/io.github.onuralpszr.lightandpresence-symbolic.svg
%{_datadir}/icons/hicolor/scalable/apps/io.github.onuralpszr.lightandpresence-off-symbolic.svg

%changelog
* Wed Oct 07 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org> - 0.1.0-2
- Name the icons after the app id, so KDE no longer shows the Plasma logo
  in their place, and ship the widget icons inside the widget package

* Wed Oct 07 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org> - 0.1.0-1
- Initial package
