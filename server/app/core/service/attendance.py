"""
출석체크 규칙

- 평일(월~금) 중 NEIS 학사일정의 휴업일 · 공휴일이 아닌 날(수업일)에만 하루 한 번 출석할 수 있습니다.
- 마지막 출석일과 오늘 사이에 수업일이 하루도 없으면 연속 출석으로 봅니다. (금요일 → 월요일, 공휴일 · 방학을 건너뜀)
- 연속 출석 일수가 11의 배수(11, 22, ...)인 날은 기본 포인트 대신 보너스 포인트를 지급하며, 연속 일수는 계속 이어집니다.

아래 함수는 DB · Redis · NEIS에 접근하지 않는 순수 함수입니다.
"""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from app.schemas.core import SchemaCore

ATTENDANCE_POINT = 10
"""출석 1회 기본 지급 포인트"""

ATTENDANCE_BONUS_POINT = 100
"""연속 출석 보너스 포인트 (이날은 기본 포인트를 지급하지 않음)"""

ATTENDANCE_BONUS_STREAK = 11
"""보너스를 지급하는 연속 출석 주기"""

ATTENDANCE_TIMEZONE = ZoneInfo("Asia/Seoul")
"""출석일을 정하는 시간대. DB 시간대와 관계없이 학교 기준(KST)입니다."""

ATTENDANCE_MAX_GAP_DAYS = 366
"""마지막 출석 이후 이 일수보다 오래 지났다면 학사일정을 조회하지 않고 연속이 끊긴 것으로 봅니다."""


def today_kst() -> date:
    """오늘 날짜(KST)"""
    return SchemaCore.now().astimezone(ATTENDANCE_TIMEZONE).date()


def is_school_day(day: date, off_days: set[date]) -> bool:
    """
    출석할 수 있는 날(수업일)인지 확인합니다.

    Args:
        day: 확인할 날짜
        off_days: 휴업일 · 공휴일 목록

    Returns:
        bool: 평일이면서 휴업일 · 공휴일이 아니면 True
    """
    return day.weekday() < 5 and day not in off_days


def count_school_days(start: date, end: date, off_days: set[date]) -> int:
    """
    start와 end 사이(양 끝 제외)의 수업일 수를 셉니다.

    Args:
        start: 시작일 (포함하지 않음)
        end: 종료일 (포함하지 않음)
        off_days: 휴업일 · 공휴일 목록

    Returns:
        int: 수업일 수
    """
    count = 0
    day = start + timedelta(days=1)
    while day < end:
        if is_school_day(day, off_days):
            count += 1
        day += timedelta(days=1)
    return count


def is_streak_continued(last_date: date | None, today: date, off_days: set[date]) -> bool:
    """
    마지막 출석일부터 오늘까지 연속 출석이 이어지는지 확인합니다.

    Args:
        last_date: 마지막 출석일 (오늘 이전, 없으면 None)
        today: 오늘 날짜
        off_days: last_date 다음 날부터 오늘 전날까지의 휴업일 · 공휴일이 들어 있는 목록

    Returns:
        bool: 사이에 빠뜨린 수업일이 없으면 True
    """
    if last_date is None or (today - last_date).days > ATTENDANCE_MAX_GAP_DAYS:
        return False
    return count_school_days(last_date, today, off_days) == 0


def next_streak(last_date: date | None, last_streak: int, today: date, off_days: set[date]) -> int:
    """
    오늘 출석했을 때의 연속 출석 일수를 계산합니다.

    Args:
        last_date: 마지막 출석일 (오늘 이전, 없으면 None)
        last_streak: 마지막 출석일의 연속 출석 일수
        today: 오늘 날짜
        off_days: last_date 다음 날부터 오늘 전날까지의 휴업일 · 공휴일이 들어 있는 목록

    Returns:
        int: 이어지면 last_streak + 1, 끊겼으면 1
    """
    return last_streak + 1 if is_streak_continued(last_date, today, off_days) else 1


def attendance_reward(streak: int) -> int:
    """
    연속 출석 일수에 따른 지급 포인트를 계산합니다.

    Args:
        streak: 연속 출석 일수 (1 이상)

    Returns:
        int: 11의 배수 날이면 `ATTENDANCE_BONUS_POINT`, 아니면 `ATTENDANCE_POINT`
    """
    return ATTENDANCE_BONUS_POINT if streak % ATTENDANCE_BONUS_STREAK == 0 else ATTENDANCE_POINT


def days_to_bonus(streak: int) -> int:
    """
    현재 연속 출석 일수에서 다음 보너스까지 남은 출석 횟수를 계산합니다.

    Args:
        streak: 현재 연속 출석 일수 (끊겼으면 0)

    Returns:
        int: 1이면 다음 출석에서 보너스를 받습니다.
    """
    return ATTENDANCE_BONUS_STREAK - streak % ATTENDANCE_BONUS_STREAK


def off_days_window_start(last_date: date | None, today: date) -> date:
    """
    연속 출석과 오늘의 출석 가능 여부를 판단하기 위해 학사일정을 조회할 시작일을 정합니다.

    Args:
        last_date: 마지막 출석일 (오늘 이전, 없으면 None)
        today: 오늘 날짜

    Returns:
        date: 마지막 출석 다음 날, 너무 오래됐거나 출석한 적이 없으면 오늘
    """
    if last_date is None or (today - last_date).days > ATTENDANCE_MAX_GAP_DAYS:
        return today
    return last_date + timedelta(days=1)
