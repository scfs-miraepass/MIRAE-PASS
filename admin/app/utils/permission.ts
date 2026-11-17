import { UserPermission } from '@miraepass/api-client'

export type PermissionCondition = UserPermission | number | Array<UserPermission | number> | { or: UserPermission[] };

export const NOTICE_MANAGEMENT_PERMISSIONS = { or: [UserPermission.CREATE_POST, UserPermission.MANAGE_POST] };

export function hasPermission(
    userPermissions: UserPermission | number | undefined | null, 
    targetPermissions: PermissionCondition
): boolean {
    const perms = userPermissions ?? UserPermission.NONE;
    
    if (Array.isArray(targetPermissions)) {
        return targetPermissions.every(target => (perms & target) === target);
    }

    if (typeof targetPermissions === "object") {
        return targetPermissions.or.some(target => (perms & target) === target);
    }

    return (perms & targetPermissions) === targetPermissions;
}
