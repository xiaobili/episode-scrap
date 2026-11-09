from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./episodescrap.db"
    secret_key: str = "dev-secret-change-me"
    encryption_key: str = ""
    tmdb_api_key: str = ""
    allowed_paths: str = ""
    scrape_concurrency: int = 3
    openlist_concurrency: int = 3
    openlist_timeout: int = 30
    openlist_retry: int = 3
    rename_template: str = "{title} - S{season:02d}E{episode:02d} - {episode_title}"
    strm_url_template: str = "{base_url}/d/{path}"
    strm_output_mode: str = "alongside"
    strm_target_dir: str = ""

    @property
    def allowed_path_list(self) -> list[str]:
        return [p.strip() for p in self.allowed_paths.split(";") if p.strip()]


settings = Settings()
