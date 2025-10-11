from backend.evaluator.extract import (
    compute_key_info_preserved,
    extract_key_units,
)


def test_extract_key_units_from_json():
    text = '{"user_id": "123", "profile": {"top_genres": ["Sci-Fi", "Drama"]}}'
    units = extract_key_units(text)
    # JSON keys should be present
    assert any(u.startswith("profile.top_genres") for u in units)


def test_compute_key_info_preserved_simple():
    sent = '"Dune" by Denis Villeneuve is Sci-Fi'
    received = 'Villeneuve delivers excellent Sci-Fi in Dune'
    preserved = compute_key_info_preserved(sent, received)
    # Expect at least the quoted phrase Dune to be preserved
    assert any("Dune" == p for p in preserved)

