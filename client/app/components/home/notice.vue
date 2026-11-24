<script setup lang="ts">
import { UserPermission } from "@miraepass/api-client";
import NoticeListItem from "~/components/notice/listItem.vue";

// 홈에 보여줄 최근 공지 개수
const HOME_NOTICE_COUNT = 3;

const session = useSession();
const toast = useToast();
const canViewNotices = computed(() => hasPermission(session.value?.permissions, UserPermission.VIEW_POST));

const { data: notices } = useAsyncData("notices.home", async (_nuxtApp, { signal }) => {
    if (!canViewNotices.value) return [];
    const req = await $API.getPostsPostsGet({
        query: { content_kind: NOTICE_CONTENT_KIND, size: HOME_NOTICE_COUNT },
        signal,
    });
    if (req.error) {
        if (!signal.aborted) toast.add({ title: "공지 목록을 불러오지 못했어요.", color: "error" });
        return [];
    }
    return toNoticeItems(req.data.data);
}, { server: false, watch: [canViewNotices] });
</script>

<template>
    <section
        v-if="canViewNotices && notices?.length"
        class="light:bg-default dark:bg-muted rounded-2xl px-0.5 py-2"
        aria-labelledby="home-notices-heading"
    >
        <div class="flex items-center justify-between pt-1 pb-0.5 pl-5.5 pr-3">
            <h2 id="home-notices-heading" class="text-p2 font-bold light:text-black/50 dark:text-white/50">공지사항</h2>
            <NuxtLink
                to="/notices"
                class="flex min-h-9 items-center gap-0.5 rounded-xl px-2.5 text-ui-p2 light:text-black/50 dark:text-white/50 transition-all active:scale-95 active:bg-accented focus-visible:outline-2 focus-visible:outline-primary"
            >
                전체 보기
                <UIcon name="i-ph-caret-right" aria-hidden="true" />
            </NuxtLink>
        </div>
        <ul>
            <li v-for="notice in notices" :key="notice.id">
                <NoticeListItem :notice="notice" />
            </li>
        </ul>
    </section>
</template>
