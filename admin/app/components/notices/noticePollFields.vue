<script setup lang="ts">
import {
    POLL_OPTION_MAX,
    POLL_OPTION_MAX_LENGTH,
    POLL_OPTION_MIN,
    POLL_QUESTION_MAX_LENGTH,
    type PollForm,
} from "~/utils/notice";

// optionsLocked: 응답이 있는 설문은 선택지를 바꿀 수 없다. (서버도 409로 막음)
const { disabled = false, optionsLocked = false } = defineProps<{
    disabled?: boolean;
    optionsLocked?: boolean;
}>();
const form = defineModel<PollForm>({ required: true });

function addOption() {
    if (form.value.options.length < POLL_OPTION_MAX) form.value.options.push("");
}

function removeOption(index: number) {
    if (form.value.options.length > POLL_OPTION_MIN) form.value.options.splice(index, 1);
}
</script>

<template>
    <div class="space-y-4 rounded-lg border border-default p-4">
        <UFormField label="질문" name="poll-question" required :hint="`${form.question.length}/${POLL_QUESTION_MAX_LENGTH}`">
            <UInput
                v-model="form.question"
                class="w-full"
                placeholder="예: 체육대회 날 점심 메뉴로 무엇이 좋을까요?"
                :maxlength="POLL_QUESTION_MAX_LENGTH"
                :disabled="disabled"
            />
        </UFormField>

        <UFormField
            label="선택지"
            name="poll-options"
            required
            :hint="`${form.options.length}/${POLL_OPTION_MAX}`"
            :help="optionsLocked ? '응답이 있는 설문은 선택지를 바꿀 수 없습니다.' : undefined"
        >
            <div class="space-y-2">
                <div v-for="(_, index) in form.options" :key="index" class="flex items-center gap-2">
                    <UInput
                        v-model="form.options[index]"
                        class="w-full"
                        :placeholder="`선택지 ${index + 1}`"
                        :maxlength="POLL_OPTION_MAX_LENGTH"
                        :disabled="disabled || optionsLocked"
                    />
                    <UButton
                        v-if="!optionsLocked"
                        icon="i-lucide-x"
                        color="neutral"
                        variant="ghost"
                        class="cursor-pointer"
                        :aria-label="`선택지 ${index + 1} 삭제`"
                        :disabled="disabled || form.options.length <= POLL_OPTION_MIN"
                        @click="removeOption(index)"
                    />
                </div>
                <UButton
                    v-if="!optionsLocked"
                    icon="i-lucide-plus"
                    color="neutral"
                    variant="soft"
                    size="sm"
                    class="cursor-pointer"
                    :disabled="disabled || form.options.length >= POLL_OPTION_MAX"
                    @click="addOption"
                >
                    선택지 추가
                </UButton>
            </div>
        </UFormField>

        <div class="grid gap-4 sm:grid-cols-2">
            <UFormField label="마감 시각" name="poll-closes-at" help="비워 두면 마감 없이 계속 응답을 받습니다.">
                <UInput v-model="form.closesAt" type="datetime-local" class="w-full" :disabled="disabled" />
            </UFormField>
            <UFormField label="응답 방식" name="poll-allow-multiple">
                <UCheckbox v-model="form.allowMultiple" label="여러 개 선택 허용" class="mt-2" :disabled="disabled" />
            </UFormField>
        </div>
    </div>
</template>
