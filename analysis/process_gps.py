"""Formats GPS log messages into a path KMZ file that Google Earth can read."""
#!/bin/env python

import collections
import json
import sys


KML_TEMPLATE = None
COLOR_MAP = {
    # Default the estimate to yellow
    # ABGR
    'estimate': 'ff00ffff'
}

PLACEMARK_TEMPLATE = '''<Placemark>
    <name>{name}</name>
    <styleUrl>{style_url}</styleUrl>
    <LineString>
            <tessellate>1</tessellate>
            <coordinates>
                {coordinates}
        </coordinates>
    </LineString>
</Placemark>
'''

STYLE_TEMPLATE = '''<StyleMap id="m{id}">
        <Pair>
                <key>normal</key>
                <styleUrl>#{id}0</styleUrl>
        </Pair>
        <Pair>
                <key>highlight</key>
                <styleUrl>#{id}1</styleUrl>
        </Pair>
</StyleMap>
<Style id="{id}0">
        <IconStyle>
                <scale>{scale}</scale>
        </IconStyle>
        <LineStyle>
                <color>{color}</color>
                <width>1</width>
        </LineStyle>
</Style>
<Style id="{id}1">
        <LineStyle>
                <color>{color}</color>
                <width>1</width>
        </LineStyle>
</Style>'''

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
    name = in_file_name[:in_file_name.rfind('.')]
    out_file_name = sys.argv[2] if len(sys.argv) > 2 else 'out.kml'
    with open(in_file_name) as in_stream:
        build_color_map(in_stream)
    with open(in_file_name) as in_stream:
        with open(out_file_name, 'w') as out_stream:
            process_streams(in_stream, out_stream, name)


def build_color_map(in_stream):
    global COLOR_MAP
    # ABGR
    preferred_colors = ['ff0000ff', 'ff00ff00', 'ffff0000']
    for line in in_stream:
        if '"device_id"' in line:
            parts = json.loads(line[line.find('{'):line.rfind('}') + 1])
            device = device_id_to_style_url(parts['device_id'])
            if device in COLOR_MAP:
                continue

            if len(preferred_colors) > 0:
                color = preferred_colors.pop()
            else:
                color = 'ffaaffff'
            COLOR_MAP[device] = color


def process_streams(in_stream, out_stream, name):
    run_count = 1
    runs = []
    for line in in_stream:
        if 'Received run command' in line:
            print('Starting run {}'.format(run_count))
            runs.append(process_run(in_stream, name, run_count))
            run_count += 1

    out_stream.write(
        KML_TEMPLATE.format(
            name=name,
            style_maps='\n'.join((
                STYLE_TEMPLATE.format(
                    id=device_id_to_style_url(device),
                    scale=1.2,
                    color=color
                ) for device, color in COLOR_MAP.items()
            )),
            folders=''.join(runs),
        )
    )


def process_run(in_stream, name, run_count):
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
                points[parts['device_id']].append((longitude, latitude))
            else:
                print('Ignoring {},{}'.format(latitude, longitude))

    print(
        'Ending run {} with {} paths'.format(
            run_count,
            len(points)
        )
    )

    return FOLDER_TEMPLATE.format(
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
                )),
                style_url='#m{id}'.format(id=device_id_to_style_url(device)),
            )
            for device in points
        ))
    )


def device_id_to_style_url(device):
    return device[:20].replace(' ', '-')


if __name__ == '__main__':
    main()
