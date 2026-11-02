<script setup lang="ts">
import type { StampType } from "@miraepass/api-client";

definePageMeta({
    permissions: [ UserPermission.GIVE_STAMP ],
});

// 응애 하드코딩
const items = ref<StampType[]>([
    '보석 십자수',
    '페이스 페인팅',
    '수학, 스트링아트',
    '일러스트',
    '주짓수',
    '플리마켓',
    '환경 퀴즈',
    '분리수거 챌린지',
    '인권 키링',
    '인권 나무',
    '문제 다트',
    '암호표 해독',
    '학교 폭력 예방'
]);
const value = ref();
const stampType = useStampType();
const toast = useToast();

const save = () => {
    stampType.value = value.value;
    toast.add({
        title: "설정 저장완료",
        description:
            "스탬프 부스 설정이 저장되었습니다. 설정 변경을 원하는 경우 앱을 완전히 종료 후 재실행 바랍니다.",
        color: "success",
    });

    navigateTo("/system/userSelect?a=service-stamp", { replace: true });
};
</script>

<template>
    <div class="flex items-center">
        <NuxtLink to="/" v-slot="{ navigate }" custom>
            <UButton
                @click="navigate()"
                color="neutral"
                variant="ghost"
                icon="i-ph-caret-left-bold"
                class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented"
                size="xl"
            />
        </NuxtLink>
        <p class="text-2xl font-bold text-gray-900 dark:text-white ml-1">
            스탬프 지급
        </p>
    </div>
    <div class="flex-1 flex flex-col justify-center items-center">
        <div class="flex-1 w-full flex flex-col justify-center items-center">
            <p class="text-base mb-2">당신이 속한 부스를 설정해주세요.</p>
            <USelectMenu
                v-model="value"
                :items="items"
                class="w-full"
                size="xl"
            />
        </div>
        <UButton
            class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
            :disabled="!value"
            @click="save"
        >
            <p class="text-p0">저장하기</p>
        </UButton>
    </div>
</template>
