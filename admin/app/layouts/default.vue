<script setup lang="ts">
import type { NavigationMenuItem } from '@nuxt/ui'
import { UserPermission } from '@/client'

const session = useSession()
const open = ref(false)

const links = computed(() => {

    const items: NavigationMenuItem[] = []

    if (hasPermission(session.value?.permissions, UserPermission.MANAGE_USER)) {
        items.push({
            label: "사용자 관리",
            icon: 'i-lucide-users',
            to: '/users'
        })
    }

    if (hasPermission(session.value?.permissions, UserPermission.MANAGE_KARAOKE)) {
        items.push({
            label: "노래방 경매 관리",
            icon: 'i-lucide-mic-vocal',
            to: '/karaoke'
        })
    }

    return items
})
</script>

<template>
    <UDashboardGroup unit="rem">
        <!-- 메뉴 -->
        <UDashboardSidebar
            id="default"
            v-model:open="open"
            collapsible
            resizable
            class="bg-elevated/25"
            :ui="{ header: 'flex items-center justify-center' }"
        >
            <template #header="{ collapsed }">
                <LogoSymbol :size="25" />
                <p class="font-semibold text-xl tracking-wide" v-if="!collapsed">미래패스</p>
            </template>
            <template #default="{ collapsed }">
                <UNavigationMenu
                    :collapsed="collapsed"
                    :items="links"
                    orientation="vertical"
                    tooltip
                    popover
                />
            </template>

            <template #footer="{ collapsed }">
                <UserMenu :collapsed="collapsed" />
            </template>
        </UDashboardSidebar>

        <!-- Panel -->
        <slot />
    </UDashboardGroup>
</template>