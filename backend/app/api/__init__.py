from fastapi import APIRouter

from app.api import datasources as datasources_api
from app.api import jellyfin as jellyfin_api
from app.api import parse as parse_api
from app.api import rename as rename_api
from app.api import scan as scan_api
from app.api import scrape as scrape_api
from app.api import settings as settings_api
from app.api import tasks as tasks_api

api_router = APIRouter()
api_router.include_router(scan_api.router)
api_router.include_router(parse_api.router)
api_router.include_router(datasources_api.router)
api_router.include_router(rename_api.router)
api_router.include_router(scrape_api.router)
api_router.include_router(tasks_api.router)
api_router.include_router(settings_api.router)
api_router.include_router(jellyfin_api.router)
