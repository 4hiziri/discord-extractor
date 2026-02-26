from discord_export_bot import extract_link_if_content_only_links


bdef test_extract_link_plain_url() -> None:
    assert extract_link_if_content_only_links("https://example.com/page") == ["https://example.com/page"]


def test_extract_link_angle_bracket_url() -> None:
    assert extract_link_if_content_only_links("<https://example.com/page>") == ["https://example.com/page"]


def test_extract_all_links_with_non_url_content() -> None:
    assert extract_link_if_content_only_links("check https://example.com/page and https://example.org") == [
        "https://example.com/page",
        "https://example.org",
    ]
