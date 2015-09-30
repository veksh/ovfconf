Summary:        Tool to configure Linux VM with OVF Environment data
Name:           ovfconf
Version:        1.0.0
Release:        1
License:        none
Group:          Applications/System
Vendor:         Alexey Vekshin
Packager:       Alexey Vekshin <alex@maxidom.ru>
Provides:       ovfconf
Requires:       perl >= 5.0, bash, open-vm-tools
Source:         %{name}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-build
URL:            https://github.com/veksh/ovfconf

%description

%prep
%setup -n %{name}

%build

%install
# create directories where the files will be located
mkdir -p $RPM_BUILD_ROOT/usr/local/sbin
mkdir -p $RPM_BUILD_ROOT/etc/init.d

# put the files in to the relevant directories.
install -m 755 ovfconf             $RPM_BUILD_ROOT/usr/local/sbin
install -m 755 boot.ovfconf        $RPM_BUILD_ROOT/etc/init.d

%pre

%post
echo "do not forget to enable startup (chkconfig boot.ovfconf on)"

%clean
rm -rf $RPM_BUILD_ROOT
rm -rf %{_tmppath}/%{name}
rm -rf %{_topdir}/BUILD/%{name}

%files
%defattr(-,root,root)
/usr/local/sbin/ovfconf
/etc/init.d/boot.ovfconf

%changelog
* Wed Sep 30 2015 alex
  - first release of RPM spec
