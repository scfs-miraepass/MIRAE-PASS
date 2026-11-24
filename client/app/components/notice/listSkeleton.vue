<script setup lang="ts">
withDefaults(defineProps<{
    count?: number;
}>(), { count: 3 });
</script>

<template>
    <div role="status" aria-label="공지를 불러오는 중입니다.">
        <div v-for="i in count" :key="i" class="flex items-center gap-3 px-5 py-3">
            <USkeleton class="size-10 shrink-0 rounded-full light:bg-elevated dark:bg-accented/50" />
            <div class="flex-1">
                <USkeleton class="mb-1.5 h-4.5 w-3/5 rounded-full light:bg-elevated dark:bg-accented/50" />
                <USkeleton class="h-3.5 w-16 rounded-full light:bg-elevated dark:bg-accented/50" />
            </div>
        </div>
    </div>
</template>
