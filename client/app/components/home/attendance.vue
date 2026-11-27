<script setup lang="ts">
const toast = useToast();

const { data: attendance, status, error, refresh } = useAsyncData(
    "attendance.status",
    async (_nuxtApp, { signal }) => {
        const req = await $API.getAttendanceAttendanceGet({ signal });
        if (req.error || !req.data.data) {
            throw createError({ statusCode: req.response?.status ?? 503, message: attendanceErrorMessage(req.error) });
        }
        return req.data.data;
    },
    { server: false },
);

const loading = computed(() => status.value === "idle" || status.value === "pending");
const submitting = ref(false);
const filled = computed(() => attendanceFilledCount(attendance.value?.streak ?? 0));
const bonusNext = computed(() => attendance.value?.days_to_bonus === 1);

const description = computed(() => {
    const value = attendance.value;
    if (!value) return "";
    if (value.attended) return `오늘 출석 완료! 다음 보너스까지 ${value.days_to_bonus}일 남았어요.`;
    if (!value.available) return "오늘은 출석하는 날이 아니에요. 주말 · 공휴일 · 방학은 연속 출석에 영향이 없어요.";
    if (bonusNext.value) return `오늘 출석하면 ${ATTENDANCE_BONUS_STREAK}일 연속 보너스를 받아요!`;
    return `보너스(${ATTENDANCE_BONUS_STREAK}일 연속)까지 ${value.days_to_bonus}일 남았어요.`;
});

const buttonLabel = computed(() => {
    const value = attendance.value;
    if (!value) return "";
    if (value.attended) return "출석 완료";
    if (!value.available) return "오늘은 쉬는 날";
    return `출석하기 +${value.reward.toLocaleString()}P`;
});

async function attend() {
    if (!attendance.value || submitting.value) return;
    submitting.value = true;
    const req = await $API.checkAttendanceAttendancePost();
    submitting.value = false;

    if (req.error) {
        toast.add({ title: "출석하지 못했어요.", description: attendanceErrorMessage(req.error), color: "error" });
        // 이미 출석했거나 출석할 수 없는 날이면 최신 상태로 다시 그린다.
        if (req.response?.status === 400 || req.response?.status === 409) refresh();
        return;
    }

    const result = req.data.data;
    toast.add(
        result.bonus
            ? { title: `${result.streak}일 연속 출석! 보너스 ${result.reward.toLocaleString()}P를 받았어요.`, color: "success" }
            : { title: `출석했어요! ${result.reward.toLocaleString()}P를 받았어요.`, color: "success" },
    );
    // 홈의 보유 포인트는 세션 값을 보여주므로 세션을 다시 받아 온다.
    await Promise.all([fetchSession(), refresh()]);
}
</script>

<template>
    <section
        class="mt-3 rounded-2xl p-5 light:bg-default dark:bg-muted"
        aria-labelledby="home-attendance-heading"
        :aria-busy="loading || submitting"
    >
        <div class="flex items-center justify-between gap-2">
            <h2 id="home-attendance-heading" class="text-p1 flex items-center gap-x-2 font-normal">
                <UIcon name="i-ph-calendar-check-fill" class="text-primary" aria-hidden="true" />
                출석체크
            </h2>
            <span
                v-if="attendance"
                class="rounded-full px-2.5 py-0.5 text-ui-p2 font-bold"
                :class="attendance.streak > 0 ? 'bg-primary/10 text-primary' : 'bg-accented light:text-black/50 dark:text-white/50'"
            >
                연속 {{ attendance.streak }}일
            </span>
        </div>

        <div v-if="loading" role="status" aria-label="출석체크 정보를 불러오는 중입니다." class="mt-4">
            <USkeleton class="h-2 w-full rounded-full light:bg-elevated dark:bg-accented/50" />
            <USkeleton class="mt-3 h-4 w-3/4 rounded-full light:bg-elevated dark:bg-accented/50" />
            <USkeleton class="mt-4 h-12 w-full rounded-xl light:bg-elevated dark:bg-accented/50" />
        </div>

        <div v-else-if="error" role="alert" class="mt-3 flex flex-col items-center gap-3 py-2 text-center">
            <p class="text-ui-p2 opacity-50">{{ error.statusCode === 403 ? "출석체크 권한이 없어요." : error.message }}</p>
            <UButton v-if="error.statusCode !== 403" color="neutral" variant="subtle" size="lg" @click="refresh()">다시 시도</UButton>
        </div>

        <template v-else-if="attendance">
            <!-- 이번 보너스 주기(11일) 중 채운 칸 -->
            <div
                class="mt-4 flex gap-1"
                role="img"
                :aria-label="`보너스까지 ${ATTENDANCE_BONUS_STREAK}칸 중 ${filled}칸 채움`"
            >
                <span
                    v-for="i in ATTENDANCE_BONUS_STREAK"
                    :key="i"
                    class="h-2 flex-1 rounded-full transition-colors"
                    :class="i <= filled ? (i === ATTENDANCE_BONUS_STREAK ? 'bg-warning' : 'bg-primary') : 'light:bg-elevated dark:bg-accented'"
                />
            </div>
            <p class="mt-3 text-ui-p2 light:text-black/50 dark:text-white/50">{{ description }}</p>
            <UButton
                size="xl"
                block
                class="mt-4 rounded-xl"
                :color="bonusNext && attendance.available && !attendance.attended ? 'warning' : 'primary'"
                :loading="submitting"
                :disabled="attendance.attended || !attendance.available"
                @click="attend"
            >
                {{ buttonLabel }}
            </UButton>
        </template>
    </section>
</template>
