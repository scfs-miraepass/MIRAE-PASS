<script setup lang="ts">
const session = useSession();
const isFirst = ref(true);

await useAsyncData(
    'settings.kioskPassword',
    async (_nuxtApp, { signal }) => {
        if (!session.value) return
        const req = await $API.kioskPasswordVerify({
            body: {
                id: session.value.id!,
                password: ""
            },
            ...signal
        })
        if (req.response == undefined) return;

        // kioskPasswordVerify는 비밀번호가 설정되지 않았을 경우 400을 응답합니다.
        isFirst.value = req.response.status == 400;

        return req
    }
)

const newPassword = ref();

</script>

<template>
    <div class="flex items-center mb-4">
        <NuxtLink to="/setting" v-slot="{ navigate }" custom>
            <UButton @click="navigate()" color="neutral" variant="ghost" icon="i-ph-caret-left-bold" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="xl" />
        </NuxtLink>
        <p class="text-2xl font-bold text-gray-900 dark:text-white ml-1">키오스크 비밀번호 설정</p>
    </div>

    <div class="flex-1 flex flex-col">
        <div class="flex-1 flex flex-col justify-center items-center pb-5">
            <div class="text-black/70 dark:text-white/70 text-center mb-5">
                <p class="text-p0 font-normal">
                    설정하려는 비밀번호 입력
                </p>
                <p class="text-ui-p2 mt-1">카페 등 키오스크에서 결제시 사용되요</p>
            </div>
            <UPinInput
                type="number"
                :length="6"
                size="xl"
                class="pointer-events-none"
            />
        </div>

        <!-- 버튼(다음, 취소, 진행) UI -->
        <div class="flex gap-3 mb-3">
            <UButton
                class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
            >
                <p class="text-p0">다음</p>
            </UButton>
        </div>

        <!-- 키패드 UI -->
        <NumberPad />

    </div>
</template>