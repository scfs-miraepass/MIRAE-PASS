import type { PostResponse } from "@miraepass/api-client";

// 공지 게시글의 content_data.kind 값
export const NOTICE_CONTENT_KIND = "notice";

// 화면에 표시할 공지. PostResponse 중 content_data가 { kind: "notice", text } 형태인 게시글에 대응한다.
export interface NoticeItem {
    id: number;
    title: string;
    text: string;
    createdAt: Date | null;
    edited: boolean;
}

// 작성 후 이 시간(ms)보다 늦게 수정된 경우에만 '수정됨'으로 표시한다. (작성 직후 updated_at이 조금 다를 수 있음)
const NOTICE_EDITED_THRESHOLD = 60 * 1000;

const toValidDate = (value?: Date | string | null) => {
    if (value == null) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
};

// 게시글을 공지로 변환한다. 공지 형식이 아니면 null을 돌려준다.
export const toNoticeItem = (post: PostResponse): NoticeItem | null => {
    const content = post.content_data;
    if (post.id == null || content?.kind !== NOTICE_CONTENT_KIND || typeof content.text !== "string") return null;

    const createdAt = toValidDate(post.created_at);
    const updatedAt = toValidDate(post.updated_at);
    return {
        id: post.id,
        title: post.title,
        text: content.text,
        createdAt,
        edited: createdAt != null && updatedAt != null && updatedAt.getTime() - createdAt.getTime() > NOTICE_EDITED_THRESHOLD,
    };
};

// 게시글 목록에서 공지 형식인 것만 골라 변환한다.
export const toNoticeItems = (posts: PostResponse[]) =>
    posts.flatMap((post) => {
        const notice = toNoticeItem(post);
        return notice ? [notice] : [];
    });

// 목록용 짧은 날짜. 올해면 "11월 24일", 아니면 "2025. 11. 24."
export const noticeDateLabel = (date: Date | null, now = new Date()) => {
    if (!date) return "";
    if (date.getFullYear() === now.getFullYear()) return `${date.getMonth() + 1}월 ${date.getDate()}일`;
    return date.toLocaleDateString("ko-KR");
};

// 상세 화면용 날짜와 시각. 예: "2026년 11월 24일 오후 3:20"
export const noticeDateTimeLabel = (date: Date | null) =>
    date
        ? date.toLocaleString("ko-KR", {
              year: "numeric",
              month: "long",
              day: "numeric",
              hour: "numeric",
              minute: "2-digit",
          })
        : "";
