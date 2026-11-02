<script setup lang="ts">
defineProps<{
    icon?: string
    icon_back?: string
    label: string
    value?: string
}>()
</script>

<template>
    <button class="w-full rounded-xl flex items-center justify-between gap-2 px-5.5 py-3 transition-all active:scale-95 active:opacity-50 active:bg-accented disabled:opacity-30! disabled:scale-100! disabled:bg-transparent!">
        <div class="flex items-center text-p1">
            <slot name="label">
                <UIcon :name="icon" v-if="icon" class="mr-2" />
                {{ label }}
            </slot>
        </div>
        <div class="flex items-center light:text-black/50 dark:text-white/50 text-ui-p2">
            <slot name="value">
                {{ value }}
                <UIcon :name="icon_back" v-if="icon_back" class="ml-1" />
            </slot>
        </div>
    </button>
</template>