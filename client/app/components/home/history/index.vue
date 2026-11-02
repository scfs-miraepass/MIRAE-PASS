<script setup lang="ts">
import Group from "./days.vue";
import Obj from "./object.vue";
import { Motion } from "motion-v";
import type { PointHistory } from "@/client";

const maxOffset = ref<number>(0);
const dataOffset = ref<number>(1);
const historyPayload = ref<PointHistory[]>([]);
const showLoading = ref<boolean>(false);
let loadingTimeout: any;

const historyData = computed(() => {
    return historyPayload.value.reduce(
        (acc, item) => {
            const date = new Date(item.created_at!);
            const key = `${date.getMonth() + 1}월 ${date.getDate()}일`;
            if (!acc[key]) acc[key] = [];
            acc[key].push(item);
            return acc;
        },
        {} as Record<string, PointHistory[]>,
    );
});

const queryParams = computed(() => ({
    limit: 20,
    offset: (dataOffset.value - 1) * 20,
}));


const { pending } = await useAsyncData(
    'point.history',

    async (_nuxtApp, { signal }) => {
        const req = await $API.getHistoryListPointHistoryGet({
            query: queryParams.value,
            ...signal
        })

        if (!req.data?.success || req.response == undefined) return;
        maxOffset.value = Number(req.response.headers.get("X-MAX-PAGE"));

        if (dataOffset.value === 1) {
            const cached = req.response.headers.get("X-CACHED") === "true";
            if (!cached) {
                // 포인트 지급또는 차감시, 히스토리 추가되고 캐싱을 삭제함으로 = 캐싱이 안된 데이터가 응답한다면 포인트가 변했다는 소리겠지오..
                console.log(
                    "기록의 캐시가 없습니다. 강제로 세션을 업데이트 합니다.",
                );
                await fetchSession();
            }
            historyPayload.value = req.data.data;
        } else {
            historyPayload.value.push(...req.data.data);
        }
        return req
    },
    { watch: [ queryParams ] }
)

watch(
    pending,
    () => {
        if (pending.value) {
            loadingTimeout = setTimeout(() => {
                showLoading.value = true;
            }, 200);
        } else {
            if (loadingTimeout) clearTimeout(loadingTimeout);
            showLoading.value = false;
        }
    },
    { immediate: true },
);

const { scrollYProgress } = useScroll();

useMotionValueEvent(scrollYProgress, "change", (current) => {
    if (current >= 0.9) {
        if (pending.value || dataOffset.value >= maxOffset.value) {
            return;
        }
        dataOffset.value++;
    }
});
</script>

<template>
    <div
        class="w-full px-1 py-7 light:bg-default dark:bg-muted rounded-2xl flex-1 flex flex-col gap-y-6"
    >
        <div
            class="flex items-center justify-between px-5"
            v-for="i in 6"
            :key="i"
            v-if="showLoading"
        >
            <div class="flex items-center">
                <USkeleton
                    class="rounded-full light:bg-elevated dark:bg-accented/50 p-0.5"
                >
                    <p
                        class="tossface aspect-square w-10 h-10 text-[26px] text-center"
                    />
                </USkeleton>
                <div class="ml-3">
                    <USkeleton
                        class="h-4.5 w-25 mb-1 rounded-full light:bg-elevated dark:bg-accented/50"
                    />
                    <USkeleton
                        class="h-3.5 w-15 rounded-full light:bg-elevated dark:bg-accented/50"
                    />
                </div>
            </div>
            <USkeleton
                class="h-4.5 w-20 mb-1 rounded-full light:bg-elevated dark:bg-accented/50"
            />
        </div>
        <Motion
            as="div"
            v-for="(items, date) in historyData"
            v-else-if="historyPayload.length"
            :initial="{ opacity: 0, translateY: '20px' }"
            :animate="{ opacity: 1, translateY: '0' }"
            :transition="{
                duration: 1,
                delay: 0.5,
                ease: [0, 0.71, 0.2, 1.01],
            }"
        >
            <Group :key="date" :date="date">
                <Obj v-for="item in items" v-bind="item" />
            </Group>
        </Motion>
        <div
            class="flex-1 flex flex-col items-center justify-center text-ui-p1 opacity-50"
            v-else-if="!pending"
        >
            <UIcon name="i-ph-smiley-sad-thin" class="text-h2 mb-1.5" />
            포인트 사용기록이 존재하지 않아요..
        </div>
    </div>
</template>
