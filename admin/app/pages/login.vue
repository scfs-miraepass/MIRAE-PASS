<script setup lang="ts">
import * as z from "zod";
import type { FormSubmitEvent } from "@nuxt/ui";

const schema = z.object({
    userid: z
        .number({ error: "사용자 고유번호 4자리를 입력해주세요." })
        .refine(
            (val) => String(val).length === 4,
            "사용자 고유번호 4자리를 입력해주세요.",
        ),
    password: z.string().min(1, { error: "비밀번호를 입력해주세요." }),
});

type Schema = z.output<typeof schema>;
const state = reactive<Partial<Schema>>({ userid: undefined, password: "" });
const isLoading = ref(false);
const errorMessage = ref<string | undefined>(undefined);

const route = useRoute();

const userIdPayload = ref<number[]>([]);
watch(userIdPayload, () => {
    state.userid = Number(userIdPayload.value?.join(""));
});

watch(state, () => (errorMessage.value = undefined));

async function onSubmit(event: FormSubmitEvent<Schema>) {
    isLoading.value = true;
    errorMessage.value = undefined;

    try {
        const { error } = await $API.loginAuthLoginPost({
            body: {
                id: event.data.userid,
                password: event.data.password,
            },
        });

        if (error) {
            errorMessage.value = "아이디 또는 비밀번호가 일치하지 않습니다.";
            return;
        }

        const redirectPath = (route.query.redirect as string) || "/";
        await navigateTo(redirectPath);
    } finally {
        isLoading.value = false;
    }
}
</script>

<template>
    <div class="flex min-h-dvh items-center justify-center bg-muted/30">
        <UCard class="w-full max-w-sm">
            <template #header>
                <div class="text-center">
                    <h1 class="text-2xl font-semibold text-default">로그인</h1>
                    <p class="mt-1 text-sm text-muted">
                        서비스를 이용하시려면 로그인해주세요.
                    </p>
                </div>
            </template>

            <UForm
                :schema="schema"
                :state="state"
                class="space-y-4"
                @submit="onSubmit"
            >
                <UFormField name="userid" label="사용자 ID" class="w-full">
                    <UPinInput
                        type="number"
                        :length="4"
                        size="lg"
                        v-model="userIdPayload"
                    />
                </UFormField>

                <!-- errorMessage가 있으면 해당 필드 하단에 인라인 에러가 표시되도록 구성 -->
                <UFormField
                    name="password"
                    label="비밀번호"
                    :error="errorMessage"
                >
                    <UInput
                        v-model="state.password"
                        type="password"
                        placeholder="비밀번호를 입력해주세요"
                        class="w-full"
                    />
                </UFormField>

                <UButton
                    type="submit"
                    label="로그인"
                    block
                    :loading="isLoading"
                    class="mt-6"
                />
            </UForm>
        </UCard>
    </div>
</template>
