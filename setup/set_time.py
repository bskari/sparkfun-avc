"""Sets the system time."""

from control.sup800f import switch_to_nmea_mode

import serial
import subprocess
import sys
import time
import threading


def main():
    """Main."""
    print('Setting time from SUP800F')
    thread = threading.Thread(target=set_time)
    thread.daemon = True
    thread.start()
    for _ in range(10):
        if not thread.is_alive():
            break
        time.sleep(1)

    if thread.is_alive():
        print('Unable to set time')
    sys.exit(0)


def set_time():
    """Sets the system time from GPS."""
    serial_ = serial.Serial('/dev/ttyAMA0', 115200)
    serial_.setTimeout(1.0)
    for _ in range(10):
        serial_.readline()
    try:
        switch_to_nmea_mode(serial_)
    except:  # pylint: disable=W0702
        print('Unable to set mode')
        sys.exit(1)
    for _ in range(10):
        serial_.readline()

    for _ in range(100):
        line = serial_.readline()
        try:
            line = line.decode('utf-8')
        except:
            raise EnvironmentError('Not a UTF-8 message')

        if line.startswith('$GPRMC'):
            print(line)
            time_str = line.split(',')[1]
            date_str = line.split(',')[9]

            day = int(date_str[0:2])
            month = int(date_str[2:4])
            year = 2000 + int(date_str[4:6])
            hour = int(time_str[0:2])
            minute = int(time_str[2:4])
            second = int(time_str[4:6])

            print(
                '{}-{}-{} {}:{}:{}'.format(
                    year,
                    month,
                    day,
                    hour,
                    minute,
                    second
                )
            )
            subprocess.call([
                'date',
                '--set',
                '{}-{}-{}'.format(year, month, day)
            ])
            subprocess.call([
                'date',
                '--set',
                '{}:{}:{}'.format(hour, minute, second)
            ])
            return

    print('No GPRMC message seen')


if __name__ == '__main__':
    main()
