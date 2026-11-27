from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.core import LoginDep, ServiceClient
from app.core.error import ExternalServiceError
from app.schemas import MealInfo, UserPermission
from app.schemas.response import ResponseModel, api_responses

router = APIRouter(prefix="/meal", tags=["meal"])
client = ServiceClient()
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


@router.get(
    "",
    response_model=ResponseModel[list[MealInfo]],
    responses=api_responses(
        {
            200: "급식 조회 성공",
            400: "존재하지 않는 날짜",
            401: "세션이 만료되었거나 유효하지 않음",
            403: "권한이 없음",
            502: "NEIS에서 급식 정보를 가져오지 못함",
        }
    ),
    status_code=status.HTTP_200_OK,
    summary="급식 조회",
    description=(
        "해당 날짜의 학교 급식(조식 · 중식 · 석식)을 조회합니다. "
        "`date`를 생략하면 학교 기준(KST) 오늘입니다. 급식이 없는 날은 빈 목록을 반환합니다. "
        "NEIS 교육정보 개방 포털의 데이터를 날짜별로 1시간 동안 캐시합니다."
    ),
)
async def get_meals(
    auth_data: LoginDep,
    # date 타입으로 받으면 SDK의 TS 타입(Date)과 요청 검증(YYYY-MM-DD 문자열)이 어긋나므로 문자열로 받아 직접 변환합니다.
    day: str | None = Query(
        None, alias="date", pattern=DATE_PATTERN, description="조회할 날짜 (YYYY-MM-DD). 생략하면 오늘"
    ),
):
    user, _ = auth_data
    if not user.has_permission(UserPermission.VIEW_MEAL):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    try:
        target = date.fromisoformat(day) if day else None
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="올바른 날짜가 아니에요.")

    try:
        meals = await client.get_meals(target)
    except ExternalServiceError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="급식 정보를 불러오지 못했어요.")

    return ResponseModel(success=True, data=meals)
