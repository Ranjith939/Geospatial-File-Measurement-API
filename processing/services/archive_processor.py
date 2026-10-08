"""Pulls Shapefiles out of a ZIP safely. I only extract shapefile parts and block path traversal, symlinks and zip bombs."""

import shutil
import stat
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath

from django.conf import settings

from core.exceptions import ValidationFailed

REQUIRED = (".shp", ".shx", ".dbf")
ALLOWED = {*REQUIRED, ".prj", ".cpg", ".qix", ".sbn", ".sbx", ".xml"}


def _member_path(info: zipfile.ZipInfo) -> PurePosixPath | None:
    """Gives back a safe relative path for the member, None if we should skip it, or raises if the entry looks hostile."""
    name = info.filename.replace("\\", "/")
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or (p.parts and p.parts[0].endswith(":")):
        raise ValidationFailed("UNSAFE_ARCHIVE", "The archive contains an unsafe path.", {"member": info.filename})
    if stat.S_ISLNK(info.external_attr >> 16):
        raise ValidationFailed("UNSAFE_ARCHIVE", "The archive contains a symbolic link.", {"member": info.filename})
    if info.is_dir() or "__MACOSX" in p.parts or p.name.startswith("."):
        return None
    suffix = ".xml" if name.lower().endswith(".shp.xml") else p.suffix.lower()
    return p if suffix in ALLOWED else None


def extract_shapefiles(zip_path: Path, dest: Path) -> tuple[list[Path], list[str], list[dict]]:
    """Extracts the shapefile sets into `dest` and returns (.shp paths of the complete sets, warnings, components)."""
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        if not any(not i.is_dir() for i in infos):
            raise ValidationFailed("EMPTY_ARCHIVE", "The ZIP archive is empty.")
        if len(infos) > settings.MAX_ARCHIVE_MEMBERS:
            raise ValidationFailed("UNSAFE_ARCHIVE", "The archive contains too many files.")
        if sum(i.file_size for i in infos) > settings.MAX_EXTRACTED_MB * 1024 * 1024:
            raise ValidationFailed("UNSAFE_ARCHIVE", "The archive expands beyond the allowed size.")

        members = [(i, p) for i in infos if (p := _member_path(i)) is not None]
        sets: dict[str, set[str]] = defaultdict(set)
        for _, p in members:
            stem = str(p.with_suffix("")).lower().removesuffix(".shp")  # foo.shp.xml -> foo
            sets[stem].add(p.suffix.lower())

        complete = {s for s, exts in sets.items() if all(e in exts for e in REQUIRED)}
        incomplete = {
            s: [e for e in REQUIRED if e not in exts]
            for s, exts in sets.items()
            if s not in complete and exts & set(REQUIRED)
        }
        if not complete:
            raise ValidationFailed(
                "INVALID_SHAPEFILE",
                "The uploaded ZIP does not contain a valid Shapefile structure.",
                # I added "found" so the user sees what they actually sent, like a GeoJSON zipped by mistake.
                {"expected": list(REQUIRED), "missing": incomplete,
                 "found": [i.filename for i in infos if not i.is_dir() and "__MACOSX" not in i.filename][:20]},
            )

        dest = dest.resolve()
        shp_paths, components = [], []
        for info, p in members:
            target = (dest / p).resolve()
            if not target.is_relative_to(dest):  # _member_path already checks this, I just want a second check
                raise ValidationFailed("UNSAFE_ARCHIVE", "The archive contains an unsafe path.")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
            components.append({"name": str(p), "size": info.file_size})
            if p.suffix.lower() == ".shp" and str(p.with_suffix("")).lower() in complete:
                shp_paths.append(target)

    warnings = [f"Shapefile '{s}' skipped: missing {', '.join(m)}" for s, m in sorted(incomplete.items())]
    return sorted(shp_paths), warnings, components
