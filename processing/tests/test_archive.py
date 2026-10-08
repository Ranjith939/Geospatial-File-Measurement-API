"""ZIP handling: nothing hostile is extracted, and only Shapefile components are."""
import io
import zipfile

from core.testing import make_zip


def code(r):
    return r.json()["error"]["code"]


def test_zip_path_traversal_rejected(upload):
    r = upload("evil.zip", make_zip({"../../evil.shp": b"x", "../../evil.shx": b"x", "../../evil.dbf": b"x"}))
    assert r.status_code == 422 and code(r) == "UNSAFE_ARCHIVE"


def test_zip_absolute_path_rejected(upload):
    r = upload("abs.zip", make_zip({"/tmp/a.shp": b"x"}))
    assert r.status_code == 422 and code(r) == "UNSAFE_ARCHIVE"


def test_zip_symlink_rejected(upload):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("link.shp")
        info.external_attr = (0o120777 << 16)
        zf.writestr(info, "/etc/passwd")
    r = upload("link.zip", buf.getvalue())
    assert r.status_code == 422 and code(r) == "UNSAFE_ARCHIVE"


def test_empty_zip(upload):
    r = upload("empty.zip", make_zip({}))
    assert r.status_code == 422 and code(r) == "EMPTY_ARCHIVE"


def test_zip_without_shapefile(upload):
    r = upload("docs.zip", make_zip({"readme.txt": b"hello", "run.exe": b"MZ"}))
    assert r.status_code == 422 and code(r) == "INVALID_SHAPEFILE"


def test_missing_shapefile_component(upload):
    r = upload("invalid_shapefile.zip")  # .shx removed
    assert r.status_code == 422 and code(r) == "INVALID_SHAPEFILE"
    assert r.json()["error"]["details"]["missing"] == {"parcels/parcels": [".shx"]}


def test_only_shapefile_members_are_extracted(upload, settings):
    from core.testing import SAMPLES
    data = make_zip({**{f"s/{n}": b for n, b in _members(SAMPLES / "valid_shapefile.zip").items()},
                     "s/notes.txt": b"x", "s/payload.exe": b"MZ"})
    r = upload("mixed.zip", data)
    assert r.status_code == 201
    names = {c["name"] for c in r.json()["components"]}
    assert "s/payload.exe" not in names and "s/notes.txt" not in names


def _members(path):
    with zipfile.ZipFile(path) as zf:
        return {n.rsplit("/", 1)[-1]: zf.read(n) for n in zf.namelist()}
