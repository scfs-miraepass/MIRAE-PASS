import { authLog } from "~/middleware/auth.global";

export const fetchSession = async () => {
    const session = useSession();
    const { lastFetched } = useAuth();
    // Nuxt 상태 관리를 사용하여 요청 중복 방지 (서버/클라이언트 안전)
    const fetchPromise = useState<Promise<any> | null>(
        "session.fetch_promise",
        () => null,
    );

    authLog("fetchSession 호출");
    // 중복 호출 방지 (요청 중일 때 기존 Promise 재사용)
    if (!fetchPromise.value) {
        authLog("새로운 API 요청 시작");
        fetchPromise.value = $API.getCurrentUserAuthGet().finally(() => {
            fetchPromise.value = null;
        });
    } else {
        authLog("기존 API 요청 대기");
    }

    const req = await fetchPromise.value;
    if (!req.error) {
        authLog("API 성공 (session 업데이트)");
        session.value = req.data.data;
        lastFetched.value = Date.now();
        useServerVersion().value = req.response.headers.get("X-Server-Version");
    } else {
        session.value = undefined;
        lastFetched.value = Date.now(); // 미인증 상태도 캐싱하기 위해 업데이트
    }
    return req;
};
