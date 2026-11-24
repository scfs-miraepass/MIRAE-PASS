import type { PostResponse } from "@miraepass/api-client";

// 공지 게시글의 content_data.kind 값
export const NOTICE_CONTENT_KIND = "notice";
export const NOTICE_TITLE_MAX_LENGTH = 100;
export const NOTICE_TEXT_MAX_LENGTH = 2000;

// 관리 화면에 표시할 공지. PostResponse 중 content_data가 { kind: "notice", text } 형태인 게시글에 대응한다.
export interface ManagedNotice {
    id: number;
    title: string;
    text: string;
    authorId: number;
    createdAt: Date | null;
    updatedAt: Date | null;
}

const toValidDate = (value?: Date | string | null) => {
    if (value == null) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
};

// 게시글 목록에서 공지 형식인 것만 골라 변환한다.
export const toManagedNotices = (posts: PostResponse[]) =>
    posts.flatMap((post): ManagedNotice[] => {
        const text = post.content_data?.text;
        if (post.id == null || post.content_data?.kind !== NOTICE_CONTENT_KIND || typeof text !== "string") return [];
        return [{
            id: post.id,
            title: post.title,
            text,
            authorId: post.author_id,
            createdAt: toValidDate(post.created_at),
            updatedAt: toValidDate(post.updated_at),
        }];
    });

export const noticeDateLabel = (date: Date | null) =>
    date ? date.toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" }) : "-";
