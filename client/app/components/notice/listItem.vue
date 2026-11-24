<script setup lang="ts">
import type { NoticeItem } from "~/utils/notice";

defineProps<{
    notice: NoticeItem;
}>();
</script>

<template>
    <NuxtLink
        :to="`/notices/${notice.id}`"
        class="flex items-center gap-3 rounded-xl px-5 py-3 transition-all active:scale-95 active:opacity-50 active:bg-accented focus-visible:outline-2 focus-visible:outline-primary"
    >
        <span class="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary" aria-hidden="true">
            <UIcon name="i-ph-megaphone-simple-fill" class="size-5" />
        </span>
        <span class="min-w-0 flex-1">
            <span class="flex min-w-0 items-center gap-1.5">
                <span class="truncate text-p1">{{ notice.title }}</span>
                <span v-if="notice.hasPoll" class="shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-p3 font-bold text-primary">설문</span>
            </span>
            <span v-if="notice.createdAt" class="mt-1 block text-ui-p2 light:text-black/50 dark:text-white/50">
                {{ noticeDateLabel(notice.createdAt) }}
            </span>
        </span>
        <UIcon name="i-ph-caret-right" class="shrink-0 light:text-black/30 dark:text-white/30" aria-hidden="true" />
    </NuxtLink>
</template>
