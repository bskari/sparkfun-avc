#!/bin/bash
# Prepares a fresh installation of an SD card for the Sparkfun AVC. This should
# be safe to run multiple times.

# First, download Raspbian net install and burn it to an SD card:
#   wget https://dl.dropbox.com/u/45842273/2012-07-15-wheezy-raspian-minimal.img.7z
#   7x z 2012-07-15-wheezy-raspian-minimal.img.7z
#   dd if=2012-07-15-wheezy-raspian-minimal.img of=/dev/sdb bs=1M
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

echo 'Want to update the firmware? (y/n) '
read firmware
if [ "${firmware}" == 'y' ];
then
    apt-get install curl  # Curl is needed for the rpi-update script
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
