<script setup lang="ts">
import { Motion } from "motion-v";

const keypad = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];

const emit = defineEmits<{
    (e: 'input', value: string, args: { vibration: typeof triggerVibration }): void
    (e: 'delete'): void
}>();

const triggerVibration = (pattern?: number) => {
    // 모바일에서 진동 함수
    // TODO: iOS 사파리에선 API 지원 안하는데 어떻게 하실
    if (typeof window !== "undefined" && window.navigator.vibrate) {
        window.navigator.vibrate(pattern ?? 10);
    }
};

const onInput = (value: string) => {
    triggerVibration();
    emit('input', value, { vibration: triggerVibration });
};
const onDelete = () => emit('delete');

// const onInput = (val: string) => {
//     triggerVibration();
//     const currentStr = String(amount.value);
//     if (currentStr.length >= 6) return; // 최대 6자리 제한
//
//     // 초기값이 0이면 새 숫자로 교체, 아니면 뒤에 추가
//     const _new = Number(amount.value === 0 ? val : currentStr + val);
//     const limit = isDeduct.value
//         ? userData.value.point!
//         : Math.min(pointLimit.value!.target_limit, pointLimit.value!.limit)!;
//     if (_new > limit) {
//         triggerVibration(20);
//         setTimeout(() => triggerVibration(100), 100);
//
//         pointError.value = true;
//         pointAnimate(
//             pointScope.value,
//             { translate: "20px" },
//             { type: "spring", stiffness: 700, damping: 3, mass: 0.5 },
//         );
//         setTimeout(
//             () =>
//                 pointAnimate(
//                     pointScope.value,
//                     { translate: "0" },
//                     { type: "spring", stiffness: 700, damping: 3, mass: 0.5 },
//                 ),
//             25,
//         );
//         return;
//     }
//     pointError.value = false;
//     amount.value = _new;
// };
//
// const onDelete = () => {
//     triggerVibration();
//     const currentStr = String(amount.value);
//     if (currentStr.length <= 1) {
//         amount.value = 0;
//     } else {
//         amount.value = Number(currentStr.slice(0, -1));
//     }
//     pointError.value = false;
// };
</script>

<template>
    <Motion
        as="div"
        class="w-full h-[30vh] grid grid-cols-3 grid-rows-4"
        :initial="{ marginBottom: 0 }"
        :animate="{ marginBottom: isConfirm ? '-30vh' : 0 }"
        :transition="{
                    type: 'spring',
                    stiffness: 950,
                    damping: 80,
                    mass: 1,
                }"
    >
        <button
            v-for="num in keypad"
            :key="num"
            @click="onInput(num)"
            class="rounded-xl gap-2 px-5.5 py-3 transition-all active:scale-95 active:opacity-50 active:bg-accented text-h6 text-center"
        >
            {{ num }}
        </button>
        <div />
        <button
            @click="onInput('0')"
            class="rounded-xl gap-2 px-5.5 py-3 transition-all active:scale-95 active:opacity-50 active:bg-accented text-h6 text-center"
        >
            0
        </button>
        <button
            @click="onDelete"
            class="rounded-xl gap-2 px-5.5 py-3 transition-all active:scale-95 active:opacity-50 active:bg-accented text-h5 text-center"
        >
            <UIcon name="i-ph-arrow-left" />
        </button>
    </Motion>
</template>