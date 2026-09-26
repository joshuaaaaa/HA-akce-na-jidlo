from akce_na_jidlo.stores import _parse_stores, format_address, nearest_store, store_chain


def test_store_chain_and_address():
    assert store_chain({"brand": "Lidl"}) == "lidl"
    assert store_chain({"name": "COOP Jednota"}) == "coop"
    assert store_chain({"name": "Potraviny U Nováků"}) is None
    # „dm“ se nesmí najít uvnitř jiného slova
    assert store_chain({"name": "Admiral"}) is None
    assert (
        format_address(
            {
                "addr:street": "Vinohradská",
                "addr:housenumber": "12",
                "addr:postcode": "120 00",
                "addr:city": "Praha",
            }
        )
        == "Vinohradská 12, 120 00 Praha"
    )


def test_parse_and_nearest():
    payload = {
        "elements": [
            {
                "type": "node",
                "id": 1,
                "lat": 50.08,
                "lon": 14.42,
                "tags": {"brand": "Albert", "name": "Albert"},
            },
            {
                "type": "way",
                "id": 2,
                "center": {"lat": 50.10, "lon": 14.50},
                "tags": {"brand": "Albert"},
            },
            {
                "type": "node",
                "id": 3,
                "lat": 48.2,
                "lon": 16.37,
                "tags": {"brand": "Billa"},
            },  # Vídeň
        ]
    }
    stores = _parse_stores(payload, "CZ")
    assert len(stores) == 2
    best = nearest_store(stores, "albert", 50.081, 14.421)
    assert best["osm_id"] == "node/1"
    assert best["distance_km"] < 0.5
    assert nearest_store(stores, "lidl", 50.08, 14.42) is None
