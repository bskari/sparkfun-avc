"""Does the rest of the setup."""

import os
import subprocess
import sys


def newer(file_name_1, file_name_2):
    """Returns true if file_1 is newer than file_2."""
    return os.stat(file_name_1).st_atime > os.stat(file_name_2).st_mtime


def exists(file_name):
    """Returns true if file exists."""
    return os.access(file_name, os.F_OK)


def main():
    """Does the rest of the setup."""

    section_test_command_tuples = (
        (
            'SSH',
            newer('sshd_config', '/etc/ssh/sshd_config'),
            (
                'cp sshd_config /etc/ssh/sshd_config',
                'service ssh restart',
            )
        ),
        (
            'dotfiles',
            not exists('/home/pi/.dotfiles'),
            (
                'bash setup-dotfiles.sh',
            )
        ),
        (
            'bash_profile',
            not exists('/home/pi/.bash_profile') or newer('bash_profile', '/home/pi/.bash_profile'),
            (
                'cp bash_profile /home/pi/.bash_profile',
            )
        ),
        (
            'network',
            newer('interfaces', '/etc/network/interfaces') or newer('resolv.conf', '/etc/resolv.conf'),
            (
                'cp interfaces /etc/network/interfaces',
                'cp resolv.conf /etc/resolv.conf',
                'ifdown wlan0',
                'ifup wlan0',
            )
        ),
        (
            'hostapd binary',
            not subprocess.check_output(
                ('md5sum', '/usr/sbin/hostapd')
            ).decode('utf-8').startswith('a18c754b6edbbcb65cbcd48692704c0b'),
            (
                'wget http://dl.dropboxusercontent.com/u/1663660/hostapd/hostapd -O /usr/sbin/hostapd',
                'chown root:root /usr/sbin/hostapd',
                'chmod 755 /usr/sbin/hostapd',
                'service hostapd restart',
            )
        ),
        (
            'hostapd.conf',
            not exists('/etc/hostapd/hostapd.conf') or newer('hostapd.conf', '/etc/hostapd/hostapd.conf') or newer('hostapd', '/etc/default/hostapd'),
            (
                'cp hostapd /etc/default/hostapd',
                'cp hostapd.conf /etc/hostapd/hostapd.conf',
                'bash setup-hostapd.sh',
                'service hostapd restart',
            )
        ),
        (
            'dnsmasq',
            newer('dnsmasq.conf', '/etc/dnsmasq.conf'),
            (
                'cp dnsmasq.conf /etc/dnsmasq.conf',
                'service dnsmasq restart',
            )
        ),
        (
            'fstab',
            newer('fstab', '/etc/fstab'),
            (
                'cp fstab /etc/fstab',
            )
            # TODO: Something about setting the Tmux directory to /tmp
        ),
        (
            'remount scripts',
            not exists('/usr/sbin/ipe-ro'),
            (
                'cp ipe-ro /usr/sbin/',
                'cp ipe-rw /usr/sbin/',
            )
        ),
        (
            'Sparkfun AVC control',
            not exists('/home/pi/.virtualenvs/sparkfun'),
            (
                'bash setup-virtualenv.sh',
            )
        ),
        (
            'Rust',
            not exists('/home/pi/rust') or not exists('/home/pi/cargo'),
            (
                'bash setup-rust.sh',
            )
        ),
        (
            'start up',
            not exists('/etc/init.d/sparkfun-rc') or newer('sparkfun-rc', '/etc/init.d/sparkfun-rc'),
            (
                'cp sparkfun-rc /etc/init.d/',
                'update-rc.d sparkfun-rc defaults',
            )
        ),
        (
            'set up GPS',
            True,
            (
                'bash setup-gps.sh',
            )
        ),
        (
            'set up Pi Blaster',
            not exists('/dev/pi-blaster'),
            (
                'bash setup-pi-blaster.sh',
            )
        ),
    )

    for section, test, commands in section_test_command_tuples:
        if test:
            print('+++ Running section {section}'.format(section=section))
            for command in commands:
                print(command)
                return_code = subprocess.call(command.split(' '))
                if return_code != 0:
                    print(
                        'Command failed with code {code}, aborting'.format(
                            code=return_code
                        )
                    )
                    sys.exit(return_code)
        else:
            print('Skipping section {section}'.format(section=section))


if __name__ == '__main__':
    main()
