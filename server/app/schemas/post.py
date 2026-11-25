from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, StringConstraints, field_serializer, field_validator
from sqlalchemy import Column, DateTime, Index, func
from sqlmodel import JSON, Field, ForeignKey, Integer, Relationship, SQLModel

from .core import SchemaCore

if TYPE_CHECKING:
    from .users import Users

# TODO: 사용자 수정과 등등 처리 로그 추가 좀 (26.08.07 1:37)


class Post(SQLModel):
    id: int | None = Field(
        primary_key=True,
        default=None,
        description="게시글 고유 ID",
        index=True,
    )  # autoincrement

    title: str = Field(..., description="게시글 제목")
    views: int = Field(default=0, description="게시글 조회수")

    # 시간 관련 데이터
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(SchemaCore.timezone),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="게시글이 작성된 시간",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(SchemaCore.timezone),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
        ),
        description="게시글이 수정된 마지막 시간",
    )

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: Any, _info):
        if isinstance(dt, datetime):
            return SchemaCore.sync_timezone(dt).isoformat()
        return dt


class Posts(Post, table=True):
    content: "PostContent" = Relationship(
        back_populates="post",
        sa_relationship_kwargs={"uselist": False},
        passive_deletes=True,
    )

    author: Users = Relationship(back_populates="posts")
    author_id: int = Field(
        foreign_key="users.id",
        ondelete="CASCADE",
        index=True,
        description="게시글 작성자의 고유 ID",
    )


class PostResponse(Post):
    author_id: int = Field(description="게시글 작성자의 고유 ID")
    content_data: dict | None = Field(default=None, description="게시글의 본문 JSON 데이터")
    has_poll: bool = Field(default=False, description="설문이 연결되어 있는지 여부")


class PostContent(SQLModel, table=True):
    # 관계
    post: Posts = Relationship(back_populates="content")
    post_id: int = Field(
        sa_column=Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
        description="연결된 게시글 고유 ID",
    )

    # JSON 내용
    data: dict = Field(..., description="게시글의 내용 JSON 데이터", sa_column=Column(JSON))


class PostPolls(SQLModel, table=True):
    # 공지 하나에 설문 하나만 둘 수 있도록 게시글 ID를 기본 키로 사용합니다.
    post_id: int = Field(
        sa_column=Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
        description="설문이 연결된 게시글 고유 ID",
    )
    question: str = Field(..., max_length=200, description="설문 질문")
    allow_multiple: bool = Field(default=False, description="복수 선택 허용 여부")
    closes_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="설문 마감 시각 (없으면 마감 없음)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(SchemaCore.timezone),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="설문이 만들어진 시간",
    )


class PostPollOptions(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None, description="설문 선택지 고유 ID")
    post_id: int = Field(
        foreign_key="postpolls.post_id",
        ondelete="CASCADE",
        index=True,
        description="선택지가 속한 설문(게시글) ID",
    )
    text: str = Field(..., max_length=100, description="선택지 내용")
    order: int = Field(default=0, description="선택지 표시 순서")


class PostPollVotes(SQLModel, table=True):
    __table_args__ = (Index("ix_postpollvotes_post_id_user_id", "post_id", "user_id"),)

    option_id: int = Field(
        sa_column=Column(Integer, ForeignKey("postpolloptions.id", ondelete="CASCADE"), primary_key=True),
        description="선택한 선택지 ID",
    )
    user_id: int = Field(
        sa_column=Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        description="응답한 유저 ID",
    )
    post_id: int = Field(
        foreign_key="postpolls.post_id",
        ondelete="CASCADE",
        description="응답한 설문(게시글) ID",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(SchemaCore.timezone),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="응답한 시간",
    )


class PollOptionResponse(SQLModel):
    id: int = Field(description="선택지 고유 ID")
    text: str = Field(description="선택지 내용")
    votes: int | None = Field(default=None, description="선택한 인원 수 (작성자·관리 권한자에게만 제공)")


class PollResponse(SQLModel):
    post_id: int = Field(description="설문이 연결된 게시글 고유 ID")
    question: str = Field(description="설문 질문")
    allow_multiple: bool = Field(description="복수 선택 허용 여부")
    closes_at: datetime | None = Field(default=None, description="설문 마감 시각 (없으면 마감 없음)")
    closed: bool = Field(description="마감 여부")
    options: list[PollOptionResponse] = Field(description="선택지 목록 (표시 순서)")
    my_option_ids: list[int] = Field(description="요청한 유저가 선택한 선택지 ID 목록")
    voter_count: int | None = Field(default=None, description="응답자 수 (작성자·관리 권한자에게만 제공)")

    @field_serializer("closes_at")
    def serialize_dt(self, dt: Any, _info):
        if isinstance(dt, datetime):
            return SchemaCore.sync_timezone(dt).isoformat()
        return dt


POLL_OPTION_MIN = 2
POLL_OPTION_MAX = 10

PollOptionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class PollOperation(BaseModel):
    question: str = Field(..., min_length=1, max_length=200, description="설문 질문")
    options: list[PollOptionText] = Field(
        ...,
        min_length=POLL_OPTION_MIN,
        max_length=POLL_OPTION_MAX,
        description=f"선택지 내용 목록 ({POLL_OPTION_MIN}~{POLL_OPTION_MAX}개, 각 1~100자, 중복 불가)",
    )
    allow_multiple: bool = Field(False, description="복수 선택 허용 여부")
    closes_at: datetime | None = Field(None, description="설문 마감 시각 (없으면 마감 없음)")

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("설문 질문을 입력해주세요.")
        return value

    @field_validator("options")
    @classmethod
    def check_duplicate_options(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("중복된 선택지가 있습니다.")
        return value


class PollVote(BaseModel):
    option_ids: list[int] = Field(..., min_length=1, max_length=POLL_OPTION_MAX, description="선택한 선택지 ID 목록")
