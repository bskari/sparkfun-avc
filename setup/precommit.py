"""Precommit script. Run this before commiting to Git."""
import os
import re


def format_kml(xml_lines):
    """Formats a KML document into something that's easily diffable."""
    # TODO: This should probably use an XML parser
    parsing_coordinates = False
    coordinates = []
    return_strings = []
    for line in xml_lines:
        if parsing_coordinates:
            if '</coordinates>' in line:
                parsing_coordinates = False

                coordinates_string = ' '.join(coordinates)
                coordinates_string = re.sub(r'\s+', '\n', coordinates_string)
                coordinates_string = coordinates_string.strip()

                return_strings.append('<coordinates>\n')
                return_strings.append(coordinates_string + '\n')
                return_strings.append('</coordinates>\n')
            else:
                coordinates.append(line)
        else:
            if '<coordinates>' in line:
                parsing_coordinates = True
            else:
                return_strings.append(line)

    return ''.join(return_strings)


def main():
    """Main function."""
    paths_directory = 'paths'
    for file_name in os.listdir(paths_directory):
        if file_name.endswith('.kml'):
            with open(paths_directory + os.sep + file_name) as file_:
                formatted = format_kml(file_)
            with open(paths_directory + os.sep + file_name, 'w') as file_:
                file_.write(formatted)


if __name__ == '__main__':
    main()
