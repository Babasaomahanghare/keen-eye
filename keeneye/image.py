"""Safe local image validation and file profiling."""

from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .errors import ImageValidationError

SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF", "BMP"}
MAX_IMAGE_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class ImageProfile:
    path: str
    filename: str
    format: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    sha256: str
    md5: str

    def to_dict(self) -> dict:
        return asdict(self)


def _hash_file(path: Path) -> tuple[str, str]:
    sha = hashlib.sha256()
    md5 = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
            md5.update(chunk)
    return sha.hexdigest(), md5.hexdigest()


def validate_image(path_value: str | Path, max_bytes: int = MAX_IMAGE_BYTES) -> ImageProfile:
    path = Path(path_value).expanduser()
    if not path.exists():
        raise ImageValidationError(
            "The image path does not exist.",
            f"KEEN EYE could not find {path}.",
            "Check the path and try again.",
        )
    if not path.is_file():
        raise ImageValidationError(
            "The supplied path is not a file.",
            f"{path} points to a directory or special filesystem entry.",
            "Provide a readable image file.",
        )
    if not path.stat().st_mode & 0o444:
        raise ImageValidationError(
            "The image is not readable.",
            "The current user does not have read permission.",
            f"Adjust permissions for {path} or choose another file.",
        )
    size = path.stat().st_size
    if size > max_bytes:
        raise ImageValidationError(
            "The image is too large.",
            f"The file is {size / 1024 / 1024:.1f} MiB; the limit is {max_bytes / 1024 / 1024:.0f} MiB.",
            "Resize or compress the image, then retry.",
        )
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image_format = (image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageValidationError(
            "KEEN EYE could not process this file.",
            "The file is not a readable supported image or may be corrupted.",
            "Try a valid JPEG or PNG image.",
        ) from exc
    if image_format not in SUPPORTED_FORMATS:
        raise ImageValidationError(
            "The image format is not supported.",
            f"Detected format: {image_format or 'unknown'}.",
            "Use JPEG, PNG, WEBP, GIF, or BMP.",
        )
    sha256, md5 = _hash_file(path)
    mime = Image.MIME.get(image_format) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return ImageProfile(
        path=str(path.resolve()),
        filename=path.name,
        format=image_format,
        mime_type=mime,
        size_bytes=size,
        width=width,
        height=height,
        sha256=sha256,
        md5=md5,
    )