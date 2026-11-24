from math import ceil

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from app.core import LoginDep, ServiceClient
from app.core.error import Conflict, ExpiredError, NotFound
from app.core.service import Post, User
from app.schemas import PollOperation, PollResponse, PollVote, Posts, UserPermission
from app.schemas.post import PostResponse
from app.schemas.response import ResponseModel, api_responses

router = APIRouter(prefix="/posts", tags=["posts"])
client = ServiceClient()


class PostCreateRequest(BaseModel):
    title: str = Field(..., description="게시글 제목")
    content_data: dict = Field(..., description="게시글의 본문 데이터")
    poll: PollOperation | None = Field(None, description="게시글과 함께 만들 설문 (없으면 설문 없이 작성)")


class PostUpdateRequest(BaseModel):
    title: str | None = Field(None, description="수정할 게시글 제목")
    content_data: dict | None = Field(None, description="수정할 게시글의 본문 데이터")
    poll: PollOperation | None = Field(
        None,
        description="설문. 보내지 않으면 그대로 두고, 객체를 보내면 만들거나 수정하며, null을 보내면 삭제합니다.",
    )


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

    post = await user.create_post(title=request.title, content=request.content_data, poll=request.poll)
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
            409: "응답이 있어 바꿀 수 없는 설문 내용이 포함됨",
        }
    ),
    status_code=status.HTTP_200_OK,
    summary="게시글 수정",
    description="기존 게시글을 수정합니다. poll을 보내면 설문도 같은 트랜잭션에서 만들거나 수정하고, null을 보내면 삭제합니다.",
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

    try:
        await post.edit(
            title=request.title,
            content=request.content_data,
            # 필드를 보냈는지(null 포함)로 '그대로 두기'와 '삭제'를 구분합니다.
            update_poll="poll" in request.model_fields_set,
            poll=request.poll,
        )
    except Conflict as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
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


# ---------- 설문 ----------


def _can_manage_post(user: User, post: Post) -> bool:
    """게시글 작성자이거나 MANAGE_POST 권한이 있는지 확인합니다."""
    return post.author_id == user.id or user.has_permission(UserPermission.MANAGE_POST)


async def _get_post_or_404(post_id: int, *, cache: bool = False) -> Post:
    post = await client.get_post(post_id, cache=cache)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")
    return post


def _require_view_post(user: User):
    if not user.has_permission(UserPermission.VIEW_POST):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")


@router.get(
    "/{post_id}/poll",
    response_model=ResponseModel[PollResponse],
    responses=api_responses(
        {
            200: "설문 조회 성공",
            401: "인증되지 않은 사용자",
            403: "권한이 없음",
            404: "게시글 또는 설문을 찾을 수 없음",
        }
    ),
    status_code=status.HTTP_200_OK,
    summary="설문 조회",
    description="게시글에 연결된 설문과 내 응답을 조회합니다. 선택지별 인원과 응답자 수는 작성자와 MANAGE_POST 권한자에게만 제공합니다.",
)
async def get_poll(post_id: int, auth: LoginDep):
    user, _ = auth
    post = await _get_post_or_404(post_id, cache=True)
    can_manage = _can_manage_post(user, post)
    if not can_manage:
        _require_view_post(user)

    try:
        poll = await post.get_poll(user_id=user.id, show_result=can_manage)
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="설문이 없습니다.")
    return ResponseModel[PollResponse](success=True, data=poll)


@router.put(
    "/{post_id}/poll",
    response_model=ResponseModel[PollResponse],
    responses=api_responses(
        {
            200: "설문 저장 완료",
            401: "인증되지 않은 사용자",
            403: "권한이 없음",
            404: "게시글을 찾을 수 없음",
            409: "응답이 있어 바꿀 수 없는 내용이 포함됨",
        }
    ),
    status_code=status.HTTP_200_OK,
    summary="설문 저장",
    description="게시글에 설문을 만들거나 수정합니다. 응답이 있는 설문은 선택지를 바꿀 수 없습니다.",
)
async def set_poll(post_id: int, request: PollOperation, auth: LoginDep):
    user, _ = auth
    post = await _get_post_or_404(post_id)
    if not _can_manage_post(user, post):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    try:
        await post.set_poll(request)
    except Conflict as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return ResponseModel[PollResponse](success=True, data=await post.get_poll(user_id=user.id, show_result=True))


@router.delete(
    "/{post_id}/poll",
    responses=api_responses(
        {
            204: "설문 삭제 완료",
            401: "인증되지 않은 사용자",
            403: "권한이 없음",
            404: "게시글 또는 설문을 찾을 수 없음",
        }
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    summary="설문 삭제",
    description="게시글의 설문과 모든 응답을 삭제합니다.",
)
async def delete_poll(post_id: int, auth: LoginDep):
    user, _ = auth
    post = await _get_post_or_404(post_id)
    if not _can_manage_post(user, post):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    try:
        await post.delete_poll()
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="설문이 없습니다.")


@router.put(
    "/{post_id}/poll/vote",
    response_model=ResponseModel[PollResponse],
    responses=api_responses(
        {
            200: "설문 응답 완료",
            400: "마감되었거나 잘못된 선택",
            401: "인증되지 않은 사용자",
            403: "권한이 없음",
            404: "게시글 또는 설문을 찾을 수 없음",
        }
    ),
    status_code=status.HTTP_200_OK,
    summary="설문 응답",
    description="설문에 응답합니다. 이미 응답했다면 새 선택으로 바꿉니다. 마감된 설문에는 응답할 수 없습니다.",
)
async def vote_poll(post_id: int, request: PollVote, auth: LoginDep):
    user, _ = auth
    _require_view_post(user)
    post = await _get_post_or_404(post_id, cache=True)

    try:
        await post.vote(user_id=user.id, option_ids=request.option_ids)
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="설문이 없습니다.")
    except ExpiredError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="마감된 설문입니다.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    poll = await post.get_poll(user_id=user.id, show_result=_can_manage_post(user, post))
    return ResponseModel[PollResponse](success=True, data=poll)


@router.delete(
    "/{post_id}/poll/vote",
    responses=api_responses(
        {
            204: "설문 응답 취소 완료",
            400: "마감된 설문",
            401: "인증되지 않은 사용자",
            403: "권한이 없음",
            404: "게시글 또는 설문을 찾을 수 없음",
        }
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    summary="설문 응답 취소",
    description="내 설문 응답을 취소합니다. 마감된 설문은 취소할 수 없습니다.",
)
async def cancel_poll_vote(post_id: int, auth: LoginDep):
    user, _ = auth
    _require_view_post(user)
    post = await _get_post_or_404(post_id, cache=True)

    try:
        await post.cancel_vote(user_id=user.id)
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="설문이 없습니다.")
    except ExpiredError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="마감된 설문입니다.")
