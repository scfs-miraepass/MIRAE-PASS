<script setup lang="ts">
import type { InputEmit } from '@/components/numberPad/index.vue'

defineProps<{
    title: string,
    description: string,
}>()

const error = ref<boolean>(false);

// 처음에 defineModel 안에다가 get/set 넣어서 value_payload를 받아서 그걸 model get/set 할때 처리해서 model에 최종 문자열로 전달했음
// 근대 model의 get은 부모, 자식 모두에서 model를 가져올때 호출되지만, set은 자식에서 model이 지정될때만 되어서, 부모에서 수정해도 실제 value_payload에 반영되지 못했음
// 해결 하기 위해 model를 정적으로 하고, value_payload를 써서 computed를 써서 처리하도록 했음
const model = defineModel<string>({ default: '' });
const value_payload = computed<string[]>({
    get: () => model.value.split(''),
    set: (value) => { model.value = value.join('') },
});
let vibration_fun: InputEmit["vibration"] | undefined;

export interface SubmitEmit {
    event: MouseEvent,
    inputVibration: typeof inputVibration,
    vibration: InputEmit["vibration"],
    error: typeof error
}
const emit = defineEmits<{
    'submit': [SubmitEmit]
    'input': [InputEmit]
    'delete': []
}>()

const [pinInputScope, pinInputAnimate] = useAnimate();

const inputVibration = () => {
    pinInputAnimate(
        pinInputScope.value,
        { translate: "20px" },
        { type: "spring", stiffness: 700, damping: 3, mass: 0.5 },
    );
    setTimeout(
        () =>
            pinInputAnimate(
                pinInputScope.value,
                { translate: "0" },
                { type: "spring", stiffness: 700, damping: 3, mass: 0.5 },
            ),
        25,
    );
}

const onInput = ({ value, vibration }: InputEmit) => {
    if (vibration_fun == undefined) {
        vibration_fun = vibration
    }
    if (model.value.length >= 6) {
        vibration(20);
        setTimeout(() => vibration(100), 100);
        inputVibration()
        error.value = true;
        return;
    }
    error.value = false;
    model.value += value
    emit('input', { value, vibration })
}
const onDelete = () => {
    error.value = false;
    model.value = model.value.length <= 1 ? "" : model.value.slice(0, -1)
    emit('delete')
};

const onClick = (event: MouseEvent) => {
    emit('submit', { event, inputVibration, vibration: vibration_fun!, error: error })
}
</script>

<template>
    <div class="flex-1 flex flex-col">
        <div class="flex-1 flex flex-col justify-center items-center pb-5">
            <div class="text-black/70 dark:text-white/70 text-center mb-5">
                <p class="text-p0 font-normal">
                    {{ title }}
                </p>
                <p class="text-ui-p2 mt-1">
                    {{ description }}
                </p>
            </div>

            <UPinInput
                type="text"
                :length="6"
                size="xl"
                class="pointer-events-none"
                color="error"
                v-model="value_payload"
                :highlight="error"
                mask

                ref="pinInputScope"
            />
        </div>

        <!-- 버튼(다음, 취소, 진행) UI -->
        <div class="flex gap-3 mb-3">
            <UButton
                class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
                :disabled="model.length != 6"
                @click="onClick"
            >
                <p class="text-p0">다음</p>
            </UButton>
        </div>

        <!-- 키패드 UI -->
        <NumberPad
            @input="onInput"
            @delete="onDelete"
        />
    </div>
</template>