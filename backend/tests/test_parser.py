from app.core.parser import FilenameParser, is_video_filename


def test_parse_western_release():
    info = FilenameParser().parse("Breaking.Bad.S01E03.1080p.BluRay.x264-DEMAND.mkv")
    assert info.title == "Breaking Bad"
    assert info.season == 1
    assert info.episode == 3
    assert info.resolution == "1080p"
    assert info.codec == "x264"
    assert info.release_group == "DEMAND"
    assert info.confidence >= 85


def test_parse_chinese():
    info = FilenameParser().parse("绝命毒师 第1季 第03集.mp4")
    assert info.title == "绝命毒师"
    assert info.season == 1
    assert info.episode == 3
    assert info.confidence >= 85


def test_parse_cross_episode():
    info = FilenameParser().parse("Show.1x02.720p.mkv")
    assert info.season == 1
    assert info.episode == 2


def test_parse_multi_episode():
    info = FilenameParser().parse("Show.S01E01-E02.mkv")
    assert info.episode == 1
    assert info.episode_end == 2


def test_parse_absolute_number_without_season():
    info = FilenameParser().parse("[Group] Some Anime - 05 [1080p].mkv")
    assert info.season is None
    assert info.confidence < 60
    assert "Group" not in (info.title or "")
    assert "1080p" not in (info.title or "")


def test_non_video_filename():
    assert is_video_filename("README.txt") is False
    assert is_video_filename("Show.S01E01.mkv") is True
