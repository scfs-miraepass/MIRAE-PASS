from math import ceil

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from app.core import LoginDep, ServiceClient
from app.core.service import Post
from app.schemas import Posts, UserPermission
from app.schemas.post import PostResponse
from app.schemas.response import ResponseModel, api_responses

router = APIRouter(prefix="/posts", tags=["posts"])
client = ServiceClient()


class PostCreateRequest(BaseModel):
    title: str = Field(..., description="게시글 제목")
    content_data: dict = Field(..., description="게시글의 본문 데이터")


class PostUpdateRequest(BaseModel):
    title: str | None = Field(None, description="수정할 게시글 제목")
    content_data: dict | None = Field(None, description="수정할 게시글의 본문 데이터")


@router.get(
    "",
    response_model=ResponseModel[list[PostResponse]],
    responses=api_responses(
        {
            200: "게시글 목록 조회 성공",
            401: "인증되지 않은 사용자",
            403: "권한이 없음",
        }
    ),
    status_code=status.HTTP_200_OK,
    summary="게시글 목록 조회",
    description="게시글 목록을 페이징하여 조회합니다. 본문 유형을 지정하면 해당 게시글의 본문도 반환합니다.",
)
async def get_posts(
    response: Response,
    auth: LoginDep,
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 당 게시글 데이터 갯수 (최대 100)"),
    content_kind: str | None = Query(None, description="필터링할 게시글 본문 유형"),
):
    user, _ = auth
    can_manage_notices = content_kind == "notice" and (
        user.has_permission(UserPermission.MANAGE_POST) or user.has_permission(UserPermission.CREATE_POST)
    )
    if not user.has_permission(UserPermission.VIEW_POST) and not can_manage_notices:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied.",
        )

    posts, total_count, cached = await Post.list_posts(page=page, size=size, content_kind=content_kind)
    response.headers["X-MAX-PAGE"] = str(max(1, ceil(total_count / size)))
    response.headers["X-CACHED"] = str(cached).lower()

    return ResponseModel[list[PostResponse]](success=True, data=posts)


@router.get(
    "/{post_id}",
    response_model=ResponseModel[PostResponse],
    responses=api_responses(
        {
            200: "게시글 상세 조회 성공",
            401: "인증되지 않은 사용자",
            404: "게시글을 찾을 수 없음",
            403: "권한이 없음",
        }
    ),
    status_code=status.HTTP_200_OK,
    summary="게시글 단일 조회",
    description="특정 ID의 게시글 상세 정보를 조회합니다.",
)
async def get_post(post_id: int, auth: LoginDep):
    user, _ = auth

    if not user.has_permission(UserPermission.VIEW_POST):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied.",
        )

    post = await client.get_post(post_id, cache=True)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found.",
        )

    return ResponseModel[PostResponse](success=True, data=await post.get_detail())


@router.post(
    "",
    response_model=ResponseModel[Posts],
    responses=api_responses(
        {
            201: "게시글 작성 완료",
            401: "인증되지 않은 사용자",
            403: "권한이 없음",
        }
    ),
    status_code=status.HTTP_201_CREATED,
    summary="게시글 작성",
    description="새로운 게시글을 작성합니다.",
)
async def create_post(request: PostCreateRequest, auth_data: LoginDep):
    user, _ = auth_data

    if not user.has_permission(UserPermission.CREATE_POST):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied.",
        )

    post = await user.create_post(title=request.title, content=request.content_data)
    return ResponseModel[Posts](success=True, data=post)


@router.patch(
    "/{post_id}",
    response_model=ResponseModel[Posts],
    responses=api_responses(
        {
            200: "게시글 수정 완료",
            401: "인증되지 않은 사용자",
            403: "권한이 없음",
            404: "게시글을 찾을 수 없음",
        }
    ),
    status_code=status.HTTP_200_OK,
    summary="게시글 수정",
    description="기존 게시글을 수정합니다.",
)
async def update_post(post_id: int, request: PostUpdateRequest, auth_data: LoginDep):
    user, _ = auth_data
    post = await client.get_post(post_id)

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found.",
        )
    if not user.has_permission(UserPermission.MANAGE_POST) and post.author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied.",
        )

    await post.edit(title=request.title, content=request.content_data)
    return ResponseModel[Posts](success=True, data=post)


@router.delete(
    "/{post_id}",
    responses=api_responses(
        {
            204: "게시글 삭제 완료",
            401: "인증되지 않은 사용자",
            403: "권한이 없음",
            404: "게시글을 찾을 수 없음",
        }
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    summary="게시글 삭제",
    description="기존 게시글을 삭제합니다.",
)
async def delete_post(
    post_id: int,
    auth_data: LoginDep,
):
    user, _ = auth_data
    post = await client.get_post(post_id)

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found.",
        )
    if not user.has_permission(UserPermission.MANAGE_POST) and post.author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied.",
        )

    await post.delete()
