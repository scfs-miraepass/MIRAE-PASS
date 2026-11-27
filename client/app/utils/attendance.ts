// 서버의 ATTENDANCE_BONUS_STREAK(app/core/service/attendance.py)와 같은 값: 이 주기마다 보너스를 받는다.
export const ATTENDANCE_BONUS_STREAK = 11;

export const attendanceErrorMessage = (err: unknown, fallback = "잠시 후 다시 시도해주세요.") =>
    err && typeof err === "object" && "message" in err ? String((err as { message: unknown }).message) : fallback;

/**
 * 이번 보너스 주기에서 채운 칸 수 (보너스를 받은 날은 모두 채운 상태로 보여준다)
 */
export const attendanceFilledCount = (streak: number) => {
    if (streak <= 0) return 0;
    const rest = streak % ATTENDANCE_BONUS_STREAK;
    return rest === 0 ? ATTENDANCE_BONUS_STREAK : rest;
};
