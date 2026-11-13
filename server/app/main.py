from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta, timezone, tzinfo
from pathlib import Path
from tomllib import load

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlmodel import select, col
from zoneinfo import ZoneInfo

from .core import ServiceClient, settings
from .core.service.karaoke import Karaoke as KaraokeService
from .router import router
from .schemas import Karaokes, KaraokeStatus, UserPermission
from .schemas.response import ErrorResponse
from .schemas.core import SchemaCore


scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Seoul"))
client = ServiceClient()

# pyproject.toml에서 버전을 동적으로 불러오기
pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
with open(pyproject_path, "rb") as f:
    pyproject_data = load(f)
    app_version = pyproject_data.get("project", {}).get("version")
    if not app_version:
        raise KeyError("Failed to find 'version' in [project] section of pyproject.toml")


@scheduler.scheduled_job(CronTrigger(second=0))
async def process_karaoke_auctions():
    """
    노래방 예약 경매의 시작/종료 시간을 확인하여 상태를 자동으로 전환하고,
    진행 중인 경매는 남은 시간을 sync 채널로 브로드캐스트합니다.

    - `PENDING` 상태이고 시작 시간이 지난 경매는 `IN_PROGRESS`로 변경합니다.
    - `IN_PROGRESS` 상태이고 종료 시간이 지난 경매는 `CONFIRMED`로 변경합니다.
    - `IN_PROGRESS` 상태이고 아직 종료 시간이 지나지 않은 경매는 남은 시간을 브로드캐스트합니다.

    매 분 정각에 실행됩니다.
    """
    client.logs.service_karaoke.debug("노래방 예약 경매 시작/종료 및 동기화 처리")
    async with client.session as session:
        query = select(Karaokes).where(col(Karaokes.status).in_([KaraokeStatus.PENDING, KaraokeStatus.IN_PROGRESS]))
        result = await session.execute(query)
        karaokes = list(result.scalars().all())

    change_progress = 0
    change_confirmed = 0
    for row in karaokes:
        karaoke = KaraokeService(row)

        if row.status == KaraokeStatus.PENDING:
            # start_time/end_time은 시간대 정보가 없는 DATETIME 컬럼이라 DB 서버 시간대 기준의
            # wall clock으로 저장됩니다. 백엔드 프로세스의 로컬 시계(datetime.now())와 그대로
            # 비교하면 두 시간대의 시차만큼 어긋나므로, DB 시간대를 붙여 aware끼리 비교합니다.
            if SchemaCore.sync_timezone(row.start_time) > SchemaCore.now():
                continue

            await karaoke.set_status(KaraokeStatus.IN_PROGRESS)
            client.logs.service_karaoke.info(f"노래방 경매 자동 시작 - ID {row.id}({row.date} / {row.time})")
            change_progress += 1

        elif row.status == KaraokeStatus.IN_PROGRESS:
            if SchemaCore.sync_timezone(row.end_time) > SchemaCore.now():
                remaining_time = SchemaCore.remaining_seconds(row.end_time)
                try:
                    await karaoke.publish("sync", remaining_time)
                except Exception:
                    # 한 경매의 발행이 실패해도 나머지 경매 처리는 계속 진행합니다.
                    client.logs.service_karaoke.exception(f"노래방 경매 동기화 발행 실패 - ID {row.id}")
                continue

            await karaoke.set_status(KaraokeStatus.CONFIRMED)
            client.logs.service_karaoke.info(f"노래방 경매 자동 종료 - ID {row.id}({row.date} / {row.time})")
            change_confirmed += 1

    client.logs.service_karaoke.debug(
        f"경매 시작/종료 스케줄 완료됨. {change_progress}개 시작, {change_confirmed}개 종료"
    )


async def resolve_database_timezone(session) -> tzinfo:
    """
    DB 서버의 시간대를 해석합니다.

    1. `@@time_zone`(SYSTEM이면 `@@system_time_zone`)을 IANA 이름으로 해석
    2. 실패 시 DB 서버의 실제 UTC 오프셋(`NOW() - UTC_TIMESTAMP()`)으로 고정 오프셋 시간대 생성

    Windows MySQL은 `@@system_time_zone`을 "대한민국 표준시"처럼 로케일 이름으로 반환하므로
    (인코딩에 따라 깨진 문자열이 되기도 함) 1단계가 실패할 수 있어 2단계 fallback이 필요합니다.
    PostgreSQL 사용하는경우 `SHOW TIME ZONE` 으로 SQL문 변경해야함
    """
    tz_string = (await session.execute(text("SELECT @@time_zone"))).scalar() or ""
    if tz_string.lower() == "system":
        tz_string = (await session.execute(text("SELECT @@system_time_zone"))).scalar() or ""

    try:
        return ZoneInfo(tz_string)
    except Exception:  # ZoneInfoNotFoundError 외에도 OSError/ValueError 등이 발생할 수 있음
        client.logs.global_.warning(
            f"DB의 서버 시간대 이름을 해석할 수 없습니다: {tz_string!r}. UTC 오프셋으로 대체합니다."
        )

    offset_seconds = (await session.execute(text("SELECT TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), NOW())"))).scalar()
    if offset_seconds is None:
        client.logs.global_.warning("DB의 UTC 오프셋을 조회할 수 없어 UTC를 사용합니다.")
        return timezone.utc

    # 초 단위 오차를 제거하기 위해 15분 단위로 반올림
    offset_seconds = round(int(offset_seconds) / 900) * 900
    return timezone(timedelta(seconds=offset_seconds))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    애플리케이션 라이프사이클 관리
    시작 시 데이터베이스 초기화, 종료 시 연결 정리
    """
    if settings.debug:
        client.logs.global_.warning("디버그 모드가 활성화 되어있습니다!")

    await client.initialize()

    client.logs.global_.info("데이터베이스 서버와 시간대를 동기화")
    async with client.session as session:
        SchemaCore.timezone = await resolve_database_timezone(session)
        client.logs.global_.debug(f"DB의 시간대: {SchemaCore.timezone}")

    scheduler.start()
    client.logs.global_.info("Scheduler 시작")

    yield

    scheduler.shutdown()
    client.logs.global_.info("Scheduler 종료")
    await client.close()


# FastAPI 인스턴스에 version 정보를 명시합니다.
app = FastAPI(lifespan=lifespan, title="MIRAE PASS BACKEND", version=app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-MAX-PAGE",
        "X-Server-Version",
        "X-CACHED",
    ],  # 클라이언트가 읽을 수 있도록 허용
)


# 모든 응답에 서버 버전을 알려주는 미들웨어 추가
@app.middleware("http")
async def add_server_version_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Server-Version"] = app.version
    return response


# 디버그 모드가 비활성화 되어있으면 모든 에러가 발생하는 내용을 로그에 출력
if not settings.debug:
    import sys

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        client.logs.global_.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(success=False, message=exc.detail or "No Message").model_dump(),
    )


@app.get("/")
async def read_root(_: UserPermission | None = None):
    return {"message": "Hello, World!"}


app.include_router(router)
