<script setup lang="ts">
import type { User } from "@/client";

defineProps<{
    members: User[];
    pendingMembers: User[];
    isLeader: boolean;
    busy: boolean;
}>();
defineEmits<{ kick: [user: User] }>();
</script>

<template>
    <div class="rounded-2xl light:bg-default dark:bg-muted p-6">
        <p class="text-ui-p2 light:text-black/50 dark:text-white/50 mb-2">
            참여중인 멤버 ({{ members.length }}명)
        </p>
        <div class="flex flex-col gap-2" v-if="members.length > 0">
            <div class="flex items-center justify-between" v-for="m in members" :key="m.id!">
                <p class="text-p1">{{ m.name }}{{ m.number ? ` (${m.grade}학년 ${m.number}반)` : "" }}</p>
                <UButton
                    v-if="isLeader"
                    size="md"
                    color="error"
                    variant="soft"
                    class="rounded-lg"
                    icon="i-ph-user-minus"
                    :disabled="busy"
                    @click="$emit('kick', m)"
                >
                    내보내기
                </UButton>
            </div>
        </div>
        <p class="text-p1" v-else>아직 참여한 멤버가 없어요.</p>

        <template v-if="pendingMembers.length > 0">
            <p class="text-ui-p2 light:text-black/50 dark:text-white/50 mt-6 mb-2">초대 대기중</p>
            <div class="flex flex-col gap-2">
                <div class="flex items-center justify-between" v-for="m in pendingMembers" :key="m.id!">
                    <p class="text-p1">{{ m.name }}{{ m.number ? ` (${m.grade}학년 ${m.number}반)` : "" }}</p>
                    <UBadge color="neutral" variant="subtle" class="rounded-full">대기중</UBadge>
                </div>
            </div>
        </template>
    </div>
</template>
