from xml.etree import ElementTree as ET

from app.models import MediaFile, ScrapeMatch


def _text(parent: ET.Element, tag: str, value: str | int | float | None) -> None:
    if value is None or value == "":
        return
    child = ET.SubElement(parent, tag)
    child.text = str(value)


def generate_episode_nfo(media: MediaFile, match: ScrapeMatch) -> str:
    root = ET.Element("episodedetails")
    _text(root, "title", match.episode_title or f"第 {match.episode} 集")
    _text(root, "showtitle", match.show_title)
    _text(root, "season", match.season)
    _text(root, "episode", match.episode)
    _text(root, "plot", match.plot)
    _text(root, "aired", match.air_date)
    _text(root, "rating", match.rating)
    _text(root, "year", match.show_year)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")
