def test_upload_then_retrieve(client, upload):
    r = upload("polygon.kml")
    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == "polygon.kml" and body["status"] == "completed"
    assert [s["stage"] for s in body["stages"]] == [
        "validating", "extracting", "parsing", "detecting_crs", "validating_geometry", "selecting_crs",
        "transforming", "measuring", "storing"]
    assert body["crs"] == "EPSG:4326" and body["file_type"] == "KML"
    assert body["stages"][1]["status"] == "skipped"  # nothing to extract for KML
    assert "stored_filename" not in body

    info = client.get(f"/api/files/{body['id']}/")
    assert info.status_code == 200 and info.json()["feature_count"] == 2
    lon0, lat0, lon1, lat1 = info.json()["bounds"]
    assert 77 < lon0 < lon1 < 78 and 12 < lat0 < lat1 < 13

    m = client.get(f"/api/files/{body['id']}/measurements/")
    assert m.status_code == 200
    first = m.json()["features"][0]
    assert first["feature_id"] == 1 and first["geometry"]["type"] == "Polygon"
    assert (first["measurement_type"], first["unit"], first["status"]) == ("area", "m²", "success")
    assert first["source_crs"] == "EPSG:4326" and first["measurement_crs"] == "EPSG:32643"


def test_measurements_filters(client, upload):
    fid = upload("mixed_geometry.kml").json()["id"]
    failed = client.get(f"/api/files/{fid}/measurements/?status=failed").json()["features"]
    assert len(failed) == 2 and all(x["status"] == "failed" for x in failed)
    unsupported = client.get(f"/api/files/{fid}/measurements/?status=unsupported").json()["features"]
    assert len(unsupported) == 1
    slim = client.get(f"/api/files/{fid}/measurements/?include_geometry=false").json()["features"]
    assert all(x["geometry"] is None for x in slim)
    assert client.get(f"/api/files/{fid}/measurements/?status=bogus").status_code == 422


def test_list_files(client, upload):
    fid = upload("point.kml").json()["id"]
    listing = client.get("/api/files/").json()
    assert listing[0]["id"] == fid


def test_not_found(client, db):
    r = client.get("/api/files/999999/")
    assert r.status_code == 404 and r.json()["error"]["code"] == "FILE_NOT_FOUND"
    assert client.get("/api/files/999999/measurements/").status_code == 404


def test_delete(client, upload):
    fid = upload("point.kml").json()["id"]
    assert client.delete(f"/api/files/{fid}/").status_code == 204
    assert client.get(f"/api/files/{fid}/").status_code == 404


def test_openapi_available(client):
    r = client.get("/api/schema/?format=json")
    assert r.status_code == 200
    assert {"/api/files/", "/api/files/{file_id}/", "/api/files/{file_id}/measurements/"} <= set(r.json()["paths"])
    assert client.get("/api/docs/").status_code == 200
