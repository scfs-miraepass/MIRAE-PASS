<script setup lang="ts">
import { UserPermission } from "@miraepass/api-client";

definePageMeta({ permissions: [UserPermission.VIEW_POST] });

const route = useRoute();
const router = useRouter();
const noticeId = computed(() => Number(route.params.id));

const { data: notice, status, error, refresh } = useAsyncData(
    computed(() => `notices.detail.${noticeId.value}`),
    async (_nuxtApp, { signal }) => {
        if (!Number.isSafeInteger(noticeId.value) || noticeId.value < 1) {
            throw createError({ statusCode: 404 });
        }

        const req = await $API.getPostPostsPostIdGet({ path: { post_id: noticeId.value }, signal });
        if (req.error) throw createError({ statusCode: req.response?.status ?? 503 });

        const item = req.data.data ? toNoticeItem(req.data.data) : null;
        if (!item) throw createError({ statusCode: 404 });
        return item;
    },
    { server: false },
);

const loading = computed(() => status.value === "idle" || status.value === "pending");

// 앱 안에서 들어온 경우 이전 화면으로, 링크로 바로 들어온 경우 공지 목록으로 돌아간다.
function goBack() {
    if (window.history.state?.back) router.back();
    else navigateTo("/notices");
}
</script>

<template>
    <div class="mb-4 flex items-center">
        <UButton @click="goBack" color="neutral" variant="ghost" icon="i-ph-caret-left-bold" aria-label="뒤로 가기" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="xl" />
        <p class="ml-1 text-2xl font-bold text-highlighted">공지사항</p>
    </div>

    <div v-if="loading" role="status" aria-label="공지를 불러오는 중입니다." class="rounded-2xl p-5 light:bg-default dark:bg-muted">
        <USkeleton class="mb-3 h-6 w-4/5 rounded-full light:bg-elevated dark:bg-accented/50" />
        <USkeleton class="h-3.5 w-32 rounded-full light:bg-elevated dark:bg-accented/50" />
        <hr class="my-5 border-default" />
        <div class="space-y-2.5">
            <USkeleton class="h-4.5 w-full rounded-full light:bg-elevated dark:bg-accented/50" />
            <USkeleton class="h-4.5 w-full rounded-full light:bg-elevated dark:bg-accented/50" />
            <USkeleton class="h-4.5 w-2/3 rounded-full light:bg-elevated dark:bg-accented/50" />
        </div>
    </div>

    <div
        v-else-if="error"
        role="alert"
        class="flex flex-col items-center justify-center gap-3 rounded-2xl px-5 py-16 text-center light:bg-default dark:bg-muted"
    >
        <UIcon
            :name="error.statusCode === 404 ? 'i-ph-file-x-thin' : error.statusCode === 403 ? 'i-ph-lock-simple-thin' : 'i-ph-wifi-slash-thin'"
            class="text-h2 opacity-50"
            aria-hidden="true"
        />
        <p class="text-ui-p1 opacity-50">
            <template v-if="error.statusCode === 404">공지를 찾을 수 없어요.<br />삭제되었거나 잘못된 주소예요.</template>
            <template v-else-if="error.statusCode === 403">공지를 볼 수 있는 권한이 없어요.</template>
            <template v-else>공지를 불러오지 못했어요.</template>
        </p>
        <UButton v-if="error.statusCode !== 404 && error.statusCode !== 403" color="neutral" variant="subtle" size="lg" @click="refresh()">다시 시도</UButton>
        <UButton v-else to="/notices" color="neutral" variant="subtle" size="lg">공지 목록 보기</UButton>
    </div>

    <article v-else-if="notice" class="rounded-2xl p-5 light:bg-default dark:bg-muted">
        <header>
            <h1 class="text-p0 font-bold break-words leading-snug">{{ notice.title }}</h1>
            <p v-if="notice.createdAt" class="mt-2 text-ui-p2 light:text-black/50 dark:text-white/50">
                <time :datetime="notice.createdAt.toISOString()">{{ noticeDateTimeLabel(notice.createdAt) }}</time>
                <span v-if="notice.edited"> · 수정됨</span>
            </p>
        </header>
        <hr class="my-5 border-default" />
        <p class="text-p1 font-normal leading-relaxed whitespace-pre-wrap break-words">{{ notice.text }}</p>
    </article>
</template>
