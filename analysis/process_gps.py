"""Formats GPS log messages into a path KMZ file that Google Earth can read."""
#!/bin/env python

import collections
import json
import sys


KML_TEMPLATE = None

PLACEMARK_TEMPLATE = '''<Placemark>
    <name>{name}</name>
    <LineString>
            <tessellate>1</tessellate>
            <coordinates>
                {coordinates}
        </coordinates>
    </LineString>
</Placemark>
'''

FOLDER_TEMPLATE = '''<Folder>
    <name>{name}</name>
    {placemark}
</Folder>
'''


def main():
    """Main function."""
    if len(sys.argv) <= 1:
        print('Usage: {} <log file>'.format(sys.argv[0]))
        return

    global KML_TEMPLATE
    with open('kml_template.xml') as file_:
        KML_TEMPLATE = file_.read()

    in_file_name = sys.argv[1]
    date = in_file_name[in_file_name.find('-') + 1:in_file_name.rfind('.')]
    out_file_name = sys.argv[2] if len(sys.argv) > 2 else 'out.kml'
    with open(in_file_name) as in_stream:
        with open(out_file_name, 'w') as out_stream:
            process_streams(in_stream, out_stream, date)


def process_streams(in_stream, out_stream, name):
    run_count = 0
    for line in in_stream:
        if 'Received run command' in line:
            print('Starting run {}'.format(run_count))
            run_count += 1
            process_run(in_stream, out_stream, name, run_count)


def process_run(in_stream, out_stream, name, run_count):
    points = collections.defaultdict(lambda: [])
    for line in in_stream:
        if 'Received stop command' in line or 'No waypoints, stopping' in line:
            break
        elif '"device_id"' in line:
            parts = json.loads(line[line.find('{'):line.rfind('}') + 1])
            latitude = parts['latitude_d']
            longitude = parts['longitude_d']
            # Ignore early bad estimates
            if latitude > 1:
                points[parts['device_id']].append((longitude, latitude))
            else:
                print('Ignoring {},{}'.format(latitude, longitude))

    print(
        'Ending run {} with {} paths'.format(
            run_count,
            len(points)
        )
    )

    out_stream.write(
        KML_TEMPLATE.format(
            name=name,
            folders=FOLDER_TEMPLATE.format(
                name=str(run_count),
                placemark='\n'.join((
                    PLACEMARK_TEMPLATE.format(
                        name=device,
                        coordinates=' '.join((
                            '{latitude},{longitude},0'.format(
                                latitude=point[0],
                                longitude=point[1]
                            )
                            for point in points[device]
                        ))
                    )
                    for device in points
                ))
            )
        )
    )


if __name__ == '__main__':
    main()
