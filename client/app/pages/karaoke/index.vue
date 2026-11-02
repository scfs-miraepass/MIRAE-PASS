<script setup lang="ts">
import type { KaraokeResponse } from "@/client";
import KaraokeHeader from "~/components/karaoke/header.vue";
import KaraokeList from "~/components/karaoke/list/list.vue";

definePageMeta({
    permissions: [UserPermission.VIEW_KARAOKE] as PermissionCondition,
});

const session = useSession();
const inviteCount = ref<number>(0);

// 전체 경매 목록을 페이지 단위로 불러온다. (date 쿼리를 생략하면 날짜에 상관없이 전체 목록)
// ranking/list.vue와 같은 무한 스크롤 패턴: X-MAX-PAGE 헤더로 마지막 페이지를 판단한다.
const PAGE_SIZE = 20;
const maxOffset = ref<number>(0);
const dataOffset = ref<number>(1);
const karaokeList = ref<KaraokeResponse[]>([]);

const queryParams = computed(() => ({
    limit: PAGE_SIZE,
    offset: (dataOffset.value - 1) * PAGE_SIZE,
}));

const fetchPage = async (offset: number, signal?: AbortSignal) => {
    const req = await $API.getKaraokeList({ query: { limit: PAGE_SIZE, offset }, signal });
    if (req.error || !req.data || !req.response) return null;
    return { items: req.data.data, maxPage: Number(req.response.headers.get("X-MAX-PAGE")) || 1 };
};

const { pending } = await useAsyncData(
    "karaoke.list",
    async (_nuxtApp, { signal }) => {
        const page = await fetchPage(queryParams.value.offset, signal);
        if (!page) return null;
        maxOffset.value = page.maxPage;
        if (dataOffset.value === 1) karaokeList.value = page.items;
        else karaokeList.value.push(...page.items);
        return page;
    },
    { watch: [queryParams] },
);

// 지금까지 불러온 페이지를 모두 다시 받아 목록을 최신 상태로 교체한다.
const reloadLoadedPages = async () => {
    const pages = await Promise.all(
        Array.from({ length: dataOffset.value }, (_, i) => fetchPage(i * PAGE_SIZE)),
    );
    if (pages.some((p) => p === null)) return;
    maxOffset.value = pages[pages.length - 1]!.maxPage;
    karaokeList.value = pages.flatMap((p) => p!.items);
};

const { scrollYProgress } = useScroll();
useMotionValueEvent(scrollYProgress, "change", (current) => {
    if (current < 0.85) return;
    if (pending.value || dataOffset.value >= maxOffset.value) return;
    dataOffset.value++;
});

// 예정(Pending) 경매의 시작 시간, 진행중(In_Progress) 경매의 종료 시간이 지나면
// 서버 상태가 갱신될 때까지 잠시 후 목록을 다시 불러와 화면을 최신 상태로 맞춘다.
const now = ref<number>(Date.now());
const hasStaleStatus = computed(() =>
    karaokeList.value.some((item) => {
        if (item.status === "Pending") return new Date(item.start_time).getTime() <= now.value;
        if (item.status === "In_Progress") return new Date(item.end_time).getTime() <= now.value;
        return false;
    }),
);

if (import.meta.client) {
    const nowTicker = setInterval(() => (now.value = Date.now()), 1000);
    let staleRetryInterval: ReturnType<typeof setInterval> | undefined;

    watch(
        hasStaleStatus,
        (stale) => {
            if (!stale) {
                if (staleRetryInterval) {
                    clearInterval(staleRetryInterval);
                    staleRetryInterval = undefined;
                }
                return;
            }
            if (staleRetryInterval) return;
            staleRetryInterval = setInterval(reloadLoadedPages, 3000);
        },
        { immediate: true },
    );

    onUnmounted(() => {
        clearInterval(nowTicker);
        if (staleRetryInterval) clearInterval(staleRetryInterval);
    });
}

if (import.meta.client && hasPermission(session.value?.permissions, UserPermission.JOIN_KARAOKE)) {
    const req = await $API.getMyKaraokePartyInvites();
    if (!req.error && req.data) inviteCount.value = req.data.data.filter((i) => i.pending).length;
}

const onCardClick = (item: KaraokeResponse) => {
    navigateTo(`/karaoke/${item.id}`);
};
</script>

<template>
    <!-- 상단 헤더: 뒤로가기 + 제목 + 초대함 버튼 -->
    <KaraokeHeader to="/" title="노래방 예약">
        <NuxtLink
            to="/karaoke/invites"
            v-slot="{ navigate }"
            custom
            v-if="hasPermission(session?.permissions, UserPermission.JOIN_KARAOKE)"
        >
            <UButton
                @click="navigate()"
                color="neutral"
                variant="ghost"
                icon="i-ph-bell-fill"
                class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented relative"
                size="xl"
            >
                <span
                    v-if="inviteCount > 0"
                    class="absolute top-1 right-1 min-w-4 h-4 px-1 rounded-full bg-error text-white text-[10px] flex items-center justify-center"
                >
                    {{ inviteCount }}
                </span>
            </UButton>
        </NuxtLink>
    </KaraokeHeader>

    <!-- 경매 목록: 로딩/빈 상태 및 날짜별로 묶인 전체 카드 목록 -->
    <KaraokeList
        :items="karaokeList"
        :pending="pending && dataOffset === 1"
        :has-more="dataOffset < maxOffset"
        @select="onCardClick"
    />
</template>
