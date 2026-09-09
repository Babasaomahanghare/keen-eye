"""EXIF extraction that never invents missing metadata."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image

GPS_TAG = 34853
TAG_NAMES = {value: key for key, value in ExifTags.TAGS.items()}


def _safe_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Fraction):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    try:
        return str(value)
    except Exception:
        return "<unreadable>"


def _coordinate(value: Any) -> float | None:
    try:
        parts = list(value)
        if len(parts) != 3:
            return None
        return float(parts[0]) + float(parts[1]) / 60 + float(parts[2]) / 3600
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def extract_metadata(path_value: str | Path) -> dict:
    result: dict[str, Any] = {
        "exif_present": False,
        "camera_make": None,
        "camera_model": None,
        "datetime": None,
        "software": None,
        "orientation": None,
        "copyright": None,
        "gps": None,
        "other": {},
    }
    try:
        with Image.open(path_value) as image:
            exif = image.getexif()
            if not exif:
                return result
            result["exif_present"] = True
            named: dict[str, Any] = {}
            for tag_id, value in exif.items():
                name = ExifTags.TAGS.get(tag_id, str(tag_id))
                named[name] = _safe_value(value)
            result["camera_make"] = named.get("Make")
            result["camera_model"] = named.get("Model")
            result["datetime"] = named.get("DateTimeOriginal") or named.get("DateTime")
            result["software"] = named.get("Software")
            result["orientation"] = named.get("Orientation")
            result["copyright"] = named.get("Copyright")
            result["other"] = {
                key: value for key, value in named.items()
                if key not in {"Make", "Model", "DateTimeOriginal", "DateTime",
                               "Software", "Orientation", "Copyright", "GPSInfo"}
            }
            gps_info = exif.get_ifd(GPS_TAG) if GPS_TAG in exif else {}
            if gps_info:
                gps_named = {ExifTags.GPSTAGS.get(k, str(k)): _safe_value(v)
                             for k, v in gps_info.items()}
                lat = _coordinate(gps_named.get("GPSLatitude"))
                lon = _coordinate(gps_named.get("GPSLongitude"))
                lat_ref = gps_named.get("GPSLatitudeRef")
                lon_ref = gps_named.get("GPSLongitudeRef")
                if lat is not None and str(lat_ref).upper().startswith("S"):
                    lat = -lat
                if lon is not None and str(lon_ref).upper().startswith("W"):
                    lon = -lon
                result["gps"] = {
                    "coordinates": {"latitude": lat, "longitude": lon}
                    if lat is not None and lon is not None else None,
                    "raw": gps_named,
                }
    except (OSError, ValueError, KeyError, TypeError):
        # The validated image remains usable; metadata is simply unavailable.
        return result
    return result


def metadata_findings(metadata: dict) -> list[str]:
    findings: list[str] = []
    if metadata.get("gps"):
        findings.append("GPS metadata detected")
    if metadata.get("camera_make") or metadata.get("camera_model"):
        findings.append("Camera/device metadata detected")
    if metadata.get("datetime"):
        findings.append("Capture timestamp metadata detected")
    if metadata.get("software"):
        findings.append("Editing/software metadata detected")
    return findings