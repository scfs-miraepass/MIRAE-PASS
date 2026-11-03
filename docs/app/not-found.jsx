import Link from 'next/link'

export const metadata = {
    title: '페이지를 찾을 수 없습니다'
}

const primary = 'hsl(var(--nextra-primary-hue) var(--nextra-primary-saturation) var(--nextra-primary-lightness, 45%))'

const styles = {
    main: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '1rem',
        minHeight: 'calc(100vh - var(--nextra-navbar-height, 4rem))',
        padding: '4rem 1.5rem',
        textAlign: 'center'
    },
    code: {
        margin: 0,
        fontSize: 'clamp(4.5rem, 15vw, 8rem)',
        fontWeight: 800,
        lineHeight: 1,
        letterSpacing: '-0.04em',
        color: primary
    },
    title: {
        margin: 0,
        fontSize: '1.5rem',
        fontWeight: 700
    },
    description: {
        margin: 0,
        maxWidth: '28rem',
        lineHeight: 1.7,
        opacity: 0.7
    },
    actions: {
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'center',
        gap: '0.75rem',
        marginTop: '1rem'
    },
    primaryButton: {
        padding: '0.625rem 1.25rem',
        borderRadius: '0.5rem',
        background: primary,
        color: '#fff',
        fontWeight: 600,
        textDecoration: 'none'
    },
    secondaryButton: {
        padding: '0.625rem 1.25rem',
        borderRadius: '0.5rem',
        border: '1px solid currentColor',
        color: 'inherit',
        fontWeight: 600,
        textDecoration: 'none',
        opacity: 0.8
    }
}

export default function NotFound() {
    return (
        <main style={styles.main}>
            <p style={styles.code}>404</p>
            <h1 style={styles.title}>페이지를 찾을 수 없습니다</h1>
            <p style={styles.description}>
                요청하신 페이지가 존재하지 않거나 이동되었을 수 있습니다.
                <br />
                주소를 다시 확인하시거나 아래 링크를 이용해 주세요.
            </p>
            <div style={styles.actions}>
                <Link href="/" style={styles.primaryButton}>
                    홈으로 돌아가기
                </Link>
                <Link href="/docs" style={styles.secondaryButton}>
                    문서 보기
                </Link>
            </div>
        </main>
    )
}
