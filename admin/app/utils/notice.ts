import type { PollOperation, PollResponse, PostResponse } from "@miraepass/api-client";

// 공지 게시글의 content_data.kind 값
export const NOTICE_CONTENT_KIND = "notice";
export const NOTICE_TITLE_MAX_LENGTH = 100;
export const NOTICE_TEXT_MAX_LENGTH = 2000;

// 설문 입력 제한. 서버의 PollOperation 검증 조건과 같다.
export const POLL_QUESTION_MAX_LENGTH = 200;
export const POLL_OPTION_MAX_LENGTH = 100;
export const POLL_OPTION_MIN = 2;
export const POLL_OPTION_MAX = 10;

// 관리 화면에 표시할 공지. PostResponse 중 content_data가 { kind: "notice", text } 형태인 게시글에 대응한다.
export interface ManagedNotice {
    id: number;
    title: string;
    text: string;
    authorId: number;
    createdAt: Date | null;
    updatedAt: Date | null;
    hasPoll: boolean;
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
            hasPoll: post.has_poll ?? false,
        }];
    });

export const noticeDateLabel = (date: Date | null) =>
    date ? date.toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" }) : "-";

// 설문 입력 폼의 값. closesAt은 <input type="datetime-local"> 값("YYYY-MM-DDTHH:mm", 브라우저 시간대)이다.
export interface PollForm {
    question: string;
    options: string[];
    allowMultiple: boolean;
    closesAt: string;
}

export const emptyPollForm = (): PollForm => ({ question: "", options: ["", ""], allowMultiple: false, closesAt: "" });

const pad = (value: number) => String(value).padStart(2, "0");

// Date를 datetime-local 입력 값으로 바꾼다.
export const toDateTimeLocal = (date: Date) =>
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;

// 서버의 설문을 입력 폼 값으로 바꾼다. 응답의 closes_at은 실제로는 ISO 문자열로 오므로 Date로 다시 만든다.
export const toPollForm = (poll: PollResponse): PollForm => {
    const closesAt = toValidDate(poll.closes_at);
    return {
        question: poll.question,
        options: poll.options.map((option) => option.text),
        allowMultiple: poll.allow_multiple,
        closesAt: closesAt ? toDateTimeLocal(closesAt) : "",
    };
};

// 입력 폼을 서버 요청 본문으로 바꾼다.
// 서버는 closes_at을 ISO 문자열로 검증하므로, 생성된 타입이 명시하는 Date가 아닌 문자열로 보낸다.
export const toPollOperation = (form: PollForm) =>
    ({
        question: form.question.trim(),
        options: form.options.map((option) => option.trim()),
        allow_multiple: form.allowMultiple,
        closes_at: form.closesAt ? new Date(form.closesAt).toISOString() : null,
    }) as unknown as PollOperation;

// 입력 폼의 문제를 돌려준다. 문제가 없으면 null.
export const pollFormError = (form: PollForm) => {
    if (!form.question.trim()) return "설문 질문을 입력해주세요.";
    const options = form.options.map((option) => option.trim());
    if (options.length < POLL_OPTION_MIN) return `선택지는 ${POLL_OPTION_MIN}개 이상이어야 합니다.`;
    if (options.some((option) => !option)) return "비어 있는 선택지가 있습니다.";
    if (new Set(options).size !== options.length) return "중복된 선택지가 있습니다.";
    return null;
};

export const pollClosesAtLabel = (value?: Date | string | null) => {
    const date = toValidDate(value);
    return date ? date.toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" }) : "마감 없음";
};

// API 응답 에러 객체에서 서버가 보낸 메시지를 꺼낸다. 요청 검증 실패(HttpValidationError)는 message 필드가 없으므로 fallback 문구를 사용한다.
export const noticeErrorMessage = (err: unknown, fallback: string) =>
    err && typeof err === "object" && "message" in err ? String((err as { message: unknown }).message) : fallback;
