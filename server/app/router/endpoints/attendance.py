from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core import LoginDep
from app.core.error import Conflict, ServiceUnavailable
from app.schemas import AttendanceResult, AttendanceStatus, UserPermission
from app.schemas.response import ResponseModel, api_responses

router = APIRouter(prefix="/attendance", tags=["attendance"])

ATTENDANCE_UNAVAILABLE_MESSAGE = "학사일정을 확인할 수 없어 지금은 출석할 수 없어요. 잠시 후 다시 시도해 주세요."


@router.get(
    "",
    response_model=ResponseModel[AttendanceStatus],
    responses=api_responses(
        {
            200: "출석체크 상태 조회 성공",
            401: "세션이 만료되었거나 유효하지 않음",
            403: "권한이 없음",
            503: "학사일정(NEIS)을 확인할 수 없음",
        }
    ),
    status_code=status.HTTP_200_OK,
    summary="출석체크 상태 조회",
    description="오늘 출석할 수 있는지, 이미 출석했는지, 현재 연속 출석 일수와 다음 보너스까지 남은 일수를 조회합니다.",
)
async def get_attendance(auth_data: LoginDep):
    user, _ = auth_data

    if not user.has_permission(UserPermission.CHECK_ATTENDANCE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="출석체크 권한이 없어요.")

    try:
        result = await user.get_attendance_status()
    except ServiceUnavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=ATTENDANCE_UNAVAILABLE_MESSAGE)

    return ResponseModel(success=True, data=result)


@router.post(
    "",
    response_model=ResponseModel[AttendanceResult],
    responses=api_responses(
        {
            201: "출석체크 성공",
            400: "오늘은 출석할 수 없는 날 (주말 · 휴업일 · 공휴일)",
            401: "세션이 만료되었거나 유효하지 않음",
            403: "권한이 없음",
            409: "오늘 이미 출석함",
            503: "학사일정(NEIS)을 확인할 수 없음",
        }
    ),
    status_code=status.HTTP_201_CREATED,
    summary="출석체크",
    description=(
        "오늘 출석하고 포인트를 받습니다. 평일 중 휴업일 · 공휴일이 아닌 날에 하루 한 번 출석할 수 있습니다.\n\n"
        "출석하면 10포인트를 받고, 연속 출석 일수가 11의 배수(11, 22, ...)인 날은 10포인트 대신 100포인트를 받습니다."
    ),
)
async def check_attendance(auth_data: LoginDep):
    user, _ = auth_data

    if not user.has_permission(UserPermission.CHECK_ATTENDANCE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="출석체크 권한이 없어요.")

    try:
        result = await user.attend()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Conflict, IntegrityError:
        # IntegrityError: 동시에 들어온 요청이 (유저, 날짜) 유니크 제약에 걸린 경우
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="오늘은 이미 출석했어요.")
    except ServiceUnavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=ATTENDANCE_UNAVAILABLE_MESSAGE)

    return ResponseModel(success=True, data=result)
