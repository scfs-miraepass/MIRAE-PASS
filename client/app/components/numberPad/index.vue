<script setup lang="ts">
import { Motion } from "motion-v";
import Key from "./key.vue";

const { hidden = false } = defineProps<{
    hidden?: boolean
}>()

export type InputEmit = { value: string, vibration: typeof triggerVibration }
const emit = defineEmits<{
    'input': [InputEmit]
    'delete': []
}>();

const keypad = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];

const triggerVibration = (pattern?: number) => {
    // 모바일에서 진동 함수
    // TODO: iOS 사파리에선 API 지원 안하는데 어떻게 하실
    if (typeof window !== "undefined" && window.navigator.vibrate) {
        window.navigator.vibrate(pattern ?? 10);
    }
};

const onInput = (value: string) => {
    triggerVibration();
    emit('input', { value, vibration: triggerVibration });
};
const onDelete = () => {
    triggerVibration();
    emit('delete')
};
</script>

<template>
    <Motion
        as="div"
        class="w-full h-[30vh] grid grid-cols-3 grid-rows-4"
        :initial="{ marginBottom: 0 }"
        :animate="{ marginBottom: hidden ? '-30vh' : 0 }"
        :transition="{
            type: 'spring',
            stiffness: 950,
            damping: 80,
            mass: 1,
        }"
    >

        <Key v-for="key in keypad" :label="key" :key="key" @click="onInput(key)" />

        <div />

        <Key label="0" key="0" @click="onInput('0')" />
        <Key class="text-h5" key="delete" @click="onDelete">
            <UIcon name="i-ph-arrow-left" />
        </Key>
    </Motion>
</template>