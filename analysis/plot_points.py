"""Writes a KML file of points from stdin."""

import fileinput


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


def build_color_map(runs):
    """Returns the color map for a series of runs.

    runs is:
      [
        {
          'device_id_1': [(lat, long), (lat, long), ...],
          'device_id_2': [(lat, long), (lat, long), ...]
          ...
        },
        {
          'device_id_1': [(lat, long), (lat, long), ...],
          'device_id_2': [(lat, long), (lat, long), ...]
          ...
        },
        ...
    ]
    """

    color_map = {
        # Default the estimate to yellow
        # ABGR
        'estimate': 'ff00ffff'
    }
    # ABGR
    preferred_colors = ['ff0000ff', 'ff00ff00', 'ffff0000', 'ffff00ff', 'ff654321']
    for run in runs:
        for device in run:
            if device in color_map:
                continue

            if len(preferred_colors) > 0:
                color = preferred_colors.pop()
            else:
                color = 'ffaaffff'
            color_map[device] = color
    return color_map


def device_id_to_style_url(device):
    """Maps device id to a style URL."""
    return device[:20].replace(' ', '-')


def get_kml(runs, name):
    """Returns the KML for a series of runs.

    runs is:
      [
        {
          'device_id_1': [(lat, long), (lat, long), ...],
          'device_id_2': [(lat, long), (lat, long), ...]
          ...
        },
        {
          'device_id_1': [(lat, long), (lat, long), ...],
          'device_id_2': [(lat, long), (lat, long), ...]
          ...
        },
        ...
    ]
    """
    folders = ''.join(
        FOLDER_TEMPLATE.format(
            name=str(run_count + 1),
            placemark='\n'.join((
                PLACEMARK_TEMPLATE.format(
                    name=device,
                    coordinates=' '.join((
                        '{longitude},{latitude},0'.format(
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
        for run_count, points in enumerate(runs)
    )

    with open('kml_template.xml') as file_:
        kml_template = file_.read()

    color_map = build_color_map(runs)

    return kml_template.format(
        name=name,
        style_maps='\n'.join((
            STYLE_TEMPLATE.format(
                id=device_id_to_style_url(device),
                scale=1.2,
                color=color
            ) for device, color in color_map.items()
        )),
        folders=''.join(folders),
    )


def main():
    """Read points from stdin."""
    print('Reading points from stdin, formatted as "lat,long" one per line')
    points = []
    for line in fileinput.input():
        latitude, longitude = [float(i) for i in line.split(',')]
        points.append((latitude, longitude))

    runs = [
        {
            'stdin': points
        }
    ]
    with open('stdin.kml', 'w') as out_file:
        out_file.write(get_kml(runs, 'stdin'))


if __name__ == '__main__':
    main()
