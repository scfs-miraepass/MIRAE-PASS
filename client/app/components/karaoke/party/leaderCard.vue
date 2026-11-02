<script setup lang="ts">
import type { User } from "@/client";

defineProps<{
    leader: User;
}>();
</script>

<template>
    <div class="rounded-2xl light:bg-default dark:bg-muted p-6">
        <p class="text-ui-p2 light:text-black/50 dark:text-white/50 mb-1">파티장</p>
        <div class="flex items-center justify-between">
            <p class="text-p1">
                {{ leader.name }}{{ leader.number ? ` (${leader.grade}학년 ${leader.number}반)` : "" }}
            </p>
            <UBadge color="primary" variant="subtle" class="rounded-full">리더</UBadge>
        </div>
    </div>
</template>
