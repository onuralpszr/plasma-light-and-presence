Name:           plasma-sensord
Version:        0.1.0
Release:        1%{?dist}
Summary:        Ambient light brightness and presence sensing for KDE Plasma

License:        Apache-2.0
URL:            https://github.com/onuralpszr/plasma-sensord
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

%description
plasma-sensord adjusts the screen brightness of a KDE Plasma session from the
ambient light sensor, and can react to human presence when the hardware has a
usable presence sensor: dim the screen when you leave, lock it when you stay
away, and wake it to the lock screen when you return.

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
%py_byte_compile %{python3} %{buildroot}%{_datadir}/plasma-sensord

%check
desktop-file-validate %{buildroot}%{_kf6_datadir}/applications/kcm_plasmasensord.desktop

%post
%systemd_user_post plasma-sensord.service

%preun
%systemd_user_preun plasma-sensord.service

%postun
%systemd_user_postun_with_restart plasma-sensord.service

%files
%license LICENSE
%doc README.md
%{_bindir}/plasma-sensord
%{_datadir}/plasma-sensord/
%{_userunitdir}/plasma-sensord.service
%{_kf6_qtplugindir}/plasma/kcms/systemsettings/kcm_plasmasensord.so
%{_kf6_datadir}/applications/kcm_plasmasensord.desktop
%{_kf6_datadir}/config.kcfg/plasmasensordsettings.kcfg
%{_kf6_datadir}/plasma/plasmoids/org.plasmasensord.widget/
%{_datadir}/icons/hicolor/scalable/apps/plasma-sensord.svg
%{_datadir}/icons/hicolor/scalable/apps/plasma-sensord-symbolic.svg
%{_datadir}/icons/hicolor/scalable/apps/plasma-sensord-off-symbolic.svg

%changelog
* Wed Oct 07 2026 Onuralp SEZER <thunderbirdtr@fedoraproject.org> - 0.1.0-1
- Initial package
