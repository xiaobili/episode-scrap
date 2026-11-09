from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.parser import FilenameParser
from app.db import get_session
from app.models import MediaFile
from app.schemas import MediaFileOut, ParseRequest, ParseUpdate, media_file_out

router = APIRouter(tags=["parse"])
parser = FilenameParser()


def _apply_status(media: MediaFile) -> None:
    if media.parsed_episode is not None or media.parsed_season is not None:
        media.status = "parsed"
    else:
        media.status = "error"


@router.post("/api/parse", response_model=list[MediaFileOut])
def parse_files(
    payload: ParseRequest, session: Session = Depends(get_session)
) -> list[MediaFileOut]:
    stmt = select(MediaFile).where(MediaFile.is_video.is_(True))
    if payload.file_ids:
        stmt = stmt.where(MediaFile.id.in_(payload.file_ids))
    elif not payload.all_files:
        raise HTTPException(status_code=400, detail="请提供 file_ids 或设置 all_files=true")
    files = session.exec(stmt).all()

    for media in files:
        info = parser.parse(media.original_name, path=media.source_ref)
        media.parsed_title = info.title
        media.parsed_year = info.year
        media.parsed_season = info.season
        media.parsed_episode = info.episode
        media.parsed_episode_end = info.episode_end
        media.parsed_episode_title = info.episode_title
        media.parsed_resolution = info.resolution
        media.parsed_codec = info.codec
        media.parsed_release_group = info.release_group
        media.confidence = info.confidence
        _apply_status(media)
        session.add(media)
    session.commit()
    for media in files:
        session.refresh(media)
    return [media_file_out(f) for f in files]


@router.put("/api/parse/{file_id}", response_model=MediaFileOut)
def update_parse(
    file_id: int, payload: ParseUpdate, session: Session = Depends(get_session)
) -> MediaFileOut:
    media = session.get(MediaFile, file_id)
    if not media:
        raise HTTPException(status_code=404, detail="文件不存在")

    mapping = {
        "title": "parsed_title",
        "year": "parsed_year",
        "season": "parsed_season",
        "episode": "parsed_episode",
        "episode_end": "parsed_episode_end",
        "episode_title": "parsed_episode_title",
        "resolution": "parsed_resolution",
        "codec": "parsed_codec",
        "release_group": "parsed_release_group",
    }
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(media, mapping[key], value)
    _apply_status(media)
    session.add(media)
    session.commit()
    session.refresh(media)
    return media_file_out(media)
