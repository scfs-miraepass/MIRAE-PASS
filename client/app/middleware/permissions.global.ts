import type { RouteLocationNormalized } from "#vue-router";

const consoleLog = (message: string, ...args: any[]) => {
    console.log(
        `%cPermissions Middleware%c ${message}`,
        "background: oklch(82.8% 0.189 84.429); color: white; padding: 2px 6px; border-radius: 4px; font-weight: 600;",
        "color: inherit;",
        ...args,
    );
};

export const permissionsMiddleware = (
    to: RouteLocationNormalized,
    from: RouteLocationNormalized,
    permissions?: PermissionCondition,
) => {
    if (import.meta.client) {
        const session = useSession();
        const requiredPermissions =
            permissions ?? (to.meta.permissions as PermissionCondition);

        console.debug(
            `%cPermissions Middleware%c`,
            "background: oklch(82.8% 0.189 84.429); color: white; padding: 2px 6px; border-radius: 4px; font-weight: 600;",
            "color: inherit;",
            requiredPermissions
        );

        // 페이지에 필요한 역할이 정의되지 않았으면 통과
        if (
            requiredPermissions === undefined || 
            requiredPermissions === null || 
            (Array.isArray(requiredPermissions) && requiredPermissions.length === 0)
        ) {
            consoleLog("페이지 권한이 설정되어 있지 않음.");
            return;
        }

        if (session.value) {
            // 사용자의 역할이 페이지에서 요구하는 역할 중 하나가 아니라면
            if (!hasPermission(session.value.permissions, requiredPermissions)) {
                throw createError({
                    statusCode: 403,
                    statusMessage: "접근 권한이 없습니다.",
                });
            }
            consoleLog("권한 확인 완료");
        } else {
            consoleLog("세션이 없음");
        }
        // 세션이 없는 경우는 auth.global.ts 에서 처리하므로 여기서는 다루지 않음.
    }
};

export default defineNuxtRouteMiddleware(permissionsMiddleware);
