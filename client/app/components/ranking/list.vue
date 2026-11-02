<script setup lang="ts">
import Obj from "@/components/ranking/object.vue";
import type { RankingResponse } from "@/client";

const props = defineProps<{
    type: "student" | "teacher";
    period: "total" | "weekly";
}>();

const maxOffset = ref<number>(0);
const dataOffset = ref<number>(1);
const payloadData = ref<RankingResponse[]>([]);

watch(
    () => props.period,
    () => {
        dataOffset.value = 1;
        maxOffset.value = 0;
        payloadData.value = [];
    },
    { flush: "sync" },
);

const queryParams = computed(() => ({
    limit: 15,
    offset: (dataOffset.value - 1) * 15,
}));

const dataFetchKey = computed(() => `point.ranking.${props.period}.${props.type}`)
const { pending } = await useAsyncData(
    dataFetchKey,
    async (_nuxtApp, { signal }) => {
        const req = await $API.getRankingPointRankingGet({
            query: {
                ...queryParams.value,
                type: props.type,
                period: props.period,
            },
            ...signal,
        });

        if (!req.data?.success || req.response == undefined) return;
        maxOffset.value = Number(req.response.headers.get("X-MAX-PAGE"));

        if (dataOffset.value === 1) {
            payloadData.value = req.data.data;
        } else {
            payloadData.value.push(...req.data.data);
        }
        return req
    }, { watch: [ queryParams, dataFetchKey ] }
)

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
        :period="period"
        :keys="i.id"
        :style="{
            animationDelay: dataOffset == 1 ? `${index * 100}ms` : undefined,
        }"
        :class="{ 'animate-fade-up-blur opacity-0': dataOffset == 1 }"
    />
    <p
        class="text-ui-p2 light:text-black/50 dark:text-white/50 text-center"
        v-if="dataOffset >= maxOffset"
    >
        더이상 없어요
    </p>
</template>
