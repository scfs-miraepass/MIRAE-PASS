<script setup lang="ts">
defineProps<{
    to: string;
    title: string;
}>();
</script>

<template>
    <div class="flex items-center mb-4">
        <NuxtLink :to="to" v-slot="{ navigate }" custom>
            <UButton
                @click="navigate()"
                color="neutral"
                variant="ghost"
                icon="i-ph-caret-left-bold"
                class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented"
                size="xl"
            />
        </NuxtLink>
        <p class="text-2xl font-bold text-gray-900 dark:text-white ml-1 flex-1">{{ title }}</p>
        <slot />
    </div>
</template>
