# ovfconf

Tool for Linux guest VM customization based on vmware OVF environment (vApp properties).

(documentation is work-in-progress, hope to finish it soon)

# Overview

OVF Environment is a way to pass arbitrary data to guest VM while deploying it from OVF
template, most useful are hostname and IP address (see [OVF specification][ovf-spec] and
William Lam [introduction][lam-ovf-environment] for details). In form of "vApp properties"
it could be used to pass data from vCenter to VM at startup.

This simple script allows to customize VMs deployed from OVF template or by cloning by
manually assigning host configuration parameters and reconfigure software after address
change.

[ovf-spec]: http://dmtf.org/sites/default/files/standards/documents/DSP0243_1.1.1.pdf
[lam-ovf-environment]: http://www.virtuallyghetto.com/2012/06/ovf-runtime-environment.html

# Mode of operation and affected files

Script is itended to be run at system startup to re-configure freshly deployed image or
clone. After getting data from OVF environment it checks for hostname and IP address
change. If changed, new IP address and host name are set in
- interface configuration file
- hosts file
- hostname config file
- "root" user description in `/etc/passwd`
- some application configs (sshd, nrpe, syslog-ng)

Other optionally configurable vApp parameters include:
- gateway address
- DNS domain
- DNS servers
- NTP servers (ntpd and chrony are supported)
- remote syslog server address (syslog-ng and rsyslogd are supported)
- smarthost SMTP server address (for postfix)

Finally, ssh host keys are erased (to be automatically regenerated for new host) and so
clone is fully configured at the end of boot process.

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

## Cloning VMs in vCenter

## Deploying OVF templates or cloning VMs with ovftool

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
- configuration parametrs (like log file name) are hard-coded too

# Caveats

- redhat/centos: better enable DSA key generation in /etc/sysconfig/sshd
