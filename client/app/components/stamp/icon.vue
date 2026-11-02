<script setup lang="ts">
const { enable = false } = defineProps<{
    enable?: boolean
}>()
</script>

<template>
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 100 100"
        class="w-20 h-20 text-primary-500"
        fill="none"
        v-if="enable"
    >
        <!-- 부드러운 배경색 (Tailwind text-primary-500을 currentColor로 상속받음) -->
        <circle cx="50" cy="50" r="44" fill="currentColor" fill-opacity="0.1" />

        <!-- 단단한 실선 테두리 -->
        <circle cx="50" cy="50" r="44" stroke="currentColor" stroke-width="4" />

        <!-- 내부 지구본 심볼 -->
        <g stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="50" cy="50" r="26" />
            <ellipse cx="50" cy="50" rx="12" ry="26" />
            <path d="M24 50h52" />
        </g>
    </svg>
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 100 100"
        class="w-20 h-20 text-gray-300 dark:text-gray-600"
        fill="none"
        stroke="currentColor"
        stroke-width="3"
        v-else
    >
        <!-- 점선 테두리 -->
        <circle cx="50" cy="50" r="44" stroke-dasharray="8 8" stroke-linecap="round" />

        <!-- 내부 지구본 심볼 (투명도를 낮춰서 연하게 표현) -->
        <g class="opacity-50" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="50" cy="50" r="26" />
            <ellipse cx="50" cy="50" rx="12" ry="26" />
            <path d="M24 50h52" />
        </g>
    </svg>
</template>