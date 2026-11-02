import { UserPermission } from '@/client'

export function hasPermission(
    userPermissions: UserPermission | number | undefined | null, 
    targetPermissions: UserPermission | number | Array<UserPermission | number>
): boolean {
    const perms = userPermissions ?? UserPermission.NONE;
    
    if (Array.isArray(targetPermissions)) {
        return targetPermissions.every(target => (perms & target) === target);
    }

    return (perms & targetPermissions) === targetPermissions;
}
