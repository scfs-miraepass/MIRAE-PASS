// 이 기기의 앱 알림(웹 푸시) 구독을 관리합니다.
// 서버 API: GET /notification/key, PUT·DELETE /notification/subscription

type PushState = "unsupported" | "denied" | "off" | "on";

// VAPID 공개키(base64url)를 PushManager.subscribe가 받는 바이트 배열로 바꿉니다.
const toApplicationServerKey = (base64url: string): Uint8Array<ArrayBuffer> => {
    const base64 = (base64url + "=".repeat((4 - (base64url.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(base64);
    const bytes = new Uint8Array(new ArrayBuffer(raw.length));
    for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
    return bytes;
};

const isSupported = () =>
    import.meta.client && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

const SW_READY_TIMEOUT_MS = 5000;

// 등록된 서비스 워커를 바로 가져옵니다. 없으면 undefined (기다리지 않음)
const getRegistration = async () => (isSupported() ? await navigator.serviceWorker.getRegistration() : undefined);

// 구독하려면 활성화된 서비스 워커가 필요해서 준비될 때까지 기다립니다. 서비스 워커가 없으면 시간 제한 뒤 undefined
const waitForRegistration = async () => {
    if (!isSupported()) return undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const timeout = new Promise<undefined>((resolve) => (timer = setTimeout(() => resolve(undefined), SW_READY_TIMEOUT_MS)));
    try {
        return await Promise.race([navigator.serviceWorker.ready, timeout]);
    } finally {
        clearTimeout(timer);
    }
};

export const usePushNotification = () => {
    const state = useState<PushState>("notification.push_state", () => "off");

    /** 브라우저 권한과 현재 구독 여부로 상태를 갱신합니다. */
    const refresh = async () => {
        if (!isSupported()) return (state.value = "unsupported");
        if (Notification.permission === "denied") return (state.value = "denied");
        const registration = await getRegistration();
        const subscription = await registration?.pushManager.getSubscription();
        state.value = subscription && Notification.permission === "granted" ? "on" : "off";
    };

    /**
     * 알림 권한을 요청하고 이 기기를 구독합니다. 반드시 버튼 클릭 같은 사용자 동작 안에서 호출해야 합니다.
     * @returns 실패하면 사용자에게 보여줄 메시지, 성공하면 undefined
     */
    const enable = async (): Promise<string | undefined> => {
        if (!isSupported()) return "이 기기에서는 알림을 받을 수 없어요. iPhone은 홈 화면에 추가한 앱에서만 받을 수 있어요.";

        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
            await refresh();
            return "알림 권한이 거부되어 있어요. 기기 설정에서 미래패스 알림을 허용해 주세요.";
        }

        const keyReq = await $API.getNotificationKey();
        if (keyReq.error) return karaokeErrorMessage(keyReq.error, "알림 설정을 불러오지 못했어요.");
        const publicKey = keyReq.data.data.public_key;
        if (!publicKey) return "지금은 알림 기능을 쓸 수 없어요.";

        const registration = await waitForRegistration();
        if (!registration) return "알림을 켜지 못했어요. 앱을 다시 열어 주세요.";
        const subscription =
            (await registration.pushManager.getSubscription()) ??
            (await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: toApplicationServerKey(publicKey),
            }));

        const json = subscription.toJSON();
        const req = await $API.subscribeNotification({
            body: { endpoint: subscription.endpoint, keys: { p256dh: json.keys?.p256dh ?? "", auth: json.keys?.auth ?? "" } },
        });
        if (req.error) {
            await subscription.unsubscribe().catch(() => undefined);
            await refresh();
            return karaokeErrorMessage(req.error, "알림을 켜지 못했어요.");
        }
        state.value = "on";
    };

    /**
     * 이 기기의 구독을 해제합니다. 로그아웃 전에도 호출합니다. (공용 기기에서 다음 사용자에게 알림이 가지 않도록)
     * 서버 요청이 실패해도 기기 구독은 해제합니다.
     */
    const disable = async () => {
        const registration = await getRegistration().catch(() => undefined);
        const subscription = await registration?.pushManager.getSubscription();
        if (subscription) {
            await $API.unsubscribeNotification({ body: { endpoint: subscription.endpoint } }).catch(() => undefined);
            await subscription.unsubscribe().catch(() => undefined);
        }
        if (isSupported()) await refresh();
    };

    return { state: readonly(state), refresh, enable, disable };
};
