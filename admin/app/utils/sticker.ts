// API 응답 에러 객체에서 서버가 보낸 메시지를 꺼낸다. 요청 검증 실패(HttpValidationError)는 message 필드가 없으므로 fallback 문구를 사용한다.
export const stickerErrorMessage = (
    err: unknown,
    fallback = "문제가 발생했습니다. 지속적으로 발생하는 경우 관리자에게 문의 바랍니다.",
) => (err && typeof err === "object" && "message" in err ? String((err as { message: unknown }).message) : fallback);
