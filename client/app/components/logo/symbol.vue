<script setup lang="ts">
withDefaults(defineProps<{
    size?: number | string,
}>(), {
    size: 50,
})
</script>
<template>
    <svg id="Layer_2" :width="size" :height="size" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 337.71 257">
        <g id="Layer_3" data-name="Layer 3">
            <polygon class="cls-5" points="0 0 .71 257 82.45 257 81.71 81 0 0"/>
        </g>
        <g id="Layer_4" data-name="Layer 4">
            <polyline class="cls-4" points="0 0 176.71 0 255.71 81 81.71 81"/>
        </g>
        <g id="Layer_5" data-name="Layer 5">
            <rect class="cls-3" x="255.71" y="0" width="82" height="81"/>
        </g>
        <g id="Layer_6" data-name="Layer 6">
            <polyline class="cls-6" points="255.69 81 82.45 257 174.71 257"/>
        </g>
        <g id="Layer_7" data-name="Layer 7">
            <polyline class="cls-2" points="255.69 81 256.72 257 173.05 257"/>
        </g>
        <g id="Layer_8" data-name="Layer 8">
            <polyline class="cls-1" points="255.69 81 337.71 162.48 337.71 257 256.72 257"/>
        </g>
    </svg>
</template>

<style scoped>
.cls-1 {
    fill: #0068b7;
}

.cls-2 {
    fill: #00a9ee;
}

.cls-3 {
    fill: #ffb700;
}

.cls-4 {
    fill: #0068bb;
}

.cls-5 {
    fill: #003e9c;
}

.cls-6 {
    fill: #8ed3f5;
}
</style>