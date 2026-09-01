import os
import zipfile
import xml.etree.ElementTree as ET
import re


def _extract_kml_from_kmz(file_path):
    """If the file is a KMZ archive, returns the KML content as bytes, else None."""
    if zipfile.is_zipfile(file_path):
        with zipfile.ZipFile(file_path, 'r') as z:
            for name in z.namelist():
                if name.lower().endswith('.kml'):
                    return z.read(name)
    return None


def _find_elevation(placemark, points_with_z=None):
    """Attempts to find elevation from name, ExtendedData, description, or 3D coordinate z-values."""
    # 1. Check <name>
    for child in placemark:
        if child.tag.endswith('name') and child.text:
            text = child.text.strip()
            try:
                return float(text)
            except ValueError:
                match = re.search(r"[-+]?\d*\.?\d+", text)
                if match:
                    try:
                        return float(match.group())
                    except ValueError:
                        pass

    # 2. Check ExtendedData / SimpleData
    for elem in placemark.iter():
        if elem.tag.endswith('SimpleData') or elem.tag.endswith('Data'):
            name_attr = elem.attrib.get('name', '').lower()
            if any(k in name_attr for k in ['elev', 'contour', 'height', 'z', 'level']):
                if elem.text:
                    try:
                        return float(elem.text.strip())
                    except ValueError:
                        pass

    # 3. Check 3D coordinate z-value if available
    if points_with_z:
        z_vals = [pt[2] for pt in points_with_z if len(pt) >= 3 and pt[2] is not None]
        if z_vals:
            return float(sum(z_vals) / len(z_vals))

    # 4. Check description
    for child in placemark:
        if child.tag.endswith('description') and child.text:
            match = re.search(r"(?:elevation|elev|height|contour)\s*[:=]?\s*([-+]?\d*\.?\d+)", child.text, re.I)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass

    return None


def parse_contours_kml(kml_file_path):
    kmz_data = _extract_kml_from_kmz(kml_file_path)
    if kmz_data:
        root = ET.fromstring(kmz_data)
    else:
        tree = ET.parse(kml_file_path)
        root = tree.getroot()

    contours = []

    for placemark in root.iter():
        if not placemark.tag.endswith('Placemark'):
            continue

        coords_elem = None
        for elem in placemark.iter():
            if elem.tag.endswith('coordinates'):
                coords_elem = elem
                break

        if coords_elem is None or not coords_elem.text:
            continue

        coords_raw = coords_elem.text.strip().split()
        points = []
        points_3d = []
        for pt in coords_raw:
            parts = pt.split(',')
            if len(parts) >= 2:
                try:
                    lon, lat = float(parts[0]), float(parts[1])
                    z_val = float(parts[2]) if len(parts) >= 3 else None
                    points.append((lon, lat))
                    points_3d.append((lon, lat, z_val))
                except ValueError:
                    continue

        if not points:
            continue

        elevation = _find_elevation(placemark, points_3d)
        if elevation is not None:
            contours.append({
                'elevation': elevation,
                'coordinates': points
            })

    return contours