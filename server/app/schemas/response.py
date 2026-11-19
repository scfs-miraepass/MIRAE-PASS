from http import HTTPStatus
from typing import Any, TypeVar

from pydantic import BaseModel, Field

Data = TypeVar("Data")


class ResponsePayload(BaseModel):
    success: bool


class ResponseModel[Data](ResponsePayload):
    data: Data = Field(description="응답 데이터")


class ErrorResponse(ResponsePayload):
    message: str = Field(description="에러 메시지")


def api_responses(descriptions: dict[int, str]) -> dict[int | str, dict[str, Any]]:
    """
    상태 코드별 설명으로 엔드포인트 데코레이터의 `responses`를 만듭니다.
    400 이상의 실패 응답에는 `ErrorResponse` 모델을 붙입니다.
    """
    responses: dict[int | str, dict[str, Any]] = {}
    for code, description in descriptions.items():
        if code >= HTTPStatus.BAD_REQUEST:
            responses[code] = {"model": ErrorResponse, "description": description}
        else:
            responses[code] = {"description": description}
    return responses
