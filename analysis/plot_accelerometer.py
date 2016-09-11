"""Plots the accelerometer readings for x, y, and z."""

from dateutil import parser as dateparser
from matplotlib import pyplot
import json
import sys



def main():
    if sys.version_info.major <= 2:
        print('Please use Python 3')
        sys.exit(1)
    if len(sys.argv) != 2:
        print('Usage: plot_accelerometer.py <log file>')
        sys.exit(1)

    with open(sys.argv[1]) as file_:
        lines = file_.readlines()

    first_stamp = timestamp(lines[0])
    acceleration_g_x = []
    acceleration_g_y = []
    acceleration_g_z = []
    acceleration_times = []
    not_moving_times = []
    run_times = []
    stop_times = []

    for line in lines:
        if 'acceleration_g_x' in line:
            data = json.loads(line[line.find('{'):])
            acceleration_g_x.append(data['acceleration_g_x'])
            acceleration_g_y.append(data['acceleration_g_y'])
            acceleration_g_z.append(data['acceleration_g_z'])
            acceleration_times.append(timestamp(line) - first_stamp)
        elif 'not moving according' in line:
            not_moving_times.append(timestamp(line) - first_stamp)
        elif 'Received run command' in line:
            run_times.append(timestamp(line) - first_stamp)
        elif 'Received stop command' in line or 'No waypoints, stopping' in line:
            stop_times.append(timestamp(line) - first_stamp)

    pyplot.plot(acceleration_times, acceleration_g_x)
    pyplot.scatter(not_moving_times, [0.25] * len(not_moving_times), color='blue')
    pyplot.scatter(run_times, [0.3] * len(run_times), color='green')
    pyplot.scatter(stop_times, [0.35] * len(stop_times), color='red')
    pyplot.draw()
    pyplot.show()

    pyplot.plot(acceleration_times, acceleration_g_y)
    pyplot.scatter(not_moving_times, [-0.25] * len(not_moving_times), color='blue')
    pyplot.scatter(run_times, [-0.3] * len(run_times), color='green')
    pyplot.scatter(stop_times, [-0.35] * len(stop_times), color='red')
    pyplot.draw()
    pyplot.show()

    pyplot.plot(acceleration_times, acceleration_g_z)
    pyplot.scatter(not_moving_times, [-0.75] * len(not_moving_times), color='blue')
    pyplot.scatter(run_times, [-0.7] * len(run_times), color='green')
    pyplot.scatter(stop_times, [-0.65] * len(stop_times), color='red')
    pyplot.draw()
    pyplot.show()

    pyplot.plot(acceleration_times, acceleration_g_x)
    pyplot.plot(acceleration_times, [i + 0.05 for i in acceleration_g_y])
    pyplot.plot(acceleration_times, [i - 0.93 for i in acceleration_g_z])
    pyplot.scatter(not_moving_times, [0.25] * len(not_moving_times), color='blue')
    pyplot.scatter(run_times, [0.3] * len(run_times), color='green')
    pyplot.scatter(stop_times, [0.35] * len(stop_times), color='red')
    pyplot.draw()
    pyplot.show()



def timestamp(line):
    """Returns the timestamp of a log line."""
    dt = dateparser.parse(line[:line.find(',')])
    comma = line.find(',')
    millis = float(line[comma + 1:line.find(':', comma)])
    return dt.timestamp() + millis / 1000.

if __name__ == '__main__':
    main()
