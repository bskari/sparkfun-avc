"""Does the rest of the setup."""

import os
import sys
import subprocess


def newer(file_name_1, file_name_2):
    """Returns true if file_1 is newer than file_2."""
    return os.stat(file_name_1).st_atime > os.stat(file_name_2).st_atime


def exists(file_name):
    """Returns true if file exists."""
    return os.access(file_name, os.F_OK)


def main():
    """Does the rest of the setup."""

    section_test_command_tuples = (
        (
            'SSH',
            exists('~/.ssh/sshd_config'),
            (
                'sed -i "s/Port 22/Port 23/" ~/.ssh/sshd_config',
            ),
        ),
        (
            'dotfiles',
            not exists('~/.dotfiles'),
            (
                'cd ~pi',
                'git clone https://github.com/bskari/dotfiles .dotfiles',
                'pushd .dotfiles',
                'bash setup.sh',
                'popd',
            ),
        ),
        (
            'network',
            newer('interfaces', '/etc/network/interfaces'),
            (
                'cp interfaces /etc/network/interfaces',
                'ifdown wlan0',
                'ifup wlan0',
            )
        ),
        (
            'hostapd',
            not subprocess.check_output(
                ('md5sum', '/usr/sbin/hostapd')
            ).startswith('1c188ad3'),
            (
                'cp hostapd /etc/default/hostapd',
                'cp hostapd.conf /etc/hostapd/hostapd.conf',
                'wget http://dl.dropbox.com/u/1663660/hostapd/hostapd -O - > /usr/sbin/hostapd',
                'chown root:root /usr/sbin/hostapd',
                'chmod 755 /usr/sbin/hostapd',
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
            not exists('~/.virtualenvs/sparkfun'),
            (
                'pushd ~/sparkfun-avc/control',
                'su -c "mkvirtualenv sparkfun -p /usr/bin/python3" pi',
                'su -c "pip install -r requirements.txt" pi',
                'su -c "deactivate" pi',
                'popd',
                'pushd ~/sparkfun-avc/setup',
                'make rooter',
                'chown root:root rooter',
                'chmod +s rooter',
                'popd',
            ),
        ),
        (
            'Start up',
            not exists('/etc/init.d/sparkfun-rc'),
            (
                'cp sparkfun-rc /etc/init.d/',
                'update-rc.d sparkdun-rc defaults',
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
