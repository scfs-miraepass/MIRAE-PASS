<script setup lang="ts">
import { Motion } from "motion-v";
import type { User, GetLimitResponse } from '@/client'
import { useElementSize } from '@vueuse/core'

definePageMeta({
    middleware: [
        (to, from) => {
            const action = to.query.a as string | undefined
            if (action != 'grant' && action != 'deduct') {
                return navigateTo("/", { replace: true });
            }
            const userData = useState<User | undefined>(
                "system.user-select.uesr",
            );
            if (!userData.value) {
                return navigateTo("/", { replace: true });
            }
        },
    ],
    permissions: { or: [ UserPermission._GRANT_POINT, UserPermission._DEDUCT_POINT ] } as PermissionCondition
});

const route = useRoute();
const session = useSession();
const userData = useState<User>("system.user-select.uesr");
const amount = ref<number>(0);
const isConfirm = ref<boolean>(false);
const isLoading = ref<boolean>(false);
const isComplete = ref<boolean>(false);
const memoContainer = ref();
const memoValue = ref<string>('');
const { width: memoWidth } = useElementSize(memoContainer)
const isDeduct = computed<boolean>(() => route.query.a == "deduct");
const pointLimit = ref<GetLimitResponse>({
    limit: 0,
    target_limit: 0,
});

const pointError = ref<boolean>(false);
const [pointScope, pointAnimate] = useAnimate();

const keypad = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];

if (import.meta.client) {
    if (!isDeduct.value) {
        const req = await $API.getLimitPointLimitTargetUserIdGet({
            path: {
                target_user_id: userData.value.id!,
            },
        });
        if (req.error) {
            // TODO: 에러 처리
        } else {
            pointLimit.value = req.data.data;
        }
    }
}

const triggerVibration = (pattern?: number) => {
    // 모바일에서 진동 함수
    // TODO: iOS 사파리에선 API 지원 안하는데 어떻게 하실
    if (typeof window !== "undefined" && window.navigator.vibrate) {
        window.navigator.vibrate(pattern ?? 10);
    }
};

const onInput = (val: string) => {
    triggerVibration();
    const currentStr = String(amount.value);
    if (currentStr.length >= 6) return; // 최대 6자리 제한

    // 초기값이 0이면 새 숫자로 교체, 아니면 뒤에 추가
    const _new = Number(amount.value === 0 ? val : currentStr + val);
    const limit = isDeduct.value
        ? userData.value.point!
        : Math.min(pointLimit.value!.target_limit, pointLimit.value!.limit)!;
    if (_new > limit) {
        triggerVibration(20);
        setTimeout(() => triggerVibration(100), 100);

        pointError.value = true;
        pointAnimate(
            pointScope.value,
            { translate: "20px" },
            { type: "spring", stiffness: 700, damping: 3, mass: 0.5 },
        );
        setTimeout(
            () =>
                pointAnimate(
                    pointScope.value,
                    { translate: "0" },
                    { type: "spring", stiffness: 700, damping: 3, mass: 0.5 },
                ),
            25,
        );
        return;
    }
    pointError.value = false;
    amount.value = _new;
};

const onDelete = () => {
    triggerVibration();
    const currentStr = String(amount.value);
    if (currentStr.length <= 1) {
        amount.value = 0;
    } else {
        amount.value = Number(currentStr.slice(0, -1));
    }
    pointError.value = false;
};

const onButton = async () => {
    isLoading.value = true;

    let req;
    const history_type = session.value!.history_type || (session.value?.type == "teacher"? "teacher":"etc")
    const body = {
        target_user_id: userData.value.id!,
        amount: amount.value,
        change_type: history_type,
        memo: memoValue.value.length > 0? memoValue.value : undefined
    }
    if (isDeduct.value) {
        req = await $API.deductPointsPointDeductPost({ body: body });
    } else {
        req = await $API.grantPointsPointGrantPost({ body: body });
    }
    if (req.error) {
        // TODO: 에러처리
        return;
    }
    isComplete.value = true;
};

const onMemoInput = (event: InputEvent) => {
    memoValue.value = (event.target as HTMLInputElement).value;
}
</script>

<template>
    <div class="flex-1 overflow-hidden flex flex-col relative">
        <div class="flex items-center mb-4 z-10">
            <UButton
                :disabled="isConfirm"
                @click="$router.back()"
                color="neutral"
                variant="ghost"
                icon="i-ph-caret-left-bold"
                class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented"
                size="xl"
            />
        </div>
        <div
            class="flex-1 flex flex-col transition"
            :class="{
                'pointer-events-none opacity-0 -translate-x-4': isComplete,
            }"
        >
            <div class="flex-1 flex flex-col">
                <!-- 상단 타이틀 -->
                <div class="mt-10" v-if="isDeduct">
                    <p
                        class="text-p0 light:text-black/70 dark:text-white/70 font-normal"
                    >
                        <span
                            class="font-bold light:text-black dark:text-white"
                            >{{ userData.name }}</span
                        >
                        {{ userData.type == "student" ? "학생" : "선생님" }}의
                        포인트에서
                    </p>
                    <p
                        class="text-p0 text-black/70 dark:text-white/70 font-normal"
                    >
                        얼마나 결제할까요?
                    </p>
                </div>
                <div class="mt-10" v-else>
                    <p
                        class="text-p0 light:text-black/70 dark:text-white/70 font-normal"
                    >
                        <span
                            class="font-bold light:text-black dark:text-white"
                            >{{ userData.name }}</span
                        >
                        {{ userData.type == "student" ? "학생" : "선생님" }}에게 포인트를
                    </p>
                    <p
                        class="text-p0 text-black/70 dark:text-white/70 font-normal"
                    >
                        얼마나 지급할까요?
                    </p>
                </div>

                <!-- 지급/차감할 포인트 UI -->
                <div
                    class="flex flex-col items-center justify-center flex-1 mb-11.5"
                >
                    <div class="flex items-center">
                        <span class="text-h2 font-bold">{{
                            amount.toLocaleString()
                        }}</span>
                        <span class="text-h4">P</span>
                    </div>
                    <p
                        class="text-ui-p2 mt-2 px-3 py-1.5 rounded-xl dark:bg-muted light:text-black/45 dark:text-white/40"
                        :class="{ 'text-error!': pointError }"
                        ref="pointScope"
                    >
                        <template v-if="isDeduct">
                            {{ userData.point!.toLocaleString() }} 포인트
                            사용가능
                        </template>
                        <template v-else>
                            {{
                                Math.min(
                                    pointLimit.target_limit,
                                    pointLimit.limit,
                                ).toLocaleString()
                            }}
                            포인트 지급가능
                        </template>
                    </p>

                    <Motion
                        as="button"
                        class="flex justify-end max-w-[90%] overflow-clip w-fit text-ui-p2 px-3 py-1.5 rounded-xl dark:bg-muted light:text-black/45 dark:text-white/40 disabled:opacity-50"
                        :initial="{ marginTop: '-1.625rem', opacity: 0 }"
                        :animate="{
                            marginTop: !isConfirm ? '-1.625rem' : '0.5rem',
                            opacity: !isConfirm ? 0 : 1
                        }"
                        :transition="{
                            duration: 0.8,
                            ease: [0, 0.71, 0.2, 1.01],
                        }"
                    >
                        <span class="absolute opacity-0 pointer-events-none" ref="memoContainer">{{ memoValue || '메모' }}</span>
                        <input type="text" class="outline-none min-w-6" placeholder="메모" v-model="memoValue" @input="onMemoInput" :style="{ width: `${memoWidth}px` }" />
                    </Motion>
                </div>
            </div>
            <p
                class="text-ui-p2 mb-5 flex items-center justify-center light:text-black/50 dark:text-white/50 transition-opacity"
                :class="[isConfirm ? 'opacity-100' : 'opacity-0']"
            >
                <UIcon name="i-ph-warning" class="mr-1" />
                {{
                    isDeduct
                        ? `${session?.type == 'service'? '결제가':'차감이'} 진행된 이후에는 취소할 수 없어요.`
                        : "지급된 이후에는 회수할 수 없어요."
                }}
            </p>
            <div class="flex gap-3 mb-3">
                <UButton
                    class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
                    :disabled="amount <= 0 || pointError"
                    @click="
                        () => {
                            isConfirm = true;
                        }
                    "
                    v-if="!isConfirm"
                >
                    <p class="text-p0">다음</p>
                </UButton>
                <UButton
                    class="rounded-2xl justify-center flex py-4.5 transition-opacity w-full"
                    :disabled="isLoading"
                    :loading="isLoading"
                    @click="onButton"
                    v-else
                >
                    <p class="text-p0">
                        {{
                            !isLoading
                                ? isDeduct
                                    ? `${session?.type == 'service'? '결제':'차감'}하기`
                                    : "지급하기"
                                : "처리중.."
                        }}
                    </p>
                </UButton>
                <Motion
                    class="aspect-square shrink-0 flex w-15"
                    :initial="{ marginRight: '-100%' }"
                    :animate="{
                        marginRight: !isConfirm || isLoading ? '-100%' : 0,
                    }"
                    :transition="{
                        type: 'spring',
                        duration: !isConfirm || isLoading ? 2.4 : 0.8,
                        bounce: 0.15,
                    }"
                >
                    <UButton
                        color="error"
                        variant="soft"
                        class="rounded-2xl justify-center flex py-4.5 transition-opacity text-nowrap w-full h-full"
                        :disabled="isLoading"
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
            <Motion
                as="div"
                class="w-full h-[30vh] grid grid-cols-3 grid-rows-4"
                :initial="{ marginBottom: 0 }"
                :animate="{ marginBottom: isConfirm ? '-30vh' : 0 }"
                :transition="{
                    type: 'spring',
                    stiffness: 950,
                    damping: 80,
                    mass: 1,
                }"
            >
                <button
                    v-for="num in keypad"
                    :key="num"
                    @click="onInput(num)"
                    class="rounded-xl gap-2 px-5.5 py-3 transition-all active:scale-95 active:opacity-50 active:bg-accented text-h6 text-center"
                >
                    {{ num }}
                </button>
                <div />
                <button
                    @click="onInput('0')"
                    class="rounded-xl gap-2 px-5.5 py-3 transition-all active:scale-95 active:opacity-50 active:bg-accented text-h6 text-center"
                >
                    0
                </button>
                <button
                    @click="onDelete"
                    class="rounded-xl gap-2 px-5.5 py-3 transition-all active:scale-95 active:opacity-50 active:bg-accented text-h5 text-center"
                >
                    <UIcon name="i-ph-arrow-left" />
                </button>
            </Motion>
        </div>
        <div
            class="pt-10 h-full w-full flex flex-col items-center justify-center absolute transition"
            :class="{
                'pointer-events-none opacity-0 translate-x-4': !isComplete,
            }"
        >
            <div
                class="h-full flex flex-col justify-center items-center text-ui-p1 opacity-50"
            >
                <UIcon name="i-ph-check-circle" class="text-h2 mb-1.5" />
                {{
                    isDeduct
                        ? `${session?.type == 'service'? '결제가':'차감이'} 정상적으로 되었어요.`
                        : "정상적으로 지급되었어요."
                }}
            </div>
            <NuxtLink
                :to="`/system/userSelect?a=${isDeduct? 'deduct-point':'grant-point'}`"
                v-slot="{ navigate }"
                custom
            >
                <UButton
                    class="rounded-2xl justify-center flex py-4.5 transition-opacity mb-3 w-full"
                    @click="navigate()"
                >
                    <p class="text-p0">돌아가기</p>
                </UButton>
            </NuxtLink>
        </div>
    </div>
</template>
