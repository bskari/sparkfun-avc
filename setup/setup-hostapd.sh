set -u
set -e

echo 'Configuring Hostapd'
if [ -f '/tmp/ssid-name.txt' ];
then
    ssid_name="$(cat '/tmp/ssid-name.txt')"
else
    echo 'SSID name? '
    read ssid_name
fi
if [ -z "${ssid_name}" ];
then
    echo 'No SSID name provided, aborting'
    return 1
fi
sed -i "s/ssid_placeholder/${ssid_name}/" /etc/hostapd/hostapd.conf

if [ -f '/tmp/wpa-passphrase.txt' ];
then
    wpa_passphrase="$(cat '/tmp/wpa-passphrase.txt')"
else
    echo 'WPA passphrase? '
    read wpa_passphrase
fi
if [ -z "${wpa_passphrase}" ];
then
    echo 'No passphrase provided, aborting'
    return 1
fi
sed -i "s/passphrase_placeholder/${wpa_passphrase}/" /etc/hostapd/hostapd.conf
