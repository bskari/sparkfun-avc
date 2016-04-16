"""Formats GPS log messages into a path KMZ file that Google Earth can read."""
#!/bin/env python

from pykml.factory import KML_ElementMaker as KML
import lxml
import sys
import zipfile


def save_points(points, name, kml):
    """Saves the points to a KML object."""
    kml.append(
            KML.Placemark(
                KML.name(name),
                KML.styleUrl('#m_ylw-pushpin'),
                KML.LineString(
                    KML.tessellate(1),
                    KML.coordinates(
                        '\n'.join((
                            '{longitude},{latitude},0 '.format(
                                longitude=longitude,
                                latitude=latitude,
                            ) for latitude, longitude in points
                        ))
                    )
                )
            )
    )


def main(in_stream, file_name):
    """Main function."""
    for line in in_stream:
        if 'Received run command' in line:
            break

    run_count = 1
    running = False

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

    with open('/tmp/out.txt') as file_:
        file_.write(
                lxml.etree.tostring(etree.ElementTree(doc),pretty_print=True)
        )
    with zipfile.ZipFile(file_name, 'w') as kml:
        kml.write('/tmp/out.txt', 'doc.kml', zipfile.ZIP_DEFLATED)


main(sys.stdin, sys.argv[0] or 'path.kmz')
