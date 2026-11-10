<script setup lang="ts">
const { class: props_class } = defineProps<{
    label?: string
    class?: string
}>()

const base_class = 'rounded-xl gap-2 px-5.5 py-3 transition-all active:scale-95 active:opacity-50 active:bg-accented text-h6 text-center'
</script>

<template>
    <button
        :class="`${props_class ?? ''} ${base_class}`"
    >
        <slot>
            {{ label }}
        </slot>
    </button>
</template>