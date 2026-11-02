<script setup lang="ts">
import type { KaraokeFinalBidResponse, KaraokePartyDetail, KaraokeResponse } from "@/client";
import { KaraokeStatus } from "@/client";
import { karaokeTimeLabel, calcDutchPay, karaokeErrorMessage, KARAOKE_BID_UNIT } from "@/utils/karaoke";
import KaraokeHeader from "~/components/karaoke/header.vue";
import AuctionResult from "~/components/karaoke/detail/result.vue";
import AuctionStatus from "~/components/karaoke/detail/status.vue";
import PartyPanel from "~/components/karaoke/detail/partyPanel.vue";
import BidForm from "~/components/karaoke/detail/bidForm.vue";
import BidHistory from "~/components/karaoke/detail/bidHistory.vue";

definePageMeta({
    permissions: [UserPermission.VIEW_KARAOKE] as PermissionCondition,
});

const route = useRoute();
const toast = useToast();
const session = useSession();
const karaokeId = computed(() => Number(route.params.id));

const detail = ref<KaraokeResponse | null>(null);
const detailPending = ref<boolean>(true);
const finalBid = ref<KaraokeFinalBidResponse | null>(null);
const party = ref<KaraokePartyDetail | null>(null);
const partyPending = ref<boolean>(true);

const fetchDetail = async () => {
    const req = await $API.getKaraoke({ path: { karaoke_id: karaokeId.value } });
    if (req.error) return false;
    detail.value = req.data.data;
    return true;
};

const fetchFinalBid = async () => {
    const req = await $API.getKaraokeFinalBid({ path: { karaoke_id: karaokeId.value } });
    finalBid.value = req.error ? null : req.data.data;
};

const fetchParty = async () => {
    partyPending.value = true;
    const req = await $API.getMyKaraokeParty({ path: { karaoke_id: karaokeId.value } });
    party.value = req.error ? null : req.data.data;
    partyPending.value = false;
};

detailPending.value = true;
await fetchDetail();
detailPending.value = false;
if (detail.value?.status === KaraokeStatus.CONFIRMED) await fetchFinalBid();
if (hasPermission(session.value?.permissions, UserPermission.JOIN_KARAOKE)) await fetchParty();
else partyPending.value = false;

// 소켓은 마감된 경매에는 연결하지 않는다 (7장: WS는 상태와 무관하게 동작하지만 마감 후엔 final-bid를 사용).
const socketEnabled = computed(() => detail.value?.status !== KaraokeStatus.CONFIRMED);
const { status: socketStatus, highestState, remainingTime, reconnectedAt } = useKaraokeSocket(karaokeId, socketEnabled);

// 서버가 상태 전이를 실시간으로 푸시해주므로, 시작/종료 시각을 로컬에서 추적할 필요가 없다.
watch(socketStatus, async (value) => {
    if (!value || !detail.value) return;
    detail.value.status = value;
    if (value === KaraokeStatus.CONFIRMED) await fetchFinalBid();
});

// 소켓이 끊겼다 재연결되면 그 사이 상태 전이 메시지를 놓쳤을 수 있으므로 REST로 한 번 맞춘다.
watch(reconnectedAt, async () => {
    const ok = await fetchDetail();
    if (ok && detail.value?.status === KaraokeStatus.CONFIRMED) await fetchFinalBid();
});

const highestAmount = computed(() => highestState.value?.highest_bid?.amount ?? detail.value?.highest_bid ?? null);
const bidsHistory = computed(() => highestState.value?.bids_history ?? []);

const roundUpToUnit = (value: number) => Math.ceil(value / KARAOKE_BID_UNIT) * KARAOKE_BID_UNIT;
const minBid = computed(() =>
    roundUpToUnit(highestAmount.value != null ? highestAmount.value + 1 : (detail.value?.min_point ?? 0)),
);

const isLeader = computed(() => !!party.value && party.value.leader_id === session.value?.id);
const isMember = computed(() => !!party.value && !isLeader.value);
const partyHeadcount = computed(() => (isLeader.value ? 1 + (party.value?.members.length ?? 0) : 1));

const bidAmount = ref<number>(0);
const bidding = ref<boolean>(false);
const creatingParty = ref<boolean>(false);

watch(
    minBid,
    (value) => {
        if (bidAmount.value < value) bidAmount.value = value;
    },
    { immediate: true },
);

const isValidBid = computed(() => bidAmount.value >= minBid.value && bidAmount.value % KARAOKE_BID_UNIT === 0 && bidAmount.value != 0);

const dutchPreview = computed(() =>
    isLeader.value && partyHeadcount.value > 1 ? calcDutchPay(bidAmount.value, partyHeadcount.value) : null,
);

const canBid = computed(() => detail.value?.status === KaraokeStatus.IN_PROGRESS && !isMember.value);

const submitBid = async () => {
    if (!isValidBid.value) return;
    bidding.value = true;
    const req = await $API.createKaraokeBid({
        path: { karaoke_id: karaokeId.value },
        body: { amount: bidAmount.value },
    });
    bidding.value = false;

    if (req.error) {
        toast.add({ title: "입찰에 실패했어요.", description: karaokeErrorMessage(req.error), color: "error" });
        await fetchDetail();
        return;
    }

    toast.add({ title: "입찰했어요!", color: "success" });
    await fetchSession();
};

const createParty = async () => {
    creatingParty.value = true;
    const req = await $API.createKaraokeParty({ path: { karaoke_id: karaokeId.value } });
    creatingParty.value = false;

    if (req.error) {
        toast.add({ title: "파티를 만들지 못했어요.", description: karaokeErrorMessage(req.error), color: "error" });
        return;
    }
    await fetchParty();
    navigateTo(`/karaoke/${karaokeId.value}/party`);
};

const dateTimeLabel = computed(() => {
    if (!detail.value) return "";
    const d = new Date(detail.value.date);
    return `${d.toLocaleDateString("ko-KR", { month: "long", day: "numeric" })} ${karaokeTimeLabel(detail.value.time)}`;
});
</script>

<template>
    <!-- 상단 헤더: 뒤로가기 + 날짜/교시 제목 -->
    <KaraokeHeader to="/karaoke" :title="dateTimeLabel" />

    <div class="flex-1 flex flex-col items-center justify-center text-ui-p1 opacity-50" v-if="detailPending">
        <UIcon name="i-ph-spinner-gap" class="text-h2 mb-1.5 animate-spin" />
        불러오는 중..
    </div>

    <div class="flex-1 flex flex-col items-center justify-center text-ui-p1 opacity-50" v-else-if="!detail">
        <UIcon name="i-ph-smiley-sad-thin" class="text-h2 mb-1.5" />
        경매를 찾지 못했어요.
    </div>

    <template v-else>
        <div class="min-h-[calc(100vh-(var(--spacing)*19))] flex flex-col gap-3 pb-6" >
            <!-- 마감된 경매: 최종 낙찰 정보만 표시 -->
            <AuctionResult v-if="detail.status === KaraokeStatus.CONFIRMED" :final-bid="finalBid" />

            <!-- 진행중 / 예정: 실시간 경매 화면 -->
            <template v-else>
                <!-- 상태 패널: 배지 + 남은시간 + 최고입찰가 -->
                <AuctionStatus
                    :status="detail.status"
                    :remaining-time="remainingTime"
                    :min-point="detail.min_point ?? 0"
                    :highest-amount="highestAmount"
                    :highest-bid="highestState?.highest_bid"
                    :class="{ 'flex-1': detail.status === KaraokeStatus.PENDING || (isMember && detail.status === KaraokeStatus.IN_PROGRESS) }"
                />

                <!-- 파티 패널: 파티 만들기 / 내 파티 요약 -->
                <PartyPanel
                    v-if="!partyPending"
                    :karaoke-id="karaokeId"
                    :party="party"
                    :is-leader="isLeader"
                    :party-headcount="partyHeadcount"
                    :dutch-preview="dutchPreview"
                    :creating-party="creatingParty"
                    @create="createParty"
                />
                <!-- 입찰 폼: 금액 조절 + 입찰하기 -->
                <BidForm
                    v-if="canBid"
                    v-model:amount="bidAmount"
                    :min-bid="minBid"
                    :is-valid="isValidBid"
                    :bidding="bidding"
                    :dutch-preview="dutchPreview"
                    @submit="submitBid"
                />
                <p class="text-ui-p2 text-center light:text-black/45 dark:text-white/40 mt-4 mb-5" v-else-if="detail.status === KaraokeStatus.IN_PROGRESS && isMember">
                    파티장만 입찰할 수 있어요.
                </p>
            </template>
        </div>
        <!-- 입찰 기록 -->
        <BidHistory v-if="detail.status === KaraokeStatus.IN_PROGRESS" :bids="bidsHistory" />
    </template>

</template>
