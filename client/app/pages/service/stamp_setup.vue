<script setup lang="ts">
import type { StampType } from "@/client";

definePageMeta({
    permissions: [ UserPermission.GIVE_STAMP ],
});

// 응애 하드코딩
const items = ref<StampType[]>([
    "쓰레기 투호",
    "철권 한판",
    "큐피트의 다트",
    "제기찰겨? 날찰겨?",
    "팔씨름 최강자전",
    "부적꾸미기",
    "누르기 챌린지",
    "공놀이 괴물",
    "철면피 노래방",
    "절대음감",
    "런닝맨",
    "의자뺏기",
    "단체줄넘기",
    "수학 키캡",
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
