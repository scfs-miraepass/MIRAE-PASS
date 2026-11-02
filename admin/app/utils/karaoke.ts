import { KaraokeStatus } from '@/client'

/**
 * 로컬 타임존 기준 오늘 날짜를 "YYYY-MM-DD"로 반환한다.
 * `toISOString()`은 UTC로 변환되어 KST 자정 근처에 하루가 어긋날 수 있어 사용하지 않는다.
 */
export function todayDateString(): string {
    const now = new Date()
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
}

export function karaokeTimeLabel(time: number): string {
    if (time === 8) return '점심시간'
    return `${time}교시`
}

export function karaokeStatusLabel(status?: KaraokeStatus): string {
    switch (status) {
        case KaraokeStatus.IN_PROGRESS:
            return '입찰 진행중'
        case KaraokeStatus.CONFIRMED:
            return '확정'
        case KaraokeStatus.PENDING:
        default:
            return '대기중'
    }
}

export function karaokeStatusColor(status?: KaraokeStatus): 'neutral' | 'warning' | 'success' {
    switch (status) {
        case KaraokeStatus.IN_PROGRESS:
            return 'warning'
        case KaraokeStatus.CONFIRMED:
            return 'success'
        case KaraokeStatus.PENDING:
        default:
            return 'neutral'
    }
}
