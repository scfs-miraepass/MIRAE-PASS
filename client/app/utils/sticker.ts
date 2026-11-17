// API 응답 에러 객체에서 서버가 보낸 메시지를 꺼낸다. 요청 검증 실패(HttpValidationError)는 message 필드가 없으므로 fallback 문구를 사용한다.
export const stickerErrorMessage = (err: unknown, fallback = "요청을 처리하지 못했어요.") =>
    err && typeof err === "object" && "message" in err ? String((err as { message: unknown }).message) : fallback;

// 반 번호로 학과를 구한다. (1 · 2반 바이오, 3 · 4반 소프트, 5 · 6반 전기과)
export const stickerDepartment = (number: number) =>
    number <= 2
        ? { label: "바이오", class: "text-rose-400" }
        : number <= 4
          ? { label: "소프트", class: "text-blue-400" }
          : { label: "전기과", class: "text-yellow-400" };
