from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, delete, func, select

from app.schemas import (
    PollOperation,
    PollOptionResponse,
    PollResponse,
    PostContent,
    PostPollOptions,
    PostPolls,
    PostPollVotes,
    Posts,
)
from app.schemas.core import SchemaCore
from app.schemas.post import PostResponse

from ..cache_events import on_post_changed
from ..core import ServiceCore
from ..database import DatabaseCore
from ..error import Conflict, ExpiredError, NotFound
from ..redis import RedisCore
from ..redis_keys import Keys

if TYPE_CHECKING:
    _Type = Posts
else:
    _Type = object


class Post(ServiceCore[Posts], _Type):
    @staticmethod
    async def list_posts(*, page: int, size: int, content_kind: str | None) -> tuple[list[PostResponse], int, bool]:
        """게시글 목록과 전체 개수를 조회합니다."""
        offset = (page - 1) * size
        if content_kind is not None:
            kind_filter = PostContent.data["kind"].as_string() == content_kind
            async with DatabaseCore.session() as session:
                count_query = select(func.count()).select_from(PostContent).where(kind_filter)
                total_count = (await session.execute(count_query)).scalar_one()
                query = (
                    select(Posts, PostContent.data, col(PostPolls.post_id).is_not(None))
                    .join(PostContent, col(PostContent.post_id) == col(Posts.id))
                    .outerjoin(PostPolls, col(PostPolls.post_id) == col(Posts.id))
                    .where(kind_filter)
                    .order_by(col(Posts.id).desc())
                    .offset(offset)
                    .limit(size)
                )
                rows = (await session.execute(query)).all()
            posts = [
                PostResponse(**post.model_dump(), content_data=data, has_poll=has_poll) for post, data, has_poll in rows
            ]
            return posts, total_count, False

        count_cache_key = Keys.Post.COUNT()
        cached_count = await RedisCore.get(count_cache_key)
        list_version = await RedisCore.get_version(Keys.Post.VERSION())
        list_cache_key = Keys.Post.PAGE(ver=list_version, page=page, size=size)
        cached_posts = await RedisCore.get(list_cache_key)

        async with DatabaseCore.session() as session:
            if cached_count is None:
                count_query = select(func.count()).select_from(Posts)
                total_count = (await session.execute(count_query)).scalar_one()
                await RedisCore.set(count_cache_key, total_count)
            else:
                total_count = int(cached_count)

            if cached_posts is not None:
                return [PostResponse.model_validate(post) for post in cached_posts], total_count, True

            query = (
                select(Posts, col(PostPolls.post_id).is_not(None))
                .outerjoin(PostPolls, col(PostPolls.post_id) == col(Posts.id))
                .order_by(col(Posts.id).desc())
                .offset(offset)
                .limit(size)
            )
            rows = (await session.execute(query)).all()
            posts = [PostResponse(**post.model_dump(), has_poll=has_poll) for post, has_poll in rows]
            await RedisCore.set(list_cache_key, [post.model_dump(exclude_unset=True) for post in posts])

        return posts, total_count, False

    async def get_content(self) -> dict | None:
        """게시글 본문 데이터를 가져옵니다."""
        async with self.session as session:
            content = await session.get(PostContent, self.id)
            return content.data if content is not None else None

    async def get_detail(self) -> PostResponse:
        """게시글 상세 응답에 메타데이터, 본문, 설문 유무를 담습니다."""
        async with self.session as session:
            has_poll = await session.get(PostPolls, self.id) is not None
        return PostResponse(**self.model_dump(), content_data=await self.get_content(), has_poll=has_poll)

    # ---------- 설문 ----------

    @staticmethod
    def _is_closed(poll: PostPolls) -> bool:
        """마감 시각이 지났는지 확인합니다. DB 값은 시간대가 없을 수 있어 sync_timezone으로 맞춰 비교합니다."""
        return poll.closes_at is not None and SchemaCore.sync_timezone(poll.closes_at) <= SchemaCore.now()

    @staticmethod
    def _to_db_time(value: datetime | None) -> datetime | None:
        """요청으로 받은 마감 시각을 DB 서버 시간대로 맞춥니다. (DB DATETIME에는 시간대가 저장되지 않음)"""
        return SchemaCore.sync_timezone(value) if value is not None else None

    @classmethod
    async def add_poll(cls, session: AsyncSession, post_id: int, poll: PollOperation):
        """
        열린 세션에 설문과 선택지를 추가합니다. 게시글 작성과 같은 트랜잭션에서 쓰기 위해 세션을 받습니다.

        Args:
            session: 사용할 DB 세션
            post_id: 설문을 연결할 게시글 ID
            poll: 설문 내용
        """
        session.add(
            PostPolls(
                post_id=post_id,
                question=poll.question,
                allow_multiple=poll.allow_multiple,
                closes_at=cls._to_db_time(poll.closes_at),
            )
        )
        await session.flush()
        session.add_all(
            PostPollOptions(post_id=post_id, text=text, order=order) for order, text in enumerate(poll.options)
        )
        await session.flush()

    async def get_poll(self, *, user_id: int, show_result: bool) -> PollResponse:
        """
        게시글에 연결된 설문을 조회합니다.

        Args:
            user_id: 요청한 유저 ID (내가 고른 선택지를 채우는 데 사용)
            show_result: 선택지별 인원과 응답자 수를 포함할지 여부

        Raises:
            NotFound: 설문이 없는 경우 발생합니다.
        """
        async with self.session as session:
            poll = await session.get(PostPolls, self.id)
            if poll is None:
                raise NotFound("설문이 없습니다.")

            options = (
                (
                    await session.execute(
                        select(PostPollOptions)
                        .where(col(PostPollOptions.post_id) == self.id)
                        .order_by(col(PostPollOptions.order), col(PostPollOptions.id))
                    )
                )
                .scalars()
                .all()
            )

            my_option_ids = (
                (
                    await session.execute(
                        select(PostPollVotes.option_id).where(
                            col(PostPollVotes.post_id) == self.id, col(PostPollVotes.user_id) == user_id
                        )
                    )
                )
                .scalars()
                .all()
            )

            counts: dict[int, int] = {}
            voter_count: int | None = None
            if show_result:
                count_rows = (
                    await session.execute(
                        select(PostPollVotes.option_id, func.count())
                        .where(col(PostPollVotes.post_id) == self.id)
                        .group_by(col(PostPollVotes.option_id))
                    )
                ).all()
                counts = {option_id: count for option_id, count in count_rows}
                voter_count = (
                    await session.execute(
                        select(func.count(func.distinct(PostPollVotes.user_id))).where(
                            col(PostPollVotes.post_id) == self.id
                        )
                    )
                ).scalar_one()

        return PollResponse(
            post_id=poll.post_id,
            question=poll.question,
            allow_multiple=poll.allow_multiple,
            closes_at=poll.closes_at,
            closed=self._is_closed(poll),
            options=[
                PollOptionResponse(
                    id=option.id,
                    text=option.text,
                    votes=counts.get(option.id, 0) if show_result else None,
                )
                for option in options
            ],
            my_option_ids=list(my_option_ids),
            voter_count=voter_count,
        )

    async def _save_poll(self, session: AsyncSession, poll: PollOperation) -> bool:
        """
        열린 세션에서 설문을 만들거나 수정합니다. 캐시 무효화와 로그는 호출한 쪽에서 커밋 후 처리합니다.

        응답이 있는 설문은 이미 고른 선택지의 의미가 바뀌지 않도록 선택지를 바꿀 수 없고,
        질문·복수 선택 여부·마감 시각만 바꿀 수 있습니다.

        Returns:
            새로 만들었으면 True, 기존 설문을 수정했으면 False

        Raises:
            Conflict: 응답이 있는 설문의 선택지를 바꾸려는 경우 발생합니다.
        """
        # 같은 설문에 대한 응답 저장과 동시에 실행되지 않도록 설문 행을 잠급니다.
        current = (
            await session.execute(select(PostPolls).where(col(PostPolls.post_id) == self.id).with_for_update())
        ).scalar_one_or_none()

        if current is None:
            await self.add_poll(session, self.id, poll)
            created = True
        else:
            created = False
            options = (
                (
                    await session.execute(
                        select(PostPollOptions)
                        .where(col(PostPollOptions.post_id) == self.id)
                        .order_by(col(PostPollOptions.order), col(PostPollOptions.id))
                    )
                )
                .scalars()
                .all()
            )

            if [option.text for option in options] != poll.options:
                has_votes = (
                    await session.execute(
                        select(func.count()).select_from(PostPollVotes).where(col(PostPollVotes.post_id) == self.id)
                    )
                ).scalar_one() > 0
                if has_votes:
                    raise Conflict("응답이 있는 설문은 선택지를 바꿀 수 없습니다.")

                await session.execute(delete(PostPollOptions).where(col(PostPollOptions.post_id) == self.id))
                session.add_all(
                    PostPollOptions(post_id=self.id, text=text, order=order) for order, text in enumerate(poll.options)
                )

            current.question = poll.question
            current.closes_at = self._to_db_time(poll.closes_at)
            if current.allow_multiple and not poll.allow_multiple:
                # 복수 선택을 끄면 이미 여러 개를 고른 응답이 규칙과 맞지 않게 되므로 막습니다.
                multi_voters = (
                    await session.execute(
                        select(PostPollVotes.user_id)
                        .where(col(PostPollVotes.post_id) == self.id)
                        .group_by(col(PostPollVotes.user_id))
                        .having(func.count() > 1)
                        .limit(1)
                    )
                ).first()
                if multi_voters is not None:
                    raise Conflict("여러 개를 고른 응답이 있어 복수 선택을 끌 수 없습니다.")
            current.allow_multiple = poll.allow_multiple
            await session.flush()
        return created

    async def _remove_poll(self, session: AsyncSession) -> bool:
        """열린 세션에서 설문과 응답을 삭제합니다. 삭제했으면 True, 설문이 없었으면 False를 돌려줍니다."""
        result = await session.execute(delete(PostPolls).where(col(PostPolls.post_id) == self.id))
        return result.rowcount > 0

    async def vote(self, *, user_id: int, option_ids: list[int]):
        """
        설문 응답을 저장합니다. 이미 응답했다면 새 선택으로 바꿉니다.

        Args:
            user_id: 응답하는 유저 ID
            option_ids: 선택한 선택지 ID 목록

        Raises:
            NotFound: 설문이 없는 경우 발생합니다.
            ExpiredError: 설문이 마감된 경우 발생합니다.
            ValueError: 이 설문의 선택지가 아니거나, 복수 선택이 꺼져 있는데 여러 개를 고른 경우 발생합니다.
        """
        selected = set(option_ids)
        async with self.session as session:
            # 설문 수정·같은 유저의 중복 요청과 겹치지 않도록 설문 행을 잠급니다.
            poll = (
                await session.execute(select(PostPolls).where(col(PostPolls.post_id) == self.id).with_for_update())
            ).scalar_one_or_none()
            if poll is None:
                raise NotFound("설문이 없습니다.")
            if self._is_closed(poll):
                raise ExpiredError("마감된 설문입니다.")
            if len(selected) > 1 and not poll.allow_multiple:
                raise ValueError("하나의 선택지만 고를 수 있습니다.")

            valid_ids = set(
                (
                    await session.execute(
                        select(PostPollOptions.id).where(
                            col(PostPollOptions.post_id) == self.id, col(PostPollOptions.id).in_(selected)
                        )
                    )
                ).scalars()
            )
            if valid_ids != selected:
                raise ValueError("이 설문의 선택지가 아닙니다.")

            await session.execute(
                delete(PostPollVotes).where(
                    col(PostPollVotes.post_id) == self.id, col(PostPollVotes.user_id) == user_id
                )
            )
            session.add_all(
                PostPollVotes(option_id=option_id, user_id=user_id, post_id=self.id) for option_id in sorted(selected)
            )

        self.logs.service_post.info(f"설문 응답 - 게시글 ID {self.id}, 유저 ID {user_id}")

    async def cancel_vote(self, *, user_id: int):
        """
        설문 응답을 취소합니다. 응답하지 않은 경우에도 오류 없이 끝납니다.

        Args:
            user_id: 응답을 취소하는 유저 ID

        Raises:
            NotFound: 설문이 없는 경우 발생합니다.
            ExpiredError: 설문이 마감된 경우 발생합니다.
        """
        async with self.session as session:
            poll = (
                await session.execute(select(PostPolls).where(col(PostPolls.post_id) == self.id).with_for_update())
            ).scalar_one_or_none()
            if poll is None:
                raise NotFound("설문이 없습니다.")
            if self._is_closed(poll):
                raise ExpiredError("마감된 설문입니다.")

            await session.execute(
                delete(PostPollVotes).where(
                    col(PostPollVotes.post_id) == self.id, col(PostPollVotes.user_id) == user_id
                )
            )

        self.logs.service_post.info(f"설문 응답 취소 - 게시글 ID {self.id}, 유저 ID {user_id}")

    async def delete(self):
        """
        게시글을 삭제합니다.
        """
        async with self.session as session:
            exc = delete(Posts).where(col(Posts.id) == self.id)
            await session.execute(exc)

        await on_post_changed(self.id, count=True)

        self.logs.service_post.info(
            f"게시글 삭제 - ID {self.id}({self.title[:10] + '...' if len(self.title) > 10 else self.title})"
        )

    async def edit(
        self,
        *,
        title: str | None = None,
        content: dict | None = None,
        update_poll: bool = False,
        poll: PollOperation | None = None,
    ):
        """
        게시글을 수정합니다. 설문도 함께 바꾸는 경우 게시글과 같은 트랜잭션에서 처리해,
        설문 저장이 실패하면 게시글 수정도 함께 취소됩니다.

        Args:
            title: 게시글의 제목
            content: 게시글의 본문 데이터
            update_poll: 설문을 바꿀지 여부. False면 설문은 그대로 둡니다.
            poll: update_poll이 True일 때 저장할 설문. None이면 설문을 삭제합니다. (설문이 없어도 오류 없음)

        Raises:
            Conflict: 응답이 있는 설문의 선택지를 바꾸려는 경우 발생합니다.
        """
        poll_log = ""
        async with self.session as session:
            post = await session.merge(self._payload)
            if title is not None:
                post.title = title

            if content is not None:
                post_content = await session.get(PostContent, post.id)
                if post_content is not None:
                    post_content.data = content
                else:
                    post.content = PostContent(data=content)
            await session.flush()

            if update_poll:
                if poll is not None:
                    poll_log = ", 설문 생성" if await self._save_poll(session, poll) else ", 설문 수정"
                elif await self._remove_poll(session):
                    poll_log = ", 설문 삭제"

        await on_post_changed(self.id)
        self._payload = post

        self.logs.service_post.info(f"게시글 수정 - ID {self.id}{poll_log}")
