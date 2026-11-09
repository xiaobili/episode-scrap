import re
from dataclasses import dataclass
from pathlib import Path

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".ts", ".webm"}

_SEASON_EPISODE = re.compile(
    r"S(?P<season>\d{1,2})E(?P<episode>\d{1,2})(?:[-–]E?(?P<episode_end>\d{1,2}))?",
    re.IGNORECASE,
)
_CROSS_EPISODE = re.compile(r"(?<!\d)(?P<season>\d{1,2})x(?P<episode>\d{1,2})(?!\d)", re.IGNORECASE)
_CHINESE_EPISODE = re.compile(r"第\s*(?P<season>\d+)\s*季.*?第\s*(?P<episode>\d+)\s*集")
_YEAR = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")

_RESOLUTION = re.compile(r"(?<!\d)(2160p|1080p|720p|480p)(?!\d)", re.IGNORECASE)
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
    def parse(self, filename: str) -> ParsedInfo:
        stem = Path(filename).stem
        info = ParsedInfo(raw=filename)

        info.resolution = self._match_group(_RESOLUTION, stem)
        info.codec = self._match_group(_CODEC, stem)
        group_match = _RELEASE_GROUP.search(stem)
        if group_match:
            info.release_group = group_match.group(1)

        match, title_raw = self._match_season_episode(stem)
        if match:
            info.season = int(match.group("season"))
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

        return None, None
