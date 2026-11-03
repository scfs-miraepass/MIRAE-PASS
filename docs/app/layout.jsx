import { Footer, LastUpdated, Layout, Navbar } from 'nextra-theme-docs'
import { Head, Search } from 'nextra/components'
import { getPageMap } from 'nextra/page-map'
import 'nextra-theme-docs/style.css'

const REPOSITORY_URL = 'https://github.com/scfs-miraepass/MIRAE-PASS'

export const metadata = {
    title: {
        template: '%s | MIRAEPASS Docs',
        default: 'MIRAEPASS Docs'
    },
    description: '순천미래과학고등학교 교내 포인트 시스템 MIRAEPASS 문서'
}

const navbar = (
    <Navbar
        logo={<b>MIRAEPASS</b>}
        projectLink={REPOSITORY_URL}
    />
)
const footer = <Footer>Apache-2.0 {new Date().getFullYear()} © 임영재(rldn12134@rldn.xyz), 위임 순천미래과학고등학교(MIRAEPASS)</Footer>

export default async function RootLayout({ children }) {
    return (
        <html
            lang="ko"
            dir="ltr"
            // next-themes 권장 설정
            suppressHydrationWarning
        >
        <Head />
        <body>
        <Layout
            navbar={navbar}
            footer={footer}
            pageMap={await getPageMap()}
            docsRepositoryBase={`${REPOSITORY_URL}/tree/master/docs`}
            copyPageButton={false}
            editLink="이 페이지 수정하기"
            feedback={{ content: '질문이 있으신가요? 피드백 남기기' }}
            lastUpdated={<LastUpdated locale="ko">마지막 수정</LastUpdated>}
            search={
                <Search
                    placeholder="문서 검색"
                    emptyResult="검색 결과가 없습니다."
                    errorText="검색 인덱스를 불러오지 못했습니다."
                    loading="불러오는 중…"
                />
            }
            themeSwitch={{ dark: '다크', light: '라이트', system: '시스템' }}
            toc={{ title: '목차', backToTop: '맨 위로' }}
        >
            {children}
        </Layout>
        </body>
        </html>
    )
}
