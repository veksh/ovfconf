# ovfconf

Simple script to customize VM clones (or OVF template deployments) with new network
settings taken from OVF/vApp metadata

# Overview

OVF Environment is a way to pass arbitrary data to guest VM on power on, widely used to
customize network parameters while deploying OVF templates. In form of "vApp properties"
it could be also used to customize VM metadata in vCenter and to pass it to VM at startup.
This script reads that metadata and updates OS configuration if required. Script is short,
relatively easy to extend and not have external dependences like XML parsers, making it
easy to integrate it in golden VM templates or OVF images.

See [OVF specification][ovf-spec] and William Lam [blog][lam-ovf-environment] for further
details about OVF Environment, and VMware [blog post][vmware-ovf-blog] for some earlier
example of OS customization script.

[ovf-spec]: http://dmtf.org/sites/default/files/standards/documents/DSP0243_1.1.1.pdf
[lam-ovf-environment]: http://www.virtuallyghetto.com/2012/06/ovf-runtime-environment.html
[vmware-ovf-blog]: http://blogs.vmware.com/vapp/2009/07/selfconfiguration-and-the-ovf-environment.html

# Mode of operation and configuration changes

Script is intended to be run at system startup to re-configure freshly deployed image or
clone (but could be run later manually or be tried in test mode, see below). After getting
data from OVF environment it checks for hostname and IP address change. If changed, new IP
address and host name are set in
- interface configuration file
- hosts file
- hostname config file
- "root" user description in `/etc/passwd`
- some application configs (sshd, nrpe, syslog-ng)

Other optionally configurable vApp parameters include:
- gateway IP address
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

It is safe to run this script at every startup: if environment is not changed (or not
available for some reason) no changes are performed.

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

There are no requirements except `perl`, `open-vm-tools` (classic Vmware Tools will do too)
and usual system tools like `sed`.

# VM and vCenter configuration

## vCenter: optional network profile

To simplify cloning between data centers, "network profile" could be assigned to main VM
administrative network (later referred as "adm-vm"). Settings for subnet mask, gateway,
DNS servers could be obtained from that profile. To configure it, go to "Networking"
section of vCenter administrative interface, select "adm-vm" and associate network profile
with it with multi-step wizard:
- name: "adm-vm ip profile"
- configure subnet and gateway, no DHCP, configure DNS server addresses, no ip pool
    - dns is specified as "10.0.128.1, 10.0.128.2" but passed w/o space in OVF env
    - possible separators are comma, semicolon on space
- skip ipv6
- configure DNS domain, no host prefix, search domain is same as, no proxy

After that, some properties like "gateway" could be replaced with their "dynamic"
versions: instead of "static String" dynamic "Gateway from <net>" could be used.

## vApp properties

Configure properties metadata for vApp before cloning: on VM settings in vCenter go to
last page ("vApp options"), enable them. Proceed to create metadata as follows (do not
forget to specify current values as defaults, or VM will be reconfigured at startup):
- Ensure ip allocation policy = "manual"
- Expand "Properties", add our props (set "Category" and "Label", do not change rest)
    - Category `name`: mandatory
        - `hostname`: static "String" 3-30, default: current hostname
        - `domain`: static "String" 5-50, default: current DNS domain name
           - or dynamic "Domain name" from "adm-vm" network
    - Category `address`: mandatory
        - `ip`: static "vApp IP address" in "adm-vm", default: current IP
        - `gateway`: dynamic "Gateway from adm-vm" or static "vApp IP address" in
          "adm-vm", default: current GW
    - Category `services`: optional; will be kept untouched if not used
        - `dns`: dynamic "DNS servers" from "adm-vm"
        - `ntp`: static String 5-50, default: current NTP servers, comma-separated
           (there is no ntp property in network profile)
        - `syslog`: static String 5-30, default: current syslog server IP or name
            - "External IP Address" would be better, but there is no "default value" field
              for it in 5.5 for some reason
        - `relay`: static String 5-50, default: current smarthost
- "IP Allocation": scheme "OVF environment", "IPv4"
- "Autoring"/"OVF Environment transport": check "VMware Tools"

Manual creation of properties in OVF template is possible too, but usually it is easier to
configure them in vCenter and export template with `ovftool` (see below). Usually exported
template requires a bit of manual customization, but most things work.

# VM deployment scenarios

## General preparation

Better power off VM before cloning. If "host file" is connected to CD-ROM disconnect it
before cloning or copy of this file will be created. Better enable DSA key generation in
`/etc/sysconfig/sshd` or older ssh clients will be unable to connect.

## Cloning VMs in vCenter

Clone machine as usual, do not opt for "customize OS". On step 1e ("Customize vApp
properties"), enter new host name and IP address (and rest of params if moving to other
domain or network). Review configuration and power on VM.

If everything worked as expected, new IP address will be assigned and visible in vCenter
shortly after boot. If something is amiss, VM will probably boot with old IP address and
hostname (as exact copy of original), investigate log (`/tmp/ovfconf.log`) and retry.

## Deploying OVF templates or cloning VMs with ovftool

[`ovftool`][ovf-tool-doc] is command-line utility to work with VM images (not limited to
OVF templates). It could be used to export VM to OVF image and import it again, and also
to clone VMs, extract metadata and so on (see documentation for details), like this:
- preview VM metadata and properties

        ovftool vi://<user>@<vca>/<datacenter>/vm/<vm-name>

- clone VM from one vCenter to another: only hostname and ip specified, rest of properties
  assumed to be same (or come from network profile)

        ovftool --name=new-vm \
          --datastore=host-storage1 --diskMode=thin \
          --network=adm-vm \
          --prop:"hostname=new-vm" \
          --prop:"ip=1.2.3.4" \
          vi://user@vca1/dc1/vm/template-vm \
          vi://alex@vca2/dc2/host/newhost.domain.com

One small caveat: `ovftool` does not work correctly when password contains special
symbols that require HTML escaping, so try to use alphanumeric passwords ("-" is ok too).

[ovf-tool-doc]: https://www.vmware.com/support/developer/ovf/

## Injecting OVF environment inside VM config file

Deploying OVF to standalone ESXi host with `ovftool` is not reliable: even with
`--X:injectOvfEnv --powerOn` it sometimes fail to actually pass OVF info. This could be
worked around with injecting OVF directly into VM config (I've found with idea in William
Lam [blog post][lam-ovf-injection]). Basically, one must
- clone VM somehow (`ovftool` is easiest way)

        ovftool --name=newvm \
          --X:logLevel=verbose --X:logFile=newvm.log \
          --datastore=host2-ds1 --diskMode=thin \
          --network=adm-srv \
          vi://root@oldhost/template-vm \
          vi://root@newhost/

- perform basic customization like enabling VNC console (just in case)
- prepare XML file (see "Technical Details" section for format description and example)
- convert it to one long line by escaping double-quote to "|22", newline to "|0A":

        cat ovfEnv.newvm.xml | perl -ane '$_ =~ s/"/|22/g; $_ =~ s/\n/|0A/g; print'

- add `guestinfo.ovfEnv = "<that blob">` into `<vm>.vmx`
- `vim-cmd vmsvc/reload <vm>` and start VM

[lam-ovf-injection]: http://www.virtuallyghetto.com/2014/06/an-alternate-way-to-inject-ovf-properties-when-deploying-virtual-appliances-directly-onto-esxi.html

# Technical details on operation, XML data format

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

Values for configuration parameters are then extracted and compared with current settings,
and configs are changed when necessary.

On every boot copy of that XML will be created in `/tmp/ovfEnv.xml` (this could be used as
a template for customization or as debugging aid), log of activity is in `/tmp/ovfconf.log`.

# Limitations

- only one interface is supported
- no ipv6 support
- untested on redhat/centos 6.x, sles 12 etc
- only some hard-coded apps and services are supported
- has some assumptions about configuraton file formats
- configuration parametrs (like log file name) are hard-coded too
