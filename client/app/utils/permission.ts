import { UserPermission as _UserPermission } from '@/client'

/*

사용 예시:

import { UserPermission } from '@/client'

// 1. 기존 방식과 동일 (모두 만족해야 함 - 암시적 AND)
const permissions = [ UserPermission._GRANT_POINT, UserPermission._MANAGE_USERS ]

// 2. OR 조건 (하나라도 만족하면 됨)
const permissions = { or: [ UserPermission._GRANT_POINT, UserPermission._MANAGE_USERS ] }

// 3. AND 조건 (명시적)
const permissions = { and: [ UserPermission._GRANT_POINT, UserPermission._MANAGE_USERS ] }

// 4. AND와 OR를 섞은 복합 조건
// (포인트 권한이 있으면서, 유저 관리 또는 시스템 설정 권한 중 하나를 가진 경우)
const permissions = {
    and: [
        UserPermission._GRANT_POINT,
        { or: [ UserPermission._MANAGE_USERS, UserPermission._SYSTEM_SETTINGS ] }
    ]
}

hasPermission(UserPermission, permissions)

 */

export const UserPermission = _UserPermission

export type PermissionCondition = 
    | _UserPermission
    | number 
    | { and: PermissionCondition[] } 
    | { or: PermissionCondition[] }
    | PermissionCondition[];

export function hasPermission(
    userPermissions: _UserPermission | number | undefined | null,
    targetPermissions: PermissionCondition | undefined | null
): boolean {
    const perms = (userPermissions ?? UserPermission.NONE) as number;
    
    if (targetPermissions === undefined || targetPermissions === null) {
        return true;
    }

    function evaluate(condition: PermissionCondition): boolean {
        if (Array.isArray(condition)) {
            if (condition.length === 0) return true;
            return condition.every(c => evaluate(c));
        }

        if (typeof condition === 'object' && condition !== null) {
            if ('and' in condition) {
                if (condition.and.length === 0) return true;
                return condition.and.every(c => evaluate(c));
            }
            
            if ('or' in condition) {
                if (condition.or.length === 0) return true;
                return condition.or.some(c => evaluate(c));
            }
        }

        // Base case: primitive number or enum
        return (perms & (condition as number)) === (condition as number);
    }

    return evaluate(targetPermissions);
}
