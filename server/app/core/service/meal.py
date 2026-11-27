from datetime import date, datetime
from html import unescape
from re import compile
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.schemas import MealDish, MealInfo, MealType

from ..config import settings
from ..core import BaseCore
from ..error import ExternalServiceError
from ..redis_keys import Keys

MEAL_TIMEZONE = ZoneInfo("Asia/Seoul")
"""'오늘'을 정할 시간대. DB 시간대와 관계없이 학교 기준(KST)입니다."""

NEIS_MEAL_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
NEIS_TIMEOUT_SECONDS = 5
NEIS_MEAL_TYPES = {"1": MealType.breakfast, "2": MealType.lunch, "3": MealType.dinner}
"""NEIS `MMEAL_SC_CODE` → 급식 종류"""

NEIS_RESULT_OK = "INFO-000"
NEIS_RESULT_NO_DATA = "INFO-200"

_LINE_BREAK = compile(r"<br\s*/?>")
_ALLERGY_SUFFIX = compile(r"\(([\d.\s]+)\)\s*$")
_NUMBER = compile(r"\d+(?:\.\d+)?")


class Meal(BaseCore):
    """
    NEIS 교육정보 개방 포털의 급식식단정보를 가져오는 서비스.
    DB 모델이 없으므로 `ServiceCore`가 아닌 `BaseCore`를 상속합니다.
    """

    @staticmethod
    def today() -> date:
        """
        학교 기준(KST) 오늘 날짜를 반환합니다.
        """
        return datetime.now(MEAL_TIMEZONE).date()

    async def get_by_date(self, day: date) -> list[MealInfo]:
        """
        해당 날짜의 급식(조식 · 중식 · 석식)을 가져옵니다. 캐시가 없으면 NEIS API를 호출합니다.

        Args:
            day: 조회할 날짜

        Returns:
            list[MealInfo]: 조식 → 중식 → 석식 순서. 급식이 없는 날은 빈 목록

        Raises:
            ExternalServiceError: NEIS API 호출 또는 응답 처리에 실패했을 경우 발생합니다.
        """
        key = Keys.Meal.DAY(date=day.strftime("%Y%m%d"))
        cached = await self.redis.get(key)
        if cached is not None:
            return [MealInfo(**item) for item in cached]

        meals = self.parse_rows(await self._fetch_rows(day))
        # 급식이 없는 날(빈 목록)도 캐시해 주말 · 방학에 NEIS를 반복 호출하지 않습니다. 실패는 캐시하지 않습니다.
        await self.redis.set(key, [meal.model_dump(mode="json") for meal in meals])
        return meals

    async def _fetch_rows(self, day: date) -> list[dict[str, Any]]:
        """
        NEIS API를 호출해 해당 날짜의 식단 행(row)을 가져옵니다.

        Raises:
            ExternalServiceError: 네트워크 오류, 잘못된 응답, 데이터 없음 외의 결과 코드를 받은 경우 발생합니다.
        """
        params = {
            "Type": "json",
            "ATPT_OFCDC_SC_CODE": settings.neis_office_code,
            "SD_SCHUL_CODE": settings.neis_school_code,
            "MLSV_YMD": day.strftime("%Y%m%d"),
        }
        if settings.neis_api_key:
            params["KEY"] = settings.neis_api_key
        else:
            # 키가 없어도 NEIS 샘플 호출(최대 5행)로 하루치(최대 3행)는 받을 수 있어 로컬 개발용으로 허용합니다.
            self.logs.service_meal.warning("NEIS_API_KEY가 설정되지 않아 키 없이 NEIS API를 호출합니다.")

        # 요청 URL에 API 키가 들어가므로, 예외 메시지 · 스택(URL 포함)은 로그에 남기지 않고 종류만 남깁니다.
        try:
            async with httpx.AsyncClient(timeout=NEIS_TIMEOUT_SECONDS) as http:
                response = await http.get(NEIS_MEAL_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            self.logs.service_meal.error(f"급식 조회 실패 - {day} HTTP {e.response.status_code}")
            raise ExternalServiceError("NEIS API 호출에 실패했습니다.")
        except (httpx.HTTPError, ValueError) as e:
            self.logs.service_meal.error(f"급식 조회 실패 - {day} {type(e).__name__}")
            raise ExternalServiceError("NEIS API 호출에 실패했습니다.")

        try:
            return self.extract_rows(data)
        except ExternalServiceError as e:
            self.logs.service_meal.error(f"급식 조회 실패 - {day} {e}")
            raise

    @staticmethod
    def extract_rows(data: Any) -> list[dict[str, Any]]:
        """
        NEIS 응답 JSON에서 식단 행(row) 목록을 꺼냅니다.

        Args:
            data: NEIS `mealServiceDietInfo` 응답 JSON

        Returns:
            list[dict]: 식단 행 목록. 데이터가 없으면(`INFO-200`) 빈 목록

        Raises:
            ExternalServiceError: 응답 형식이 예상과 다르거나, 정상 · 데이터 없음 외의 결과 코드인 경우 발생합니다.
        """
        if not isinstance(data, dict):
            raise ExternalServiceError("NEIS 응답 형식이 올바르지 않습니다.")

        # 결과가 없거나 오류이면 {"RESULT": {...}}만, 정상이면 {"mealServiceDietInfo": [{"head": ...}, {"row": ...}]}
        if "RESULT" in data:
            code = data["RESULT"].get("CODE")
            if code == NEIS_RESULT_NO_DATA:
                return []
            raise ExternalServiceError(f"NEIS 결과 코드 {code}")

        try:
            head, body = data["mealServiceDietInfo"]
            code = next(item["RESULT"]["CODE"] for item in head["head"] if "RESULT" in item)
            rows = body["row"]
        except KeyError, TypeError, ValueError, StopIteration:
            raise ExternalServiceError("NEIS 응답 형식이 올바르지 않습니다.")

        if code != NEIS_RESULT_OK:
            raise ExternalServiceError(f"NEIS 결과 코드 {code}")
        return rows

    @classmethod
    def parse_rows(cls, rows: list[dict[str, Any]]) -> list[MealInfo]:
        """
        NEIS 식단 행 목록을 급식 정보로 바꿉니다. 알 수 없는 급식 종류는 건너뜁니다.

        Args:
            rows: NEIS 식단 행 목록

        Returns:
            list[MealInfo]: 조식 → 중식 → 석식 순서
        """
        order = list(NEIS_MEAL_TYPES.values())
        meals = [
            MealInfo(
                type=NEIS_MEAL_TYPES[row["MMEAL_SC_CODE"]],
                dishes=cls.parse_dishes(row.get("DDISH_NM") or ""),
                calorie=cls.parse_calorie(row.get("CAL_INFO")),
            )
            for row in rows
            if row.get("MMEAL_SC_CODE") in NEIS_MEAL_TYPES
        ]
        return sorted(meals, key=lambda meal: order.index(meal.type))

    @staticmethod
    def parse_dishes(text: str) -> list[MealDish]:
        """
        NEIS 메뉴 문자열을 메뉴 목록으로 바꿉니다.

        `"쌀밥 <br/>국-닭개장 (15)<br/>고기왕만두 (1.5.6.)"`처럼 메뉴는 `<br/>`로 나뉘고,
        메뉴 끝의 괄호 안 숫자는 알레르기 유발 식품 번호입니다.

        Args:
            text: NEIS `DDISH_NM` 값

        Returns:
            list[MealDish]: 메뉴 목록 (빈 줄 제외)
        """
        dishes = []
        for line in _LINE_BREAK.split(text):
            name = unescape(line).strip()
            allergies: list[int] = []
            if match := _ALLERGY_SUFFIX.search(name):
                allergies = [int(n) for n in match.group(1).replace(" ", "").split(".") if n]
                name = name[: match.start()].strip()
            if name:
                dishes.append(MealDish(name=name, allergies=allergies))
        return dishes

    @staticmethod
    def parse_calorie(text: str | None) -> float | None:
        """
        NEIS 열량 문자열(`"848.3 Kcal"`)에서 숫자만 꺼냅니다.

        Args:
            text: NEIS `CAL_INFO` 값

        Returns:
            float | None: 열량(kcal). 값이 없으면 None
        """
        if not text or not (match := _NUMBER.search(text)):
            return None
        return float(match.group())
