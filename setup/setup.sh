#!/bin/bash
# Prepares a fresh installation of an SD card for the Sparkfun AVC. This should
# be safe to run multiple times.

# First, download Minibian and burn it to an SD card:
#   wget http://sourceforge.net/projects/minibian/files/2014-11-24-wheezy-minibian.tar.gz/download -o minibian.tar.gz
#   tar -xvzf minibian.tar.gz
#   dd if=*minibian*img of=/dev/sdb bs=1M
# Install git and clone the repo:
#   (root password is raspberry)
#   apt-get update
#   apt-get install git
#   git clone git@www.skari.org:sparkfun-avc
# Run this file!

set -u
set -e

if [ "${USER}" != 'root' ];
then
    echo 'You must be root'
    exit 1
fi

echo -n 'Want to update the firmware? (y/n) '
read firmware
if [ "${firmware}" == 'y' ];
then
    apt-get install curl  # Curl is needed for the rpi-update script
    apt-get install binutils # readelf is needed for the rpi-update script
    curl https://raw.githubusercontent.com/Hexxeh/rpi-update/master/rpi-update > /usr/bin/rpi-update
    chmod +x /usr/bin/rpi-update
    rpi-update
    reboot
    exit 0
fi

apt-get update
apt-get install -y libparted0debian1 parted lua5.1 triggerhappy
if [ ! -f 'raspi-config_20140902-1_all.deb' ];
then
    wget http://archive.raspberrypi.org/debian/pool/main/r/raspi-config/raspi-config_20140902-1_all.deb
    dpkg -i raspi-config_20140902-1_all.deb
fi
echo 'Get ready to expand the root FS and enable the camera (press enter)'
read
raspi-config  # Expand the root FS, enable the camera

echo -n 'Password for user pi? '
read password
echo "pi:${password}" | chpasswd

apt-get upgrade
# TODO: Install raspistill and raspivid? We could use the picamera Python library
# TODO: What about gstreamer?
apt-get install -y \
    ack-grep \
    dnsmasq \
    gcc \
    gpsd \
    hostapd \
    iw \
    libraspberrypi-bin \
    mpg123 \
    openssh-server \
    python-virtualenv \
    python3 \
    python3-dev \
    python3-pip \
    tmux \
    vim \

# Hell with bash, let's do the rest of this in Python
python3 setup.py
