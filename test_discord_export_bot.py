from discord_export_bot import expand_link_in_post


bdef test_extract_link_plain_url() -> None:
    assert expand_link_in_post("https://example.com/page") == ["https://example.com/page"]


def test_extract_link_angle_bracket_url() -> None:
    assert expand_link_in_post("<https://example.com/page>") == ["https://example.com/page"]


def test_extract_all_links_with_non_url_content() -> None:
    assert expand_link_in_post("check https://example.com/page and https://example.org") == [
        "https://example.com/page",
        "https://example.org",
    ]
