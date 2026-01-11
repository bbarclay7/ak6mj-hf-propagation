"""Geographic utilities for Maidenhead grid squares and distance/bearing calculations."""

import math


def grid_to_latlon(grid: str) -> tuple[float, float] | None:
    """Convert Maidenhead grid to lat/lon (center of grid).

    Args:
        grid: Maidenhead grid square (4 or 6 characters)

    Returns:
        Tuple of (latitude, longitude) or None if invalid
    """
    grid = grid.upper().strip()
    if len(grid) < 4:
        return None

    try:
        lon = (ord(grid[0]) - ord('A')) * 20 - 180
        lat = (ord(grid[1]) - ord('A')) * 10 - 90
        lon += (ord(grid[2]) - ord('0')) * 2
        lat += (ord(grid[3]) - ord('0')) * 1

        if len(grid) >= 6:
            lon += (ord(grid[4].upper()) - ord('A')) * (2/24) + (1/24)
            lat += (ord(grid[5].upper()) - ord('A')) * (1/24) + (1/48)
        else:
            lon += 1  # center of 2-char subsquare
            lat += 0.5

        return lat, lon
    except (IndexError, ValueError):
        return None


def calc_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate bearing from point 1 to point 2 in degrees.

    Args:
        lat1, lon1: Starting point latitude and longitude
        lat2, lon2: Ending point latitude and longitude

    Returns:
        Bearing in degrees (0-360)
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.atan2(x, y)
    return (math.degrees(bearing) + 360) % 360


def calc_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in kilometers.

    Args:
        lat1, lon1: Starting point latitude and longitude
        lat2, lon2: Ending point latitude and longitude

    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def bearing_to_direction(bearing: float) -> str:
    """Convert bearing to compass direction.

    Args:
        bearing: Bearing in degrees (0-360)

    Returns:
        Compass direction (N, NNE, NE, etc.)
    """
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = round(bearing / 22.5) % 16
    return dirs[idx]
