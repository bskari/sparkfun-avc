#!/bin/bash
set -u

if [ "${USER}" != 'root' ];
then
    echo 'Please run as root'
    exit 1
fi

if [ "$#" -ne 2 ];
then
    echo "Usage: $0 <minibian-file.tgz.zip.img> </dev/sdcard>"
    exit 1
fi

deflate=''
if [ -n "$(echo $1 | grep -P 'gz$')" ];
then
    if [ -n "$(echo $1 | grep -P '(tgz|tar.gz)$')" ];
    then
        deflate='tar -xOzf'
        size="$(gzip -l $1 | grep 'tar$' | awk '{print $2}')"
    else
        deflate='gzip -c'
        size="$(gzip -l $1 | grep 'img$' | awk '{print $2}')"
    fi
elif [ -n "$(echo $1 | grep -P 'zip$')" ];
then
    deflate='unzip -c'
    size="$(unzip -l $1 | grep 'img$' | awk '{print $1}')"
elif [ -n "$(echo $1 | grep -P 'img$')" ];
then
    deflate='cat'
    size=$(ls -l | awk '{print $5}')
else
    echo 'Invalid file format?'
    exit 1
fi

echo "$2" | grep '/dev/mmcblk'
if [ "$?" -ne 0 ];
then
    echo 'Possibly invalid SD block device, aborting'
    exit 1
fi

if [ -z "${size}" ];
then
    echo 'Invalid size'
    exit 1
fi

set -e
echo "Running $deflate $1 | pv -s ${size} | dd of=$2 bs=1M"
for i in $(seq 10 -1 1);
do
    echo $i
    sleep 1
done
$deflate $1 | pv -s "${size}" | dd of=$2 bs=1M
