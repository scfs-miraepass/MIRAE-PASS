<script setup lang="ts">
const route = useRoute()
const noticeId = computed(() => String(route.params.id))

const { data: notice, status, error, refresh } = useAsyncData(
    computed(() => `notice-${noticeId.value}`),
    async () => {
        const response = await $fetch<{ data: { title: string; text: string } }>(
            `/api/posts/notices/${encodeURIComponent(noticeId.value)}`,
        )
        return response.data
    },
    { server: false },
)
</script>

<template>
    <section class="mx-auto w-full max-w-xl pb-6">
        <NuxtLink to="/" class="mb-4 inline-flex min-h-11 items-center gap-2 font-medium text-blue-800 dark:text-blue-200">
            <UIcon name="i-ph-arrow-left" aria-hidden="true" />
            홈으로
        </NuxtLink>

        <p v-if="status === 'idle' || status === 'pending'" role="status">공지를 불러오는 중입니다.</p>
        <div v-else-if="error" role="alert">
            <p v-if="error.statusCode === 404">공지를 찾을 수 없습니다.</p>
            <p v-else-if="error.statusCode === 403">공지를 볼 수 있는 권한이 없습니다.</p>
            <template v-else>
                <p>공지를 불러오지 못했습니다.</p>
                <UButton class="mt-3" @click="refresh()">다시 시도</UButton>
            </template>
        </div>
        <article v-else-if="notice" class="overflow-hidden rounded-xl border border-blue-200 dark:border-blue-800">
            <header class="bg-blue-50 px-5 py-4 dark:bg-blue-950/40">
                <p class="mb-1 text-sm font-medium text-blue-800 dark:text-blue-200">공지사항</p>
                <h1 class="break-words text-xl font-bold">{{ notice.title }}</h1>
            </header>
            <p class="whitespace-pre-wrap break-words px-5 py-5 leading-relaxed">{{ notice.text }}</p>
        </article>
    </section>
</template>
