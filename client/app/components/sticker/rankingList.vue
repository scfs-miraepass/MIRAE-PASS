<script setup lang="ts">
import Obj from "@/components/sticker/rankingObject.vue";
import type { StickerRankingResponse } from "@miraepass/api-client";

const props = defineProps<{
    q: string;
}>();

const PAGE_SIZE = 15;

const maxOffset = ref<number>(0);
const dataOffset = ref<number>(1);
const payloadData = ref<StickerRankingResponse[]>([]);

watch(
    () => props.q,
    () => {
        dataOffset.value = 1;
        maxOffset.value = 0;
        payloadData.value = [];
    },
    { flush: "sync" },
);

const queryParams = computed(() => ({
    limit: PAGE_SIZE,
    offset: (dataOffset.value - 1) * PAGE_SIZE,
}));

const dataFetchKey = computed(() => `sticker.ranking.${props.q}`);
const { pending } = await useAsyncData(
    dataFetchKey,
    async (_nuxtApp, { signal }) => {
        const req = await $API.getStickerRanking({
            query: {
                ...queryParams.value,
                q: props.q || undefined,
            },
            signal,
        });

        if (req.error || !req.response) return;
        maxOffset.value = Number(req.response.headers.get("X-MAX-PAGE"));

        if (dataOffset.value === 1) {
            payloadData.value = req.data.data;
        } else {
            payloadData.value.push(...req.data.data);
        }
        return req.data;
    },
    { watch: [queryParams, dataFetchKey] },
);

const { scrollYProgress } = useScroll();

useMotionValueEvent(scrollYProgress, "change", (current) => {
    if (current >= (dataOffset.value <= 3 ? 0.5 : 0.85)) {
        if (pending.value || dataOffset.value >= maxOffset.value) {
            return;
        }
        dataOffset.value++;
    }
});
</script>

<template>
    <Obj
        v-for="(i, index) in payloadData"
        v-bind="i"
        :key="i.id"
        :style="{
            animationDelay: dataOffset == 1 ? `${index * 100}ms` : undefined,
        }"
        :class="{ 'animate-fade-up-blur opacity-0': dataOffset == 1 }"
    />
    <p
        class="text-ui-p2 light:text-black/50 dark:text-white/50 text-center"
        v-if="!pending && payloadData.length === 0"
    >
        {{ q ? "검색 결과가 없어요" : "아직 학생이 없어요" }}
    </p>
    <p
        class="text-ui-p2 light:text-black/50 dark:text-white/50 text-center"
        v-else-if="dataOffset >= maxOffset && payloadData.length > 0"
    >
        더이상 없어요
    </p>
</template>
