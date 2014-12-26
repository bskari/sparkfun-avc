#!/bin/bash
# Prepares a fresh installation of an SD card for the Sparkfun AVC.

# First, download pi-whatever and burn it to an SD card:
#   dd if=raspberry-pi.img of=/dev/sdb bs=1M
# Install git and clone the repo:
#   git clone git@www.skari.org:sparkfun-avc
# Run this file!

set -u
set -e

if [ "${USER}" != 'root' ];
then
    echo 'You must be root'
    exit 1
fi

adduser bs
echo 'bs:sparkfun' | chpasswd

apt-get update
apt-get upgrade
# TODO: Install raspistill and raspivid? We could use the picamera Python library
# TODO: What about gstreamer?
apt-get install \
    dnsmasq \
    python-virtualenv \
    python3-pip \
    hostapd \
    tmux \
    iw

for command_ in \
    'echo +++ network +++' \
        'cp interfaces /etc/network/interfaces' \
        'ifdown wlan0' \
        'ifup wlan0' \
    'echo +++ hostapd +++' \
        'cp hostapd /etc/default/hostapd' \
        'cp hostapd.conf /etc/hostapd/hostapd.conf' \
        'curl http://dl.dropbox.com/u/1663660/hostapd/hostapd > /usr/sbin/hostapd' \
        'chown root:root /usr/sbin/hostapd' \
        'chmod 755 /usr/sbin/hostapd' \
        'service hostapd restart' \
    'echo +++ dnsmasq +++' \
        'cp dnsmasq.conf /etc/dnsmasq.conf' \
        'service dnsmasq restart' \
    'echo +++ Sparkfun AVC control +++' \
        'pushd ~/sparkfun-avc/control' \
        'su -c "mkvirtualenv sparkfun -p /usr/bin/python3" bs' \
        'su -c "pip install -r requirements.txt" bs' \
        'su -c "deactivate" bs' \
        'popd' \
        'pushd ~/sparkfun-avc/setup' \
        'make rooter' \
        'chown root:root rooter' \
        'chmod +s rooter' \
        'popd' \
        'cp sparkfun-rc /etc/init.d/' \
        'update-rc.d sparkdun-rc defaults' \
    'echo +++ camera +++' \
        'curl https://raw.githubusercontent.com/asb/raspi-config/master/raspi-config > /usr/local/sbin/raspi-config' \
        'chown root:root /usr/local/sbin/raspi-config' \
        'chmod 755 /usr/local/sbin/raspi-config' \
        'cp config.txt /boot/config.txt' \
        'echo TODO: download raspistill and raspivid' \
    'echo +++ reboot +++' \
        'shutdown -r -t 30'
do
    set +e
    echo "${command_}" | grep '^echo'
    set -e
    if [ "$?" -ne 0 ];
    then
        echo "${command_}"
    fi

    "${command_}"
done
