from app.providers.base import SeasonInfo


def find_episode(season: SeasonInfo, episode: int | None):
    if episode is None:
        return None
    for item in season.episodes:
        if item.episode == episode:
            return item
    return None
