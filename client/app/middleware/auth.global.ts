const LOGIN_CACHE_TTL = 1000 * 60 * 5; // 5분 (로그인 상태에서 세션에 대한 캐시 TTL)
const UNAUTH_CACHE_TTL = 60 * 60 * 24 * 1 * 1000; // 1일 (비 로그인 상태에서 세션에 대한 캐시 TTL)

// 브라우저 콘솔 로그를 예쁘게 출력하기 위한 헬퍼 함수
export const authLog = (message: string, ...args: any[]) => {
    console.log(
        `%cAuth Middleware%c ${message}`,
        "background: oklch(48.8% 0.243 264.376); color: white; padding: 2px 6px; border-radius: 4px; font-weight: 600;",
        "color: inherit;",
        ...args,
    );
};

export default defineNuxtRouteMiddleware(async (to) => {
    if (import.meta.client) {
        authLog(`'${to.path}'으로 페이지 이동`);
        const session = useSession();
        const { lastFetched } = useAuth();
        const now = Date.now();

        // 이미 세션 정보가 있는 경우
        if (session.value) {
            authLog("기존 세션 존재");
            // Stale-While-Revalidate 패턴: 캐시 유효기간 경과 시 백그라운드 갱신
            if (now - lastFetched.value > LOGIN_CACHE_TTL) {
                authLog("캐시 만료, 갱신 시작");
                const req = await fetchSession();
                if (req.error && !to.path.startsWith("/login")) {
                    authLog("갱신 실패, 로그인 페이지으로 이동시킵니다.");
                    return navigateTo("/login", { replace: true });
                }
            } else {
                authLog("캐시와 세션이 유효함.");
            }

            if (to.path.startsWith("/login")) {
                authLog(
                    "이미 세션이 존재합니다. 메인 페이지으로 이동시킵니다.",
                );
                return navigateTo("/");
            }
            authLog(
                `통과. ${(LOGIN_CACHE_TTL - (now - lastFetched.value)) / 1000}초 후 만료됨.`,
            );
            return;
        }

        // 미인증 상태(로그아웃 상태) 캐싱
        const isUnauthCached =
            lastFetched.value > 0 &&
            now - lastFetched.value <= UNAUTH_CACHE_TTL;
        if (isUnauthCached && to.path.startsWith("/login")) {
            authLog(
                `미인증 상태 캐시 유효. ${(UNAUTH_CACHE_TTL - (now - lastFetched.value)) / 1000}초 후 만료됨.`,
            );
            return;
        }

        authLog("세션 없음, API 호출 대기");
        // 세션 정보가 없으면 API 호출 대기 (최초 진입, 캐시 만료, 또는 보호된 라우트 진입 시도 등)
        const req = await fetchSession();

        if (to.path.startsWith("/login")) {
            if (!req.error) {
                authLog(
                    "이미 세션이 존재합니다. 메인 페이지으로 이동시킵니다.",
                );
                return navigateTo("/");
            }
            authLog("로그인 페이지 통과");
            return;
        }

        if (req.error) {
            authLog("세션 없습니다. 로그인 페이지으로 이동시킵니다.");
            return navigateTo("/login", { replace: true });
        }

        authLog("세션 확인 완료");
    }
});
