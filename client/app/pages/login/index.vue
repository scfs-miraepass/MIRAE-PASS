<script setup lang="ts">
import { Motion } from "motion-v";
import type { UserType } from "@/client";

definePageMeta({
    layout: false,
});

const [scope, animate] = useAnimate();
const route = useRoute();
const disableOpening = route.query.disableOpening === "true";
const colorMode = useColorMode();

const isDark = computed(() => colorMode.value === "dark");

const typeSelect = (type: UserType) => {
    // 완전히 보였을 때 부터 선택 이벤트가 처리 되도록
    if (
        scope.value &&
        Number(window.getComputedStyle(scope.value).opacity) < 0.8
    )
        return;
    navigateTo(`/login/${type}`, { replace: true });
};
</script>

<template>
    <Motion
        as="div"
        class="w-screen h-screen p-7 flex flex-col justify-center items-center absolute top-0 left-0"
        :initial="{ opacity: 1 }"
        :animate="{ opacity: 0 }"
        :transition="{
            duration: 0.8,
            delay: 2.5,
            ease: [0, 0.71, 0.2, 1.01],
        }"
        v-if="!disableOpening"
    >
        <Motion
            as="p"
            class="text-h6 font-bold"
            :initial="{ opacity: 0, translateY: '20px' }"
            :animate="{ opacity: 1, translateY: '0' }"
            :transition="{
                duration: 1,
                delay: 0.5,
                ease: [0, 0.71, 0.2, 1.01],
            }"
        >
            안녕하세요!
        </Motion>
        <Motion
            as="div"
            class="flex items-center justify-center text-p0 mt-1.5"
            :initial="{ opacity: 0, translateY: '20px' }"
            :animate="{ opacity: 1, translateY: '0' }"
            :transition="{
                duration: 0.8,
                delay: 1.0,
                ease: [0, 0.71, 0.2, 1.01],
            }"
        >
            <LogoSymbol size="20px" />
            <span class="text-primary ml-1">미래패스</span>에 오신걸 환영해요
        </Motion>
    </Motion>

    <Motion
        as="div"
        class="w-screen h-screen p-7 flex flex-col absolute top-0 left-0"
        :initial="{ opacity: 0 }"
        :animate="{ opacity: 1 }"
        :transition="{
            duration: 1,
            delay: disableOpening ? 0 : 2.5,
            ease: [0, 0.71, 0.2, 1.01],
        }"
        ref="scope"
    >
        <div class="flex-1 flex flex-col py-34">
            <p class="text-h6 font-bold">지금,</p>
            <p class="text-h6 font-bold mt-2">미래패스를 시작해보세요</p>
            <div class="flex-1 flex flex-col items-center justify-end gap-4">
                <!-- color 해서 넣었는데 안되서 template으로 하드코딩 ㅎ -->
                <template v-if="isDark">
                    <UButton
                        icon="i-hugeicons-student"
                        color="neutral"
                        variant="soft"
                        class="w-full rounded-full text-p0! py-4.5 font-semibold"
                        block
                        @click="typeSelect('student')"
                    >
                        학생으로 로그인하기
                    </UButton>
                    <UButton
                        icon="i-hugeicons-teaching"
                        color="neutral"
                        variant="soft"
                        size="xl"
                        class="w-full rounded-full text-p0! py-4.5 font-semibold"
                        block
                        @click="typeSelect('teacher')"
                    >
                        선생님으로 로그인하기
                    </UButton>
                </template>
                <template v-else>
                    <UButton
                        icon="i-hugeicons-student"
                        color="primary"
                        variant="soft"
                        class="w-full rounded-full text-p0! py-4.5 font-semibold"
                        block
                        @click="typeSelect('student')"
                    >
                        학생으로 로그인하기
                    </UButton>
                    <UButton
                        icon="i-hugeicons-teaching"
                        color="primary"
                        variant="soft"
                        size="xl"
                        class="w-full rounded-full text-p0! py-4.5 font-semibold"
                        block
                        @click="typeSelect('teacher')"
                    >
                        선생님으로 로그인하기
                    </UButton>
                </template>
                <UButton
                    class="cursor-pointer"
                    variant="link"
                    color="neutral"
                    @click="typeSelect('service')"
                    >서비스로 로그인</UButton
                >
            </div>
        </div>
    </Motion>
</template>

<style scoped>
body {
    @apply overflow-hidden;
}
</style>
