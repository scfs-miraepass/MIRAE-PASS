from enum import StrEnum

from pydantic import BaseModel, Field


class MealType(StrEnum):
    """급식 종류 (NEIS `MMEAL_SC_CODE` 1 · 2 · 3)"""

    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"


class MealDish(BaseModel):
    name: str = Field(..., description="메뉴 이름")
    allergies: list[int] = Field(default_factory=list, description="알레르기 유발 식품 번호 (NEIS 기준 1~19)")


class MealInfo(BaseModel):
    type: MealType = Field(..., description="급식 종류 (breakfast: 조식, lunch: 중식, dinner: 석식)")
    dishes: list[MealDish] = Field(default_factory=list, description="메뉴 목록 (식단표 순서)")
    calorie: float | None = Field(None, ge=0, description="열량 (kcal). NEIS에 정보가 없으면 null")
