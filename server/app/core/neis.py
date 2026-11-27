"""
NEIS 교육정보 개방 포털 학사일정(SchoolSchedule) 조회

출석체크에서 휴업일 · 공휴일(방학 포함)을 판단하기 위해 사용합니다.
API 문서: https://open.neis.go.kr/portal/data/service/selectServicePage.do?infId=OPEN17220190722175038389180
"""

import asyncio
from calendar import monthrange
from datetime import date, datetime

import httpx

from .config import settings
from .error import ServiceUnavailable
from .loggers import LoggerCore
from .redis import RedisCore
from .redis_keys import Keys

NEIS_SCHEDULE_URL = "https://open.neis.go.kr/hub/SchoolSchedule"
NEIS_TIMEOUT = 5
NEIS_PAGE_SIZE = 1000

NEIS_OFF_DAY_NAMES = frozenset({"휴업일", "공휴일"})
"""출석 불가일로 보는 수업공제일명(SBTR_DD_SC_NM) 값. 방학 기간도 학교가 휴업일로 입력합니다."""

NEIS_NO_DATA_CODE = "INFO-200"
"""해당하는 데이터가 없을 때의 결과 코드"""


def _month_starts(start: date, end: date) -> list[date]:
    """start ~ end 기간에 걸친 각 달의 1일 목록"""
    months = []
    current = start.replace(day=1)
    while current <= end:
        months.append(current)
        current = date(current.year + 1, 1, 1) if current.month == 12 else date(current.year, current.month + 1, 1)
    return months


def _parse_off_days(data: dict) -> list[date]:
    """
    NEIS 학사일정 응답에서 출석 불가일을 꺼냅니다.

    Raises:
        ServiceUnavailable: 응답이 오류이거나 형식이 예상과 다른 경우 발생합니다.
    """
    # 데이터가 없으면 SchoolSchedule 대신 최상위에 RESULT만 내려옵니다.
    result = data.get("RESULT")
    if result is not None:
        if result.get("CODE") == NEIS_NO_DATA_CODE:
            return []
        raise ServiceUnavailable(f"NEIS 학사일정 조회 실패 ({result.get('CODE')})")

    try:
        head, body = data["SchoolSchedule"]
        code = head["head"][1]["RESULT"]["CODE"]
        rows = body["row"]
    except KeyError, IndexError, TypeError, ValueError:
        raise ServiceUnavailable("NEIS 학사일정 응답 형식이 올바르지 않습니다.")

    if code != "INFO-000":
        raise ServiceUnavailable(f"NEIS 학사일정 조회 실패 ({code})")

    off_days = set()
    for row in rows:
        if row.get("SBTR_DD_SC_NM") in NEIS_OFF_DAY_NAMES:
            off_days.add(datetime.strptime(row["AA_YMD"], "%Y%m%d").date())
    return sorted(off_days)


async def _fetch_month(client: httpx.AsyncClient, month: date) -> list[date]:
    """한 달치 출석 불가일을 캐시 또는 NEIS에서 가져옵니다."""
    key = Keys.Neis.OFF_DAYS(year_month=month.strftime("%Y%m"))
    cached = await RedisCore.get(key)
    if cached is not None:
        return [date.fromisoformat(day) for day in cached]

    neis = settings.neis
    if neis is None:
        raise ServiceUnavailable("NEIS 설정이 없습니다.")

    last_day = month.replace(day=monthrange(month.year, month.month)[1])
    params = {
        "KEY": neis.api_key,
        "Type": "json",
        "pIndex": 1,
        "pSize": NEIS_PAGE_SIZE,
        "ATPT_OFCDC_SC_CODE": neis.office_code,
        "SD_SCHUL_CODE": neis.school_code,
        "AA_FROM_YMD": month.strftime("%Y%m%d"),
        "AA_TO_YMD": last_day.strftime("%Y%m%d"),
    }
    try:
        response = await client.get(NEIS_SCHEDULE_URL, params=params)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as e:
        # httpx 예외 메시지에는 요청 URL(API 키 포함)이 들어 있으므로 예외 종류만 남깁니다.
        LoggerCore.service_attendance.error(f"NEIS 학사일정 요청 실패 - {month:%Y-%m} ({type(e).__name__})")
        raise ServiceUnavailable("NEIS 학사일정을 가져오지 못했습니다.")

    try:
        off_days = _parse_off_days(data)
    except ServiceUnavailable as e:
        LoggerCore.service_attendance.error(f"NEIS 학사일정 응답 오류 - {month:%Y-%m} ({e})")
        raise

    await RedisCore.set(key, [day.isoformat() for day in off_days])
    LoggerCore.service_attendance.debug(f"NEIS 학사일정 조회 - {month:%Y-%m} 출석 불가일 {len(off_days)}일")
    return off_days


async def get_off_days(start: date, end: date) -> set[date]:
    """
    start ~ end(양 끝 포함) 기간의 출석 불가일(휴업일 · 공휴일)을 가져옵니다.
    주말은 포함하지 않으므로, 주말 여부는 따로 확인해야 합니다.

    Args:
        start: 시작일
        end: 종료일

    Returns:
        set[date]: 기간 안의 출석 불가일

    Raises:
        ServiceUnavailable: NEIS 설정이 없거나, 조회에 실패한 경우 발생합니다.
    """
    if start > end:
        return set()

    async with httpx.AsyncClient(timeout=NEIS_TIMEOUT) as client:
        results = await asyncio.gather(*(_fetch_month(client, month) for month in _month_starts(start, end)))

    return {day for days in results for day in days if start <= day <= end}
