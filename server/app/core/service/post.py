from typing import TYPE_CHECKING

from sqlmodel import col, delete, func, select

from app.schemas import PostContent, Posts
from app.schemas.post import PostResponse

from ..cache_events import on_post_changed
from ..core import ServiceCore
from ..database import DatabaseCore
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
                    select(Posts, PostContent.data)
                    .join(PostContent, col(PostContent.post_id) == col(Posts.id))
                    .where(kind_filter)
                    .order_by(col(Posts.id).desc())
                    .offset(offset)
                    .limit(size)
                )
                rows = (await session.execute(query)).all()
            posts = [PostResponse(**post.model_dump(), content_data=data) for post, data in rows]
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

            query = select(Posts).order_by(col(Posts.id).desc()).offset(offset).limit(size)
            rows = (await session.execute(query)).scalars().all()
            posts = [PostResponse.model_validate(post) for post in rows]
            await RedisCore.set(list_cache_key, [post.model_dump(exclude_unset=True) for post in posts])

        return posts, total_count, False

    async def get_content(self) -> dict | None:
        """게시글 본문 데이터를 가져옵니다."""
        async with self.session as session:
            content = await session.get(PostContent, self.id)
            return content.data if content is not None else None

    async def get_detail(self) -> PostResponse:
        """게시글 상세 응답에 메타데이터와 본문을 담습니다."""
        return PostResponse(**self.model_dump(), content_data=await self.get_content())

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

    async def edit(self, *, title: str | None = None, content: dict | None = None):
        """
        게시글을 수정합니다.

        Args:
            title: 게시글의 제목
            content: 게시글의 본문 데이터
        """
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

        await on_post_changed(self.id)
        self._payload = post

        self.logs.service_post.info(f"게시글 수정 - ID {self.id}")
