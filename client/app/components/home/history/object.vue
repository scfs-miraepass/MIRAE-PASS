<script setup lang="ts">
import type { PointHistory } from "@/client";

const props = defineProps<PointHistory>();

const isInfoOpen = ref<boolean>(false);
const infoModalCreate = ref<boolean>(false);

watch(isInfoOpen, (value) => {
    if (value) {
        infoModalCreate.value = true;
    } else {
        setTimeout(() => infoModalCreate.value = false, 200);
    }
})

const amountSign = computed(() => (props.changed_amount > 0 ? "+" : ""));

const formattedTime = computed(() => {
    const date = new Date(props.created_at!);
    return date.toLocaleTimeString("ko-KR", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
    });
});

const modalFormattedTime = computed(() => {
    const date = new Date(props.created_at!);
    return date.toLocaleTimeString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
    });
});

const icon = computed(() => {
    if (!props.type) {
        return {
            icon: "🧊",
            color: "#586475",
        };
    }
    return {
        teacher: {
            icon: "🎓",
            color: "#a2bcff",
        },
        cafe: {
            icon: "🧋",
            color: "#7bd58f",
        },
        food: {
            icon: "🥐",
            color: "#a191ff",
        },
        etc: {
            icon: "🧊",
            color: "#586475",
        },
        grant: {
            icon: "🧑‍🎓",
            color: "#586475",
        },
        quest: {
            icon: "", // TODO
            color: "",
        },
        stamp: {
            icon: "🌲",
            color: "#C7678C",
        },
        stamp_bonus: {
            icon: "🎄",
            color: "#a191ff",
        },
        karaoke_bid: {
            icon: "🎤",
            color: "#f2a154",
        },
        karaoke_cancel: {
            icon: "🎤",
            color: "#586475",
        },
    }[props.type];
});
</script>

<template>
    <UModal v-model:open="isInfoOpen" v-if="infoModalCreate">
        <template #content>


            <div class="p-5">
                <div class="flex items-center justify-between gap-1.5">
                    <div class="flex items-center">
                        <div
                            class="rounded-full bg-(--color) p-0.5"
                            :style="`--color: ${icon.color}`"
                        >
                            <p
                                class="tossface aspect-square w-10 h-10 text-[26px] text-center -mb-px"
                            >
                                {{ icon.icon }}
                            </p>
                        </div>
                        <div class="ml-3">
                            <p class="text-p1 mb-1">{{ reason }}</p>
                            <p class="text-ui-p2 light:text-black/50 dark:text-white/50">
                                {{ modalFormattedTime }}
                            </p>
                        </div>
                    </div>
                    <p class="text-p1" :class="{ 'text-primary': amountSign == '+' }">
                        {{ amountSign }}{{ props.changed_amount.toLocaleString() }}P
                    </p>
                </div>

                <hr class="border-default my-5" />
                <div class="text-p1">
                    <p class="text-ui-p2 light:text-black/50 dark:text-white/50 mb-1.5">
                        메모
                    </p>
                    {{ memo || '메모가 없습니다.' }}
                </div>

            </div>
        </template>
    </UModal>

    <div class="flex items-center justify-between rounded-xl px-5 py-2 transition-all active:scale-95 active:opacity-50 active:bg-accented" @click="isInfoOpen = true">
        <div class="flex items-center">
            <div
                class="rounded-full bg-(--color) p-0.5"
                :style="`--color: ${icon.color}`"
            >
                <p
                    class="tossface aspect-square w-10 h-10 text-[26px] text-center -mb-px"
                >
                    {{ icon.icon }}
                </p>
            </div>
            <div class="ml-3">
                <p class="text-p1 mb-0.5">{{ reason }}</p>
                <p class="text-ui-p2 light:text-black/50 dark:text-white/50">
                    {{ formattedTime }}
                </p>
            </div>
        </div>
        <p class="text-p1" :class="{ 'text-primary': amountSign == '+' }">
            {{ amountSign }}{{ props.changed_amount.toLocaleString() }}P
        </p>
    </div>
</template>
