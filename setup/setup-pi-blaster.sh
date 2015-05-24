#!/bin/bash

set -u
set -e

if [ -e /dev/pi-blaster ];
then
    exit 0
fi

cd /tmp
git clone https://github.com/sarfata/pi-blaster
cd pi-blaster
./autogen.sh
./configure
make
sudo apt-get install autoconf
sudo make install
