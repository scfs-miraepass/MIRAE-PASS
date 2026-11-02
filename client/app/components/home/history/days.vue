<script setup lang="ts">
defineProps<{
    date: string
}>()
</script>

<template>
    <!-- 하루 그룹 -->
    <div>
        <p class="text-ui-p2 light:text-black/50 dark:text-white/50 mb-2 px-5">{{ date }}</p> <!-- 일자 -->
        <div class="flex flex-col">
            <!-- 기록 -->
            <slot />
        </div>
    </div>
</template>