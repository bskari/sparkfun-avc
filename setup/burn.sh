#!/bin/bash
set -u

if [ "${USER}" != 'root' ];
then
    echo 'Please run as root'
    exit 1
fi

if [ "$#" -ne 2 ];
then
    echo "Usage: $0 <minibian-file.tar.gz> </dev/sdcard>"
    exit 1
fi

echo "$1" | grep 'gz'
if [ "$?" -ne 0 ];
then
    echo 'Not a gzip file, aborting'
    exit 1
fi

echo "$2" | grep '/dev/mmcblk'
if [ "$?" -ne 0 ];
then
    echo 'Possibly invalid SD block device, aborting'
    exit 1
fi

size="$(gzip -l $1 | grep 'tar$' | awk '{print $2}')"

if [ -z "${size}" ];
then
    echo 'Invalid size'
    exit 1
fi

set -e
tar -xOzf $1 | pv -s "${size}" | dd of=$2 bs=1M
