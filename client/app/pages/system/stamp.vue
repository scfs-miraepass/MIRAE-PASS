<script setup lang="ts">
import type { StampsList } from "@/client";

definePageMeta({
    permissions: [ UserPermission.VIEW_STAMP ]
});

const payload = ref<StampsList[]>([])

await useAsyncData(
    'stamp',
    async (_nuxtApp, { signal }) => {
        const req = await $API.getUserStampsStampGet()
        if (!req.data?.success || req.response == undefined) return;
        payload.value = req.data.data

        return req
    }
)
</script>

<template>
    <div class="flex items-center">
        <NuxtLink to="/" v-slot="{ navigate }" custom>
            <UButton @click="navigate()" color="neutral" variant="ghost" icon="i-ph-caret-left-bold" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="xl" />
        </NuxtLink>
        <p class="text-2xl font-bold text-gray-900 dark:text-white ml-1">탄소중립 동아리 페스티벌</p>
    </div>
    <div>
        <div class="text-center my-10">
            <p class="text-xl">부스에 참여해 스탬프를 받아보세요!</p>
            <p class="text-base light:text-black/50 dark:text-white/50">스탬프를 통해 포인트를 받을 수 있어요.</p>
        </div>
        <hr class="border-default mt-1" />
        <div class="text-center my-5 light:text-black/50 dark:text-white/50">
            {{ payload.length }}개 중<span class="ml-1.5 text-xl font-semibold light:text-black dark:text-white">{{ payload.filter(i => i.have).length }}개 완료</span>
        </div>
        <hr class="border-default" />
        <div class="px-10 py-8 space-y-8">
            <StampObject v-for="i in payload" v-bind="i" />
        </div>
    </div>
</template>