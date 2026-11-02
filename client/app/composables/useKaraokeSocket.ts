import { type User, KaraokeStatus } from "@/client";

// 백엔드 KaraokeBidHistoryItem과 동일한 형태. WS 전용 응답이라 OpenAPI 스펙에는 포함되지 않는다.
export interface KaraokeSocketBid {
    id: number;
    auction_id: number;
    party_id: number | null;
    amount: number;
    created_at: string;
    bidder: User | null;
}

export interface KaraokeSocketState {
    highest_bid: KaraokeSocketBid | null;
    bids_history: KaraokeSocketBid[];
    remaining_time: number;
}

type KaraokeSubData =
    | { type: "status"; data: KaraokeStatus }
    | { type: "highest"; data: KaraokeSocketState }
    | { type: "sync"; data: number };

// 노래방 경매 실시간 상태 구독. `/karaoke/{id}/ws`는 OpenAPI 스펙에 포함되지 않아 SDK가 생성되지 않으므로 직접 연결한다.
export const useKaraokeSocket = (
    karaokeId: MaybeRefOrGetter<number>,
    enabled: MaybeRefOrGetter<boolean> = true,
) => {
    const status = ref<KaraokeStatus | null>(null);
    const highestState = ref<KaraokeSocketState | null>(null);
    const remainingTime = ref<number>(0);
    const isConnected = ref<boolean>(false);

    // 재연결에 성공할 때마다 갱신되는 타임스탬프. 끊겨 있던 동안 놓쳤을 수 있는 상태 전이를
    // 호출 측이 REST로 다시 맞출 수 있도록 신호를 준다 (최초 연결 시에는 갱신되지 않는다).
    const reconnectedAt = ref<number>(0);

    let ws: WebSocket | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | undefined;
    let reconnectDelay = 1000;
    let stopped = false;
    let hasConnectedOnce = false;

    const cleanupSocket = () => {
        clearTimeout(reconnectTimeout);
        if (ws) {
            ws.onopen = null;
            ws.onmessage = null;
            ws.onclose = null;
            ws.onerror = null;
            ws.close();
            ws = null;
        }
        isConnected.value = false;
    };

    const connect = () => {
        if (!import.meta.client || stopped) return;
        cleanupSocket();

        const id = toValue(karaokeId);
        const protocol = location.protocol === "https:" ? "wss" : "ws";
        const socket = new WebSocket(`${protocol}://${location.host}/api/karaoke/${id}/ws`);
        ws = socket;

        socket.onopen = () => {
            isConnected.value = true;
            reconnectDelay = 1000;
            if (hasConnectedOnce) reconnectedAt.value = Date.now();
            hasConnectedOnce = true;
        };
        socket.onmessage = (event) => {
            const payload = JSON.parse(event.data) as KaraokeSubData;

            switch (payload.type) {
                case "highest":
                    highestState.value = payload.data;
                    remainingTime.value = payload.data.remaining_time;
                    break;
                case "status":
                    status.value = payload.data;
                    break;
                case "sync":
                    remainingTime.value = payload.data;
                    break;
            }
        };
        socket.onclose = () => {
            isConnected.value = false;
            if (stopped || !toValue(enabled)) return;
            reconnectTimeout = setTimeout(() => {
                reconnectDelay = Math.min(reconnectDelay * 2, 15000);
                connect();
            }, reconnectDelay);
        };
        socket.onerror = () => socket.close();
    };

    let countdownInterval: ReturnType<typeof setInterval> | undefined;
    const startCountdown = () => {
        if (countdownInterval) return;
        countdownInterval = setInterval(() => {
            if (remainingTime.value > 0) remainingTime.value -= 1;
        }, 1000);
    };
    const stopCountdown = () => {
        clearInterval(countdownInterval);
        countdownInterval = undefined;
    };

    if (import.meta.client) {
        watchEffect(() => {
            if (toValue(enabled)) {
                connect();
                startCountdown();
            } else {
                cleanupSocket();
                stopCountdown();
            }
        });
    }

    onScopeDispose(() => {
        stopped = true;
        stopCountdown();
        cleanupSocket();
    });

    return { status, highestState, remainingTime, isConnected, reconnectedAt };
};
