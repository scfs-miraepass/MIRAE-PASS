from typing import Annotated

from pydantic import BaseModel, Field, MySQLDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Database(BaseModel):
    url: MySQLDsn = Field(alias="URL")
    pool_size: int = Field(10, alias="POOL_SIZE")
    max_overflow: int = Field(20, alias="MAX_OVERFLOW")
    pool_timeout: int = Field(30, alias="POOL_TIMEOUT")


class Redis(BaseModel):
    url: RedisDsn = Field(alias="URL")


class Session(BaseModel):
    cookie_name: str = Field("session_id", alias="COOKIE_NAME")
    expire_seconds: int = Field(3600 * 24 * 7, alias="EXPIRE_SECONDS")  # 기본 7일


class Service(BaseModel):
    session: Session = Field(Session(), alias="SESSION")


class Neis(BaseModel):
    """NEIS 교육정보 개방 포털 Open API 설정 (출석체크의 학사일정 조회에 사용)"""

    api_key: str = Field(alias="API_KEY")
    office_code: str = Field(alias="OFFICE_CODE")  # 시도교육청코드 (ATPT_OFCDC_SC_CODE)
    school_code: str = Field(alias="SCHOOL_CODE")  # 행정표준코드 (SD_SCHUL_CODE)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_nested_delimiter="_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    database: Database = Field(alias="DATABASE")
    redis: Redis = Field(alias="REDIS")
    service: Service = Field(Service(), alias="SERVICE")
    neis: Neis | None = Field(None, alias="NEIS")
    debug: bool = Field(False, alias="DEBUG")
    database_debug: bool = Field(False, alias="DATABASE_DEBUG")
    allow_origins: Annotated[list[str], NoDecode] = Field(alias="ALLOWED_ORIGINS")

    @field_validator("allow_origins", mode="before")
    @classmethod
    def decode_allow_origins(cls, v):
        if isinstance(v, str):
            # 쉼표로 나누고 앞뒤 공백을 제거해요
            return [item.strip() for item in v.split(",")]
        return v


settings = Settings()
