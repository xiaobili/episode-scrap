import os

import pytest

from app.core.strm import (
    StrmTemplateError,
    library_target,
    match_strm_rule,
    mirror_target,
    render_strm,
    rule_target_dir,
    strm_filename,
    validate_strm_template,
)


def test_render_strm_encodes_path():
    content = render_strm(
        "{base_url}/d/{path}",
        base_url="https://fox.example.com",
        path="/电视剧/Show S01E01.mp4",
    )
    assert content == (
        "https://fox.example.com/d/"
        "%E7%94%B5%E8%A7%86%E5%89%A7/Show%20S01E01.mp4"
    )


def test_render_strm_supports_raw_path_and_filename():
    content = render_strm(
        "{base_url}/p{raw_path}?name={filename}",
        base_url="https://fox.example.com",
        path="/剧集/Show.S01E01.mkv",
    )
    assert content == "https://fox.example.com/p/剧集/Show.S01E01.mkv?name=Show.S01E01.mkv"


def test_unknown_variable_raises():
    with pytest.raises(StrmTemplateError):
        validate_strm_template("{base_url}/d/{unknown}")


def test_template_requires_path():
    with pytest.raises(StrmTemplateError):
        validate_strm_template("{base_url}/d/")


def test_strm_filename_replaces_extension():
    assert strm_filename("Show - S01E01.mkv") == "Show - S01E01.strm"
    assert strm_filename("Show - S01E01") == "Show - S01E01.strm"


def test_library_target():
    target = library_target("/library", "绝命毒师", 2, "绝命毒师 - S02E01.strm")
    assert target == "/library/绝命毒师/Season 02/绝命毒师 - S02E01.strm"


def test_mirror_target_keeps_relative_structure():
    target = mirror_target(
        "/library",
        "/cloud/tv",
        "/cloud/tv/绝命毒师/Season 02/01.mkv",
        "绝命毒师 - S02E01.strm",
    )
    assert target == "/library/绝命毒师/Season 02/绝命毒师 - S02E01.strm"


def test_mirror_target_falls_back_when_outside_root():
    target = mirror_target("/library", "/cloud/tv", "/other/01.mkv", "a.strm")
    assert target is None


def test_mirror_target_without_root():
    assert mirror_target("/library", None, "/cloud/tv/01.mkv", "a.strm") is None


def test_match_strm_rule_uses_longest_prefix():
    rules = [
        {"source": "/cloud", "target_dir": "/base"},
        {"source": "/cloud/美剧", "target_dir": "/strm/美剧"},
    ]
    matched = match_strm_rule(
        rules, "/cloud/美剧/大宋提刑官/Season 01/01.mkv"
    )
    assert matched is not None
    rule, rel_dir = matched
    assert rule["target_dir"] == "/strm/美剧"
    assert rel_dir == "大宋提刑官/Season 01"
    assert rule_target_dir(rule, rel_dir) == "/strm/美剧/大宋提刑官/Season 01"


def test_match_strm_rule_respects_path_boundary():
    rules = [{"source": "/cloud/美剧", "target_dir": "/strm/美剧"}]
    assert match_strm_rule(rules, "/cloud/美剧2/01.mkv") is None


def test_match_strm_rule_returns_none_without_hit():
    rules = [{"source": "/cloud/美剧", "target_dir": "/strm/美剧"}]
    assert match_strm_rule(rules, "/other/01.mkv") is None
