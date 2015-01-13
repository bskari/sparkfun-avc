set -u
set -e

echo 'SSID name? '
read ssid_name
if [ -z "${ssid_name}" ];
then
    echo 'No SSID name provided, aborting'
    return 1
fi
sed -i "s/ssid_placeholder/${ssid_name}/" /etc/hostapd/hostapd.conf

echo 'WPA passphrase? '
read wpa_passphrase
if [ -z "${wpa_passphrase}" ];
then
    echo 'No passphrase provided, aborting'
    return 1
fi
sed -i "s/passphrase_placeholder/${wpa_passphrase}/" /etc/hostapd/hostapd.conf
