# ovfconf

Tool for Linux guest VM customization based on vmware OVF environment (vApp properties)

# Overview

OVF Environment: see William Lam [introduction][lam-ovf-environment]

Unfortunately, there is no common way to utilize this fine mechanism to provide VM images
with self-configuration abilities (vmware implement one in VCenter Appliance OVF image as
`/etc/init.d/vaos`, but this implementation is somewhat hard to reuse and has too many
external dependences). This simple tool developed to fill this void.

[lam-ovf-environment]: http://www.virtuallyghetto.com/2012/06/ovf-runtime-environment.html

# Features

Script is intended to be run at system startup and re-configure freshly deployed image and
set new hostname and IP address (assuming same subnet and domain). Other optionally
configurable parameters include:
- gateway address
- DNS domain
- DNS servers
- NTP servers (ntpd and chrony are supported)
- remote syslog server address (syslog-ng and rsyslogd are supported)
- smarthost SMTP server address (for postfix)

Script is tested on Suse Linux Enterprise 11.x and CentOS 7.1 (and will refuse to run
elsewhere) under VMWare ESXi 5.5 hypervisor. Changes to adapt it to other platforms will
be minimal, and there is a special "test" mode to check effects on copy of "/etc" (see
source and "test" directory).

# Installation

Just copy `ovfconf` script to `/usr/local/sbin` and install startup scripts.
- centos 7.x

        cp ovfconf /usr/local/sbin/
        cp ovfconf.service /etc/systemd/system/
        systemctl enable ovfconf.service

- sles 11.x

        cp ovfconf /usr/local/sbin/
        cp boot.ovfconf /etc/init.d/
        chkconfig boot.ovfconf on

Example RPM spec for SLES 11 is also provided.

There are no requirements except perl, open-vm-tools (classic Vmware Tools will do too)
and usual system tools like `sed`.

# Usage modes

## Injecting OVF environment inside VM config file

Deploying OVF to standalone ESXi host with "ovftool" is not reliable: even with
`--X:injectOvfEnv --powerOn` it sometimes fail to actually pass OVF info. This could be
worked around with injecting OVF info directly into VM config (I've found with idea in
William Lam [blog post][lam-ovf-injection]). Basically, one must
- prepare XML file (see "Technical Details" section for format description)
- convert it to one long line by escaping double-quote to "|22", newline to "|0A":

        cat ovfEnv.falcon-e1.xml | perl -ane '$_ =~ s/"/|22/g; $_ =~ s/\n/|0A/g; print'

- add `guestinfo.ovfEnv = "<that blob">` into `<vm>.vmx`
- `vim-cmd vmsvc/reload <vm>` and start VM

[lam-ovf-injection]: http://www.virtuallyghetto.com/2014/06/an-alternate-way-to-inject-ovf-properties-when-deploying-virtual-appliances-directly-onto-esxi.html

# Technical details on operation

To get OVF environment from hypervisor script calls `vmware-rpctool 'info-get
guestinfo.ovfEnv'` producing XML like

    <?xml version="1.0" encoding="UTF-8"?>
    <Environment
         xmlns="http://schemas.dmtf.org/ovf/environment/1"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xmlns:oe="http://schemas.dmtf.org/ovf/environment/1"
         xmlns:ve="http://www.vmware.com/schema/ovfenv"
         oe:id=""
         ve:vCenterId="vm-136">
       <PlatformSection>
          <Kind>VMware ESXi</Kind>
          <Version>5.5.0</Version>
          <Vendor>VMware, Inc.</Vendor>
          <Locale>en</Locale>
       </PlatformSection>
       <PropertySection>
             <Property oe:key="dns" oe:value="1.2.3.1,1.2.3.2"/>
             <Property oe:key="domain" oe:value="domain.com"/>
             <Property oe:key="gateway" oe:value="1.1.1.254"/>
             <Property oe:key="hostname" oe:value="testvm1"/>
             <Property oe:key="ip" oe:value="1.1.1.1"/>
             <Property oe:key="ntp" oe:value="ntp1.domain.com, ntp2.domain.com"/>
             <Property oe:key="relay" oe:value="smtp.domain.com"/>
             <Property oe:key="syslog" oe:value="log.domain.com"/>
       </PropertySection>
       <ve:EthernetAdapterSection>
          <ve:Adapter ve:mac="00:50:56:90:1f:50" ve:network="adm-vm" ve:unitNumber="7"/>
       </ve:EthernetAdapterSection>
    </Environment>

Values for configuration parameters then extracted and compared with current ones,
performing required changes in OS config.

# Limitations

- no ipv6 support, only one interface is supported
- untested on redhat/centos 6.x, sles 12 etc
- only some hard-coded apps and services are supported
- has some assumptions about configuraton file formats

# Caveats

- redhat/centos: better enable DSA key generation in /etc/sysconfig/sshd

# Further ideas

- Separate configuration file with options like log location
