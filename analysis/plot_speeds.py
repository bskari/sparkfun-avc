"""Plots the speed readings."""

#from dateutil import parser as dateparser
from matplotlib import pyplot
import collections
import datetime
import json
import sys



def main():
    """Main function."""
    if sys.version_info.major <= 2:
        print('Please use Python 3')
        sys.exit(1)
    if len(sys.argv) != 2:
        print('Usage: {} <log file>'.format(sys.argv[0]))
        sys.exit(1)

    with open(sys.argv[1]) as file_:
        lines = file_.readlines()

    first_stamp = timestamp(lines[0])
    speeds = collections.defaultdict(lambda: [])
    times = collections.defaultdict(lambda: [])
    acceleration_times = []
    not_moving_times = []
    run_times = []
    stop_times = []

    for line in lines:
        if 'speed_m_s' in line:
            data = json.loads(line[line.find('{'):])
            speeds[data['device_id']].append(data['speed_m_s'])
            times[data['device_id']].append(timestamp(line) - first_stamp)
        elif 'not moving according' in line:
            not_moving_times.append(timestamp(line) - first_stamp)
        elif 'Received run command' in line:
            run_times.append(timestamp(line) - first_stamp)
        elif 'Received stop command' in line or 'No waypoints, stopping' in line:
            stop_times.append(timestamp(line) - first_stamp)

    for device, speeds in speeds.items():
        pyplot.scatter(times[device], speeds)
        pyplot.scatter(not_moving_times, [0.25] * len(not_moving_times), marker='x', color='blue')
        pyplot.scatter(run_times, [0.3] * len(run_times), marker='x', color='green')
        pyplot.scatter(stop_times, [0.35] * len(stop_times), marker='x', color='red')
        pyplot.title(device)
        pyplot.draw()
        pyplot.show()


def timestamp(line):
    """Returns the timestamp of a log line."""
    # 2016-08-22 09:57:28,343
    year = int(line[0:4])
    month = int(line[5:7])
    day = int(line[8:10])
    hour = int(line[11:13])
    minute = int(line[14:16])
    seconds = int(line[17:19])
    comma = line.find(',')
    millis = float(line[comma + 1:line.find(':', comma)])
    dt = datetime.datetime(year, month, day, hour, minute, seconds)
    return dt.timestamp() + millis / 1000.

if __name__ == '__main__':
    main()
