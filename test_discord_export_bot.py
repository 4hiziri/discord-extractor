from discord_export_bot import extract_link_if_content_only_links


def test_extract_link_plain_url() -> None:
    assert extract_link_if_content_only_links("https://example.com/page") == ["https://example.com/page"]


def test_extract_link_angle_bracket_url() -> None:
    assert extract_link_if_content_only_links("<https://example.com/page>") == ["https://example.com/page"]


def test_extract_links_from_message_content() -> None:
    assert extract_link_if_content_only_links("check https://example.com/page and https://example.org/x") == [
        "https://example.com/page",
        "https://example.org/x",
    ]


def test_extract_link_with_no_url_returns_empty_list() -> None:
    assert extract_link_if_content_only_links("hello world") == []
