<script setup lang="ts">
import { UserPermission } from "@miraepass/api-client";
import NoticeListItem from "~/components/notice/listItem.vue";
import NoticeListSkeleton from "~/components/notice/listSkeleton.vue";

definePageMeta({ permissions: [UserPermission.VIEW_POST] });

// 한 번에 불러올 공지 개수
const NOTICE_PAGE_SIZE = 20;

const page = ref(1);
const maxPage = ref(1);
const notices = ref<NoticeItem[]>([]);

const { status, error, refresh } = useAsyncData("notices.list", async (_nuxtApp, { signal }) => {
    const req = await $API.getPostsPostsGet({
        query: { content_kind: NOTICE_CONTENT_KIND, page: page.value, size: NOTICE_PAGE_SIZE },
        signal,
    });
    if (req.error) throw createError({ statusCode: req.response?.status ?? 503 });

    maxPage.value = Number(req.response?.headers.get("X-MAX-PAGE")) || 1;
    const items = toNoticeItems(req.data.data);
    // 첫 페이지는 새로 채우고, 다음 페이지부터는 이어 붙인다.
    notices.value = page.value === 1 ? items : [...notices.value, ...items];
    return true;
}, { server: false, watch: [page] });

const loading = computed(() => status.value === "idle" || status.value === "pending");
const hasMore = computed(() => page.value < maxPage.value);
</script>

<template>
    <div class="mb-4 flex items-center">
        <NuxtLink to="/" v-slot="{ navigate }" custom>
            <UButton @click="navigate()" color="neutral" variant="ghost" icon="i-ph-caret-left-bold" aria-label="홈으로" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="xl" />
        </NuxtLink>
        <h1 class="ml-1 text-2xl font-bold text-highlighted">공지사항</h1>
    </div>

    <div class="flex flex-1 flex-col rounded-2xl px-0.5 py-2 light:bg-default dark:bg-muted">
        <ul v-if="notices.length">
            <li v-for="notice in notices" :key="notice.id">
                <NoticeListItem :notice="notice" />
            </li>
        </ul>

        <NoticeListSkeleton v-if="loading" :count="notices.length ? 2 : 6" />
        <div v-else-if="error" role="alert" class="flex flex-col items-center justify-center gap-3 px-5 py-6 text-center" :class="{ 'flex-1': !notices.length }">
            <UIcon name="i-ph-wifi-slash-thin" class="text-h2 opacity-50" aria-hidden="true" />
            <p class="text-ui-p1 opacity-50">
                {{ error.statusCode === 403 ? "공지를 볼 수 있는 권한이 없어요." : "공지 목록을 불러오지 못했어요." }}
            </p>
            <UButton v-if="error.statusCode !== 403" color="neutral" variant="subtle" size="lg" @click="refresh()">다시 시도</UButton>
        </div>
        <div v-else-if="!notices.length" class="flex flex-1 flex-col items-center justify-center py-10 text-ui-p1 opacity-50">
            <UIcon name="i-ph-megaphone-simple-thin" class="mb-1.5 text-h2" aria-hidden="true" />
            아직 등록된 공지가 없어요.
        </div>
        <div v-else-if="hasMore" class="px-3 pt-1 pb-1">
            <UButton block color="neutral" variant="ghost" size="lg" class="gap-1 rounded-xl text-ui-p2 light:text-black/50 dark:text-white/50" @click="page++">
                더 보기
                <UIcon name="i-ph-caret-down" aria-hidden="true" />
            </UButton>
        </div>
    </div>
</template>
