import mimetypes
import uuid
from io import BytesIO

from django.core.files.uploadedfile import UploadedFile
from django.http import FileResponse
from ninja.errors import HttpError
from PIL import Image, UnidentifiedImageError

IMAGE_TYPES = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp'}
MAX_IMAGE_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def inspect_image(f: UploadedFile, *, max_bytes: int = 25 * 1024 * 1024) -> tuple[int, int, str]:
    """Sprawdza, czy plik jest obrazem; zwraca (szerokość, wysokość, rozszerzenie)."""
    if f.size and f.size > max_bytes:
        raise HttpError(413, f'Plik jest za duży (maks. {max_bytes // 1024 // 1024} MB).')
    try:
        data = f.read()
        f.seek(0)
        with Image.open(BytesIO(data)) as im:
            im.verify()
        with Image.open(BytesIO(data)) as im:
            w, h = im.size
            fmt = (im.format or '').lower()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise HttpError(400, 'Plik nie jest poprawnym obrazem.') from exc
    ext = {'jpeg': 'jpg', 'png': 'png', 'webp': 'webp'}.get(fmt)
    if not ext:
        raise HttpError(400, 'Dozwolone formaty: JPG, PNG, WEBP.')
    return w, h, ext


def new_name(ext: str) -> str:
    return f'{uuid.uuid4().hex}.{ext}'


def serve(field, filename: str | None = None, as_attachment: bool = False) -> FileResponse:
    if not field:
        raise HttpError(404, 'Brak pliku.')
    ctype = mimetypes.guess_type(field.name)[0] or 'application/octet-stream'
    resp = FileResponse(field.open('rb'), content_type=ctype, as_attachment=as_attachment, filename=filename or None)
    resp['Cache-Control'] = 'private, max-age=86400'
    return resp
