<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

defineProps<{
    collapsed?: boolean
}>()

const session = useSession()
const colorMode = useColorMode()

const userName = computed(() => `${session.value!.name}${ session.value!.type == 'teacher'? ' 선생님': '' }`)

const items = computed<DropdownMenuItem[][]>(() => (
    [
        [
            {
                label: '테마',
                icon: 'i-lucide-sun-moon',
                children: [
                    {
                        label: '라이트',
                        icon: 'i-lucide-sun',
                        type: 'checkbox',
                        checked: colorMode.value === 'light' && colorMode.preference !== 'system',
                        onSelect: (e: Event) => {
                            e.preventDefault()
                            colorMode.preference = 'light'
                        }
                    },
                    {
                        label: '다크',
                        icon: 'i-lucide-moon',
                        type: 'checkbox',
                        checked: colorMode.value === 'dark' && colorMode.preference !== 'system',
                        onSelect: (e: Event) => {
                            e.preventDefault()
                            colorMode.preference = 'dark'
                        }
                    },
                    {
                        label: '시스템',
                        icon: 'i-lucide-monitor',
                        type: 'checkbox',
                        checked: colorMode.preference === 'system',
                        onSelect: (e: Event) => {
                            e.preventDefault()
                            colorMode.preference = 'system'
                        }
                    }
                ]
            },
            {
                label: '로그아웃',
                icon: 'i-lucide-log-out',
                to: "/logout",
                color: "error"
            }
        ]
    ]
))
</script>

<template>
    <UDropdownMenu
        :items="items"
        :content="{ align: 'center', collisionPadding: 12 }"
        :ui="{ content: collapsed ? 'w-48' : 'w-(--reka-dropdown-menu-trigger-width)' }"
    >
        <UButton
            v-bind="{
                label: collapsed ? undefined : userName,
                trailingIcon: collapsed ? undefined : 'i-lucide-chevrons-up-down'
            }"
            color="neutral"
            variant="ghost"
            block
            :square="collapsed"
            class="data-[state=open]:bg-elevated"
            :ui="{ trailingIcon: 'text-dimmed' }"
        />
    </UDropdownMenu>
</template>