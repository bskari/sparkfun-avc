import collections
import json
import re


placemark_template = '''
		<Placemark>
			<name>{name}</name>
			<styleUrl>#m_ylw-pushpin</styleUrl>
			<LineString>
				<tessellate>1</tessellate>
				<coordinates>
{coordinates}
				</coordinates>
			</LineString>
		</Placemark>
'''


def main():
    with open('out.json') as file_:
        lines = [json.loads(line) for line in file_]
    counter = collections.Counter()
    for line in lines:
        counter[line['useragent']] += 1
    print(json.dumps(counter, sort_keys=True, indent=2))

    def format_placemark(user_agent, entries):
        name = re.search(r'\([^\)]+\)', user_agent)
        if name is None:
            name = 'unknown'
        else:
            name = name.group()[1:-1]

        coordinates = ' '.join(
                (('{},{},0'.format(line['longitude'], line['latitude']) for line in entries))
        )
        print('Saved {} coordinates for {}'.format(len(entries), name))
        return placemark_template.format(name=name, coordinates=coordinates)


    separated_entries = collections.defaultdict(lambda: [])
    for user_agent in counter:
        for line in lines:
            if line['useragent'] == user_agent:
                separated_entries[user_agent].append(line)

    with open('coordinates_template.kml') as template:
        template = ''.join(template.readlines())

    # Parentheses are here to match the regex for user agent extraction
    separated_entries['(all)'] = lines
    placemarks = '\n'.join((
        format_placemark(user_agent, entries)
        for user_agent, entries in separated_entries.items()
    ))
    all_xml = template.format(placemark_template=placemarks)
    with open('out.kml', 'w') as kml:
        kml.write(all_xml)


if __name__ == '__main__':
    main()
