<script setup lang="ts">
import Section from "~/components/setting/section.vue";
import History from "~/components/home/history/index.vue";
import Point from "~/components/home/point.vue";
import Ranking from "@/components/home/section/ranking.vue";
import Stamp from "@/components/home/section/stamp.vue";
import StampGive from "@/components/home/section/stampGive.vue";
import GrantPoint from "@/components/home/section/grantPoint.vue";
import DeductPoint from "@/components/home/section/deductPoint.vue";
import Karaoke from "@/components/home/section/karaoke.vue";

const session = useSession()
const sectionItem = computed(() => {
    const items = []
    const permissions = session.value!.permissions

    if (hasPermission(permissions, UserPermission.GRANT_POINT)) items.push(GrantPoint)
    if (hasPermission(permissions, UserPermission.DEDUCT_POINT)) items.push(DeductPoint)
    if (hasPermission(permissions, UserPermission.VIEW_RANK)) items.push(Ranking)
    if (hasPermission(permissions, UserPermission.GIVE_STAMP)) items.push(StampGive)
    if (hasPermission(permissions, UserPermission.VIEW_STAMP)) items.push(Stamp)
    if (hasPermission(permissions, UserPermission.VIEW_KARAOKE)) items.push(Karaoke)

    return items
})
</script>

<template>
    <div class="w-full flex items-center justify-between opacity-50 -mt-2">
        <p class="text-ui-p1 font-medium light:text-black/50 dark:text-white/50" v-if="session!.type == 'student'">{{ session!.id }} {{ session!.name }}</p>
        <p class="text-ui-p1 font-medium light:text-black/50 dark:text-white/50" v-else>{{ session!.name }}{{ session!.type == 'teacher'? ' 선생님':'' }}</p>
        <NuxtLink to="/setting" v-slot="{ navigate }" custom>
            <UButton @click="navigate()" color="neutral" variant="ghost" icon="i-ph-gear-fill" class="p-2 rounded-2xl hover:bg-accented active:bg-accented focus-visible:bg-accented" size="xl" />
        </NuxtLink>
    </div>
    <div class="pb-2 mt-2.5 flex-1 flex flex-col">
        <Point v-if="hasPermission(session!.permissions, UserPermission.VIEW_POINT)" />
        <Section class="mt-3" v-if="sectionItem.length > 0">
            <component v-for="i in sectionItem" :is="i" />
        </Section>
        <template v-if="hasPermission(session!.permissions, UserPermission.VIEW_POINT_HISTORY)">
            <hr class="my-3 border-default" />
            <History />
        </template>
    </div>
</template>