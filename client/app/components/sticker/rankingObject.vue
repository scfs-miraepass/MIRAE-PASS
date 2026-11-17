<script setup lang="ts">
import type { StickerRankingResponse } from "@miraepass/api-client";

defineProps<StickerRankingResponse>();
</script>

<template>
    <div class="flex items-center justify-between">
        <div class="flex items-center">
            <p
                class="aspect-square w-11 mx-2.5 text-center -mb-px font-semibold"
                :class="
                    rank > 3
                        ? 'text-[26px] light:text-black/50 dark:text-white/50'
                        : 'text-[35px] tossface'
                "
            >
                <template v-if="rank == 1">🥇</template>
                <template v-else-if="rank == 2">🥈</template>
                <template v-else-if="rank == 3">🥉</template>
                <template v-else>{{ rank }}</template>
            </p>
            <div class="ml-3">
                <div class="flex items-center mb-0.5">
                    <p class="text-p1">{{ name }}</p>

                    <p
                        v-if="grade != null && grade >= 1"
                        class="text-ui-p2 ml-1"
                        :class="stickerDepartment(number ?? 0).class"
                    >
                        {{ grade }}학년 {{ stickerDepartment(number ?? 0).label }}
                    </p>
                </div>
                <p
                    class="text-ui-p2"
                    :class="count > 0 ? 'light:text-black/50 dark:text-white/50' : 'light:text-black/30 dark:text-white/30'"
                >
                    <span class="tossface">♡</span> {{ count }}개
                </p>
            </div>
        </div>
        <div class="flex items-center gap-1 mr-3">
            <span
                v-for="i in 3"
                :key="i"
                class="tossface text-lg"
                :class="{ 'opacity-25 grayscale': i > count }"
            >
                💗
            </span>
        </div>
    </div>
</template>
