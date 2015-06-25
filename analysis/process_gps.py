"""Formats GPS log messages into a path KMZ file that Google Earth can read."""
#!/bin/env python

import sys
import zipfile


def write_header(out_stream):
    """Writes the KML header."""
    out_stream.write('''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"
    xmlns:gx="http://www.google.com/kml/ext/2.2"
    xmlns:kml="http://www.opengis.net/kml/2.2"
    xmlns:atom="http://www.w3.org/2005/Atom">
<Document>
    <name>paths.kmz</name>
    <Style id="s_ylw-pushpin">
            <IconStyle>
                    <scale>1.1</scale>
                    <Icon>
                            <href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>
                    </Icon>
                    <hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
            </IconStyle>
    </Style>
    <StyleMap id="m_ylw-pushpin">
            <Pair>
                    <key>normal</key>
                    <styleUrl>#s_ylw-pushpin</styleUrl>
            </Pair>
            <Pair>
                    <key>highlight</key>
                    <styleUrl>#s_ylw-pushpin_hl</styleUrl>
            </Pair>
    </StyleMap>
    <Style id="s_ylw-pushpin_hl">
            <IconStyle>
                    <scale>1.3</scale>
                    <Icon>
                            <href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>
                    </Icon>
                    <hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
            </IconStyle>
    </Style>
''')


def write_footer(out_stream):
    """Writes the KML footer."""
    out_stream.write('''
</Document>
</kml>
    ''')


def save_points(points, name, out_stream):
    """Saves the points to a stream."""
    out_stream.write('''
        <Placemark>
            <name>{name}</name>
            <styleUrl>#m_ylw-pushpin</styleUrl>
            <LineString>
                <tessellate>1</tessellate>
                <coordinates>
    '''.format(
        name=name
    ))
    previous = None
    for point in points:
        if point == previous:
            continue
        previous = point
        (latitude, longitude) = point
        if (
                latitude < 35
                or latitude > 45
                or longitude < -110
                or longitude > -100
        ):
            print(
                'Ignoring bad point: {}, {}'.format(
                    latitude,
                    longitude,
                )
            )
            continue
        previous = (latitude, longitude)
        out_stream.write(
            '{longitude},{latitude},0 '.format(
                longitude=longitude,
                latitude=latitude,
            )
        )
    out_stream.write('''
            </coordinates>
        </LineString>
    </Placemark>
    ''')


def main(in_stream):
    """Main function."""
    for line in in_stream:
        if 'Received run command' in line:
            break

    run_count = 1
    running = False
    with open('/tmp/out.txt', 'w') as file_:
        write_header(file_)

        points = []
        for line in in_stream:
            if not running and 'Received run command' in line:
                print('Starting run {}'.format(run_count))
                running = True
            elif running and (
                    'Received stop command' in line
                    or 'No waypoints, stopping' in line
            ):
                print(
                    'Ending run {} with {} points'.format(
                        run_count,
                        len(points)
                    )
                )
                running = False
                save_points(points, 'run-{}'.format(run_count), file_)
                points = []
                run_count += 1
            elif running and 'lat: ' in line:
                parts = line.split(' ')
                latitude = float(parts[3].split(',')[0])
                longitude = float(parts[5].split(',')[0])
                points.append((latitude, longitude))

        write_footer(file_)

    with zipfile.ZipFile('path.kml', 'w') as kml:
        kml.write('/tmp/out.txt', 'doc.kml', zipfile.ZIP_DEFLATED)


main(sys.stdin)
