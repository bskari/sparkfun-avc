set -u

enabled_debug_console_md5='a51b441bfdde643f237ad2fa77027052'
disabled_debug_console='dwc_otg.lpm_enable=0 console=tty1 root=/dev/mmcblk0p2 rootfstype=ext4 elevator=deadline rootwait'
disabled_debug_console_md5='95c03f60dc74035dc528a6db18425e1d'
cmdline_md5="$(md5sum /boot/cmdline.txt | cut -f 1 -d ' ')"

if [ "${cmdline_md5}" == "${enabled_debug_console_md5}" ];
then
    echo 'Replacing boot cmdline'
    echo "${disabled_debug_console}" > /boot/cmdline.txt
elif [ "${cmdline_md5}" == "${disabled_debug_console_md5}" ];
then
    echo 'boot cmdline already installed'
else
    echo '*** Unknown boot cmdline, no action taken'
fi

getty='T0:23:respawn:/sbin/getty -L ttyAMA0 115200 vt100'
disabled_getty="#${getty}"
grep -q "${disabled_getty}" /etc/inittab
if [ $? -eq 0 ];
then
    echo 'getty already disabled'
else
    grep -q "${getty}" /etc/inittab
    if [ $? -eq 0 ];
    then
        echo 'Disabling getty in inittab'
        sed -i 's/^T0\:23\:respawn\:/#T0\:23\:respawn\:/' /etc/inittab
    else
        echo '*** No getty found, either enabled or disabled'
    fi
fi
