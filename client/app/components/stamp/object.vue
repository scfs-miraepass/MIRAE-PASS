<script setup lang="ts">
import Icon from "./icon.vue";
import type { StampsList } from "@/client";

const { time } = defineProps<StampsList>();

const formattedTime = computed(() => {
    if (time == null) return "";
    const date = new Date(time);
    const hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= 12 ? "오후" : "오전";
    const displayHours = hours % 12 || 12;
    return `${ampm} ${displayHours}시 ${minutes}분`;
});
</script>

<template>
    <div class="flex items-center">
        <Icon :enable="have" />
        <div class="ml-2.5">
            <p class="text-p0 mb-0.5">{{ name }}</p>

            <p class="text-ui-p2 text-primary-500" v-if="have">
                {{ formattedTime }} 완료
            </p>
            <p class="text-ui-p2 light:text-black/50 dark:text-white/50" v-else>
                미완료
            </p>
        </div>
    </div>
</template>
