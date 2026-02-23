from discord_export_bot import extract_link_if_content_only_link


def test_extract_link_plain_url() -> None:
    assert extract_link_if_content_only_link("https://example.com/page") == "https://example.com/page"


def test_extract_link_angle_bracket_url() -> None:
    assert extract_link_if_content_only_link("<https://example.com/page>") == "https://example.com/page"


def test_extract_link_with_non_url_content_returns_none() -> None:
    assert extract_link_if_content_only_link("check https://example.com/page") is None
