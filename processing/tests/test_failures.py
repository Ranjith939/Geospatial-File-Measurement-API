"""One bad feature should never break the whole file."""

from core.testing import kml

GOOD = "<Placemark><name>{n}</name><LineString><coordinates>77.0,12.0 77.01,12.0</coordinates></LineString></Placemark>"
BAD = "<Placemark><name>bad</name><LineString><coordinates>77.0,abc</coordinates></LineString></Placemark>"


def test_success_invalid_success(measurements):
    f, m = measurements("iso.kml", kml(GOOD.format(n="one") + BAD + GOOD.format(n="three")))
    assert (f["feature_count"], f["successful_count"], f["failed_count"]) == (3, 2, 1)
    assert f["status"] == "completed_with_errors"
    assert m["one"]["status"] == m["three"]["status"] == "success"
    assert m["bad"]["status"] == "failed" and m["bad"]["error_code"] == "INVALID_GEOMETRY"
    assert m["bad"]["feature_id"] == 2


def test_mixed_geometry_sample(measurements):
    f, m = measurements("mixed_geometry.kml")
    assert (f["feature_count"], f["successful_count"], f["failed_count"]) == (7, 4, 3)
    assert m["Well"]["measurement_status"] == "not_required"
    assert m["Bow-tie"]["error_code"] == "INVALID_GEOMETRY" and "Self-intersection" in m["Bow-tie"]["error"]
    assert m["Bow-tie"]["geometry"] is not None  # we still draw it so the user can see what's wrong
    assert m["Broken coords"]["error_code"] == "INVALID_GEOMETRY"
    assert m["Point + Line"]["measurement_status"] == "unsupported" and m["Point + Line"]["status"] == "unsupported"
    assert m["Point + Line"]["error"] == "Measurement not supported for GeometryCollection geometry"
    assert f["totals"]["by_status"] == {"measured": 3, "not_required": 1, "failed": 2, "unsupported": 1}


def test_demo_dataset_198_features(measurements):
    f, m = measurements("land_parcels.zip")
    assert (f["feature_count"], f["successful_count"], f["failed_count"]) == (198, 196, 2)
    assert f["status"] == "completed_with_errors"
    failed = [v for v in m.values() if v["status"] == "failed"]
    assert [v["feature_id"] for v in failed] == [83, 141]  # both failures sit in the middle of the file
    assert {v["properties"]["village"] for v in failed} == {"Disputed"}
    by_id = {v["feature_id"]: v for v in m.values()}
    assert by_id[82]["status"] == by_id[84]["status"] == "success"  # the features next to them are fine
    # every good parcel should match its surveyed area (I drew them exactly in UTM 43N)
    for v in m.values():
        if v["status"] == "success":
            assert abs(v["measurement"]["area_m2"] - v["properties"]["survey_m2"]) < 0.5
