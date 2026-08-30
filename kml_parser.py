import xml.etree.ElementTree as ET


def parse_contours_kml(kml_file_path):
    tree = ET.parse(kml_file_path)
    root = tree.getroot()

    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    contours = []

    for placemark in root.iter('{http://www.opengis.net/kml/2.2}Placemark'):
        name_elem = placemark.find('kml:name', ns)
        coords_elem = placemark.find('.//kml:coordinates', ns)

        if name_elem is not None and coords_elem is not None:
            try:
                elevation = float(name_elem.text.strip())
            except (ValueError, TypeError):
                continue

            coords_raw = coords_elem.text.strip().split()
            points = []
            for pt in coords_raw:
                parts = pt.split(',')
                if len(parts) >= 2:
                    lon, lat = float(parts[0]), float(parts[1])
                    points.append((lon, lat))

            if points:
                contours.append({
                    'elevation': elevation,
                    'coordinates': points
                })

    return contours