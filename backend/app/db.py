from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


def init_db() -> None:
    # 确保所有模型均已导入注册
    import app.models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _ensure_columns()


def _ensure_columns() -> None:
    """为已有 SQLite 数据库补齐新增列（create_all 不会修改旧表结构）。"""
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(taskrecord)")}
        if columns and "write_strm" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE taskrecord ADD COLUMN write_strm BOOLEAN NOT NULL DEFAULT 0"
            )
            conn.commit()

        ol_columns = {
            row[1] for row in conn.exec_driver_sql("PRAGMA table_info(openlistinstance)")
        }
        if ol_columns and "mount_path" not in ol_columns:
            conn.exec_driver_sql(
                "ALTER TABLE openlistinstance ADD COLUMN mount_path VARCHAR NOT NULL DEFAULT '/'"
            )
            conn.commit()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
