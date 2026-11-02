<script setup lang="ts">
import type { User } from "@/client";
import Icon from "~/components/stamp/icon.vue";

definePageMeta({
    middleware: [
        (to, from) => {
            const userData = useState<User | undefined>(
                "system.user-select.uesr",
            );
            if (!userData.value) {
                return navigateTo("/", { replace: true });
            }
        },
    ],
    permissions: [ UserPermission.GIVE_STAMP ],
});

const stampType = useStampType();
const userData = useState<User>("system.user-select.uesr");
const isLoading = ref<boolean>(false);
const toast = useToast();

const giveStamp = async () => {
    isLoading.value = true;

    const req = await $API.createStampStampPost({
        body: {
            user_id: userData.value.id!,
            stamp_type: stampType.value!,
        },
    });
    if (req.error) {
        if (req.response!.status == 409) {
            toast.add({
                title: "지급 실패",
                description: "이미 스탬프를 획득한 사용자 입니다.",
                color: "error",
            });
        } else {
            toast.add({
                title: "지급 실패",
                description:
                    "알 수 없는 이유로 지급에 실패했습니다. 관리자에게 문의하세요.",
                color: "error",
            });
        }
    } else {
        toast.add({
            title: "지급 완료",
            description: `${userData.value!.name}님에게 스탬프를 지급했습니다.`,
            color: "success",
        });
    }
    navigateTo("/system/userSelect?a=service-stamp", { replace: true });
};
</script>

<template>
    <div class="flex-1 overflow-hidden flex flex-col relative">
        <div class="flex-1 flex flex-col">
            <div class="flex-1 flex flex-col">
                <div class="mt-24">
                    <p
                        class="text-p0 light:text-black/70 dark:text-white/70 font-normal"
                    >
                        <span
                            class="font-bold light:text-black dark:text-white"
                            >{{ userData.name }}</span
                        >
                        {{ userData.type == "student" ? "학생" : "선생님" }}에게
                    </p>
                    <p
                        class="text-p0 text-black/70 dark:text-white/70 font-normal"
                    >
                        스탬프를 지급할까요?
                    </p>
                </div>
                <div class="flex flex-col items-center mt-25">
                    <Icon enable class="w-25 h-25" />
                    <p class="text-p0 mt-2">{{ stampType }}</p>
                </div>
            </div>
            <p
                class="text-ui-p2 mb-5 flex items-center justify-center light:text-black/50 dark:text-white/50"
            >
                <UIcon name="i-ph-warning" class="mr-1" />
                스탬프가 지급되면 추후 회수하거나 재지급 할 수 없어요.
            </p>
            <div class="space-y-3 mb-3">
                <UButton
                    class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
                    @click="giveStamp"
                    :disabled="isLoading"
                    :loading="isLoading"
                >
                    <p class="text-p0">
                        {{ !isLoading ? "지급하기" : "처리중.." }}
                    </p>
                </UButton>
                <UButton
                    color="error"
                    variant="soft"
                    class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
                    :disabled="isLoading"
                    @click="$router.back()"
                >
                    <p class="text-p0">취소</p>
                </UButton>
            </div>
        </div>
    </div>
</template>
