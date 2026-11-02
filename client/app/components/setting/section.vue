<script setup lang="ts">
defineProps<{
    name?: string
}>()
</script>

<template>
    <div class="light:bg-default dark:bg-muted rounded-2xl px-0.5 py-2">
        <p class="text-p2 pt-3 pb-1.5 px-5.5 font-bold light:text-black/50 dark:text-white/50" v-if="name">{{ name }}</p>
        <slot />
    </div>
</template>