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
    assert info.episode == 5
    assert info.title == "Some Anime"
    assert info.resolution == "1080p"
    assert info.confidence >= 60


def test_parse_bare_episode_number():
    info = FilenameParser().parse("01.mp4")
    assert info.season is None
    assert info.episode == 1
    assert info.title is None


def test_parse_bare_episode_with_4k_suffix():
    for name in ("01.4k.mp4", "01-4k.mp4", "01~4k.mp4"):
        info = FilenameParser().parse(name)
        assert info.episode == 1, name
        assert info.season is None, name
        assert info.resolution == "2160p", name
        assert info.title is None, name


def test_parse_chinese_episode_without_season():
    info = FilenameParser().parse("绝命毒师 第03集.mp4")
    assert info.title == "绝命毒师"
    assert info.season is None
    assert info.episode == 3


def test_parse_dot_separated_season_episode():
    info = FilenameParser().parse("Show.S01.E02.1080p.mkv")
    assert info.season == 1
    assert info.episode == 2
    assert info.title == "Show"


def test_parse_bare_episode_with_version_suffix():
    info = FilenameParser().parse("01v2.mp4")
    assert info.season is None
    assert info.episode == 1
    assert info.title is None


def test_parse_episode_prefix():
    info = FilenameParser().parse("Show Name EP07 720p.mkv")
    assert info.episode == 7
    assert info.title == "Show Name"


def test_movie_year_is_not_parsed_as_episode():
    info = FilenameParser().parse("Blade.Runner.2049.2017.1080p.mkv")
    assert info.episode is None
    assert info.season is None


def test_folder_title_and_season_from_path():
    info = FilenameParser().parse("01.mp4", path="/media/绝命毒师/Season 02/01.mp4")
    assert info.title == "绝命毒师"
    assert info.season == 2
    assert info.episode == 1
    assert info.confidence >= 85


def test_folder_without_season_defaults_to_first_season():
    info = FilenameParser().parse("01.mp4", path="/media/大明王朝/01.mp4")
    assert info.title == "大明王朝"
    assert info.season == 1
    assert info.episode == 1


def test_file_season_beats_folder_default():
    info = FilenameParser().parse("Show.S03E04.mkv", path="/media/大明王朝/Show.S03E04.mkv")
    assert info.title == "大明王朝"
    assert info.season == 3
    assert info.episode == 4


def test_folder_title_beats_filename_title():
    info = FilenameParser().parse("English Name - 01.mp4", path="/media/绝命毒师/Season 1/English Name - 01.mp4")
    assert info.title == "绝命毒师"
    assert info.season == 1


def test_chinese_season_folder():
    info = FilenameParser().parse("01.mp4", path="/媒体/大明王朝/第2季/01.mp4")
    assert info.title == "大明王朝"
    assert info.season == 2


def test_generic_folder_is_not_used_as_title():
    info = FilenameParser().parse("01.mp4", path="/media/电视剧/01.mp4")
    assert info.title is None
    assert info.season is None


def test_non_video_filename():
    assert is_video_filename("README.txt") is False
    assert is_video_filename("Show.S01E01.mkv") is True
