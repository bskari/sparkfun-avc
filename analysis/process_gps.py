"""Formats GPS log messages into a path KMZ file that Google Earth can read."""
#!/bin/env python

import collections
import json
import sys

from plot_points import get_kml


def main():
    """Main function."""
    if len(sys.argv) <= 1:
        print('Usage: {} <log file>'.format(sys.argv[0]))
        return

    in_file_name = sys.argv[1]
    name = in_file_name[:in_file_name.rfind('.')]
    out_file_name = sys.argv[2] if len(sys.argv) > 2 else 'out.kml'
    with open(in_file_name) as in_stream:
        lines = in_stream.readlines()
    runs = process_lines(iter(lines))
    with open(out_file_name, 'w') as out_stream:
        out_stream.write(get_kml(runs, name))


def process_lines(in_stream):
    """I don't know."""
    run_count = 1
    runs = []
    for line in in_stream:
        if 'Received run command' in line:
            print('Starting run {}'.format(run_count))
            runs.append(process_run(in_stream, run_count))
            run_count += 1
    return runs


def process_run(in_stream, run_count):
    """Returns the points in a run."""
    points = collections.defaultdict(lambda: [])
    for line in in_stream:
        if 'Received stop command' in line or 'No waypoints, stopping' in line:
            break
        elif '"device_id"' in line:
            parts = json.loads(line[line.find('{'):line.rfind('}') + 1])
            if 'latitude_d' not in parts:
                # Probably an accelerometer message
                continue
            latitude = parts['latitude_d']
            longitude = parts['longitude_d']
            # Ignore early bad estimates
            if latitude > 1:
                points[parts['device_id']].append((latitude, longitude))
            else:
                print('Ignoring {},{}'.format(latitude, longitude))

    print(
        'Ending run {} with {} paths'.format(
            run_count,
            len(points)
        )
    )
    return points


if __name__ == '__main__':
    main()
