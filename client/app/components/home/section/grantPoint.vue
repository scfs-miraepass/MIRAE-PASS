<script setup lang="ts">
import PageButton from "~/components/setting/object.vue";

const session = useSession();
const { pending, data: limitResult } = await useAsyncData(
    'grant_point.point_limit',
    (_nuxtApp, { signal }) => $API.getLimitSessionPointLimitGet({ signal }),
    {
        transform(data) {
            return {
                ...data,
                expiresAt: Date.now() + 10 * 1000
            }
        },
        getCachedData(key, nuxtApp) {
            const cachedData = nuxtApp.payload.data[key] || nuxtApp.static.data[key];
            if (cachedData && cachedData.expiresAt >= Date.now()) {
                return cachedData;
            }
            return undefined;
        }
    }
)

const pointLimit = computed<number>(() => {
    if (limitResult.value?.data?.success) {
        return limitResult.value.data.data;
    }
    return 0;
});
</script>

<template>
    <NuxtLink to="/system/userSelect?a=grant-point" v-slot="{ navigate }" custom>
        <PageButton @click="navigate()" icon="i-ph-hand-coins" label="포인트 지급" :disabled="pointLimit <= 0">
            <template #value>
                <USkeleton class="blur-xs" v-if="pending">
                    1000 포인트 남음
                </USkeleton>
                <template v-else-if="hasPermission(session!.permissions, UserPermission.NO_LIMIT_POINT)">
                    제한 없음
                </template>
                <template v-else>
                    {{ pointLimit }} 포인트 남음
                </template>
            </template>
        </PageButton>
    </NuxtLink>
</template>