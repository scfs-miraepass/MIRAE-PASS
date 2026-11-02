<script setup lang="ts">
import {Motion} from "motion-v";

defineProps<{
    isLeader: boolean;
    busy: boolean;
}>();
defineEmits<{ disperse: []; leave: [] }>();

const isConfirm = ref<boolean>(false);
</script>

<template>
    <div
        class="text-ui-p2 mb-2 flex flex-col items-center light:text-black/50 dark:text-white/50 transition-opacity"
        :class="[isConfirm ? 'opacity-100' : 'opacity-0']"
    >
        {{ isLeader ? '정말로 파티를 해산하시겠어요?': '정말로 파티를 나가시겠어요?' }}
    </div>
    <div class="flex items-center">
        <UButton
            class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
            @click="
                () => {
                    if (isConfirm) {
                        if (isLeader) {
                            $emit('disperse')
                        } else {
                            $emit('leave')
                        }
                        return
                    }
                    isConfirm = true;
                }
            "
            :loading="busy"
            color="error" variant="soft"
        >
            <p class="text-p0 text-nowrap px-4">{{ isLeader ? '파티 해산': '파티 탈퇴' }}</p>
        </UButton>
        <Motion
            class="flex w-full ml-3"
            :initial="{ marginRight: '-112%', marginLeft: '3rem' }"
            :animate="{
                marginRight: !isConfirm || busy ? '-112%' : 0,
                marginLeft: !isConfirm || busy ? '3rem' : '1rem',
            }"
            :transition="{
                type: 'spring',
                duration: 0.8,
                bounce: 0.15,
            }"
        >
            <UButton
                class="rounded-2xl justify-center flex py-4.5 transition-opacity text-nowrap w-full h-full"
                @click="
                    () => {
                        isConfirm = false;
                    }
                "
            >
                <p class="text-p0">취소</p>
            </UButton>
        </Motion>
    </div>
</template>
