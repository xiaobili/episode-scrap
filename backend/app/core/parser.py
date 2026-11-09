import re
from dataclasses import dataclass
from pathlib import Path

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".ts", ".webm"}

_SEASON_EPISODE = re.compile(
    r"S(?P<season>\d{1,2})[\s._-]?E(?P<episode>\d{1,2})(?:[-–]E?(?P<episode_end>\d{1,2}))?",
    re.IGNORECASE,
)
_CROSS_EPISODE = re.compile(r"(?<!\d)(?P<season>\d{1,2})x(?P<episode>\d{1,2})(?!\d)", re.IGNORECASE)
_CHINESE_EPISODE = re.compile(r"第\s*(?P<season>\d+)\s*季.*?第\s*(?P<episode>\d+)\s*集")
_CHINESE_EPISODE_ONLY = re.compile(r"第\s*(?P<episode>\d{1,3})\s*[集话話]")
_EPISODE_PREFIX = re.compile(
    r"(?<![A-Za-z0-9])EP?[\s._-]?(?P<episode>\d{1,3})(?![A-Za-z0-9])", re.IGNORECASE
)
_BARE_EPISODE = re.compile(
    r"(?<![A-Za-z0-9])(?P<episode>\d{1,3})(?:v\d{1,2})?(?![A-Za-z0-9])", re.IGNORECASE
)
_SEASON_WORD = re.compile(r"(?:season|series)[\s._-]*$", re.IGNORECASE)
_YEAR = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")

_RESOLUTION = re.compile(r"(?<!\d)(2160p|1080p|720p|480p|4k)(?!\d)", re.IGNORECASE)
_CODEC = re.compile(r"(?<![a-z0-9])(x265|x264|h\.?265|h\.?264|hevc|av1)(?![a-z0-9])", re.IGNORECASE)
_RELEASE_GROUP = re.compile(r"-([A-Za-z][A-Za-z0-9@]{1,20})$")

_NOISE = re.compile(
    r"(?<![a-z0-9])("
    r"bluray|blu-ray|bdrip|brrip|web-dl|webrip|web|hdtv|dvdrip|remux|"
    r"proper|repack|extended|uncut|multi|dual|"
    r"dts(?:-hd)?|ddp?5\.1|ac3|aac|truehd|flac|atmos|"
    r"hdr10\+?|hdr|dv|dolby\s?vision|10bit|8bit|"
    r"chs|cht|eng|jpn|korsub|subbed|dubbed|"
    r"内封|中字|双语|国语|粤语|高清|蓝光"
    r")(?![a-z0-9])",
    re.IGNORECASE,
)
_BRACKETS = re.compile(r"[\[【（(][^\]】）)]*[\]】）)]")

_SEASON_FOLDER = re.compile(
    r"^(?:season[\s._-]*|series[\s._-]*|s|第\s*)(\d{1,2})(?:\s*季)?$", re.IGNORECASE
)
_DRIVE_PART = re.compile(r"^[A-Za-z]:\\?$")
_GENERIC_FOLDERS = {
    "media",
    "medias",
    "tv",
    "tvshows",
    "shows",
    "series",
    "videos",
    "video",
    "movies",
    "movie",
    "downloads",
    "download",
    "anime",
    "影视",
    "电视剧",
    "电影",
    "剧集",
    "国产剧",
    "美剧",
    "日剧",
    "韩剧",
    "动漫",
}


@dataclass
class ParsedInfo:
    title: str | None = None
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    episode_end: int | None = None
    episode_title: str | None = None
    resolution: str | None = None
    codec: str | None = None
    release_group: str | None = None
    raw: str = ""
    confidence: int = 0


def is_video_filename(filename: str) -> bool:
    return Path(filename).suffix.lower() in VIDEO_EXTENSIONS


def _clean_title(value: str) -> str:
    text = _BRACKETS.sub(" ", value)
    text = _NOISE.sub(" ", text)
    text = re.sub(r"[._]+", " ", text)
    text = re.sub(r"[\s\-–]+$", "", text)
    text = re.sub(r"\s*-\s*\d{1,4}$", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" -–_")
    return text.strip()


class FilenameParser:
    def parse(self, filename: str, path: str | None = None) -> ParsedInfo:
        stem = Path(filename).stem
        info = ParsedInfo(raw=filename)

        info.resolution = self._match_group(_RESOLUTION, stem)
        if info.resolution and info.resolution.lower() == "4k":
            info.resolution = "2160p"
        info.codec = self._match_group(_CODEC, stem)
        group_match = _RELEASE_GROUP.search(stem)
        if group_match:
            info.release_group = group_match.group(1)

        match, title_raw = self._match_season_episode(stem)
        if match:
            season = match.groupdict().get("season")
            if season:
                info.season = int(season)
            info.episode = int(match.group("episode"))
            end = match.groupdict().get("episode_end")
            if end:
                info.episode_end = int(end)
            if title_raw is None:
                title_raw = stem[: match.start()]
        else:
            title_raw = stem

        year_match = _YEAR.search(title_raw)
        if year_match:
            info.year = int(year_match.group(1))
            title_raw = title_raw[: year_match.start()] + " " + title_raw[year_match.end() :]

        info.title = _clean_title(title_raw) or None

        folder_title, folder_season = self._folder_hints(path)
        if folder_season is not None and info.season is None:
            info.season = folder_season
        if folder_title:
            info.title = folder_title

        confidence = 0
        if info.title:
            confidence += 40
        if info.season is not None:
            confidence += 25
        if info.episode is not None:
            confidence += 25
        if info.year or info.release_group:
            confidence += 10
        info.confidence = min(confidence, 100)
        return info

    @staticmethod
    def _folder_hints(path: str | None) -> tuple[str | None, int | None]:
        if not path:
            return None, None
        parts = [
            part
            for part in Path(path).parent.parts
            if part and part not in ("/", "\\") and not _DRIVE_PART.match(part)
        ]
        if not parts:
            return None, None

        index = len(parts) - 1
        season: int | None = None
        season_match = _SEASON_FOLDER.match(parts[index])
        if season_match:
            season = int(season_match.group(1))
            index -= 1
        if index < 0:
            return None, season

        name = parts[index].strip()
        if not name or name.lower() in _GENERIC_FOLDERS:
            return None, season
        title = _clean_title(name) or None
        if not title:
            return None, season
        return title, season if season is not None else 1

    @staticmethod
    def _match_group(pattern: re.Pattern[str], text: str) -> str | None:
        m = pattern.search(text)
        return m.group(1) if m else None

    @staticmethod
    def _match_season_episode(stem: str) -> tuple[re.Match[str] | None, str | None]:
        chinese = _CHINESE_EPISODE.search(stem)
        if chinese:
            return chinese, stem[: chinese.start()]

        for pattern in (_SEASON_EPISODE, _CROSS_EPISODE):
            m = pattern.search(stem)
            if m:
                return m, stem[: m.start()]

        # 无季信息时，依次尝试：第 N 集 / EPn / 裸集号（如 01、01.4k、01-4k）
        for pattern in (_CHINESE_EPISODE_ONLY, _EPISODE_PREFIX):
            m = pattern.search(stem)
            if m:
                return m, stem[: m.start()]

        for m in _BARE_EPISODE.finditer(stem):
            if int(m.group("episode")) < 1:
                continue
            prefix = stem[: m.start()]
            if prefix.rstrip().endswith("第") or _SEASON_WORD.search(prefix):
                continue
            return m, prefix

        return None, None
