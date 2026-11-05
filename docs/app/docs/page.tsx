import { redirect } from 'next/navigation'

// 정적 export에서는 next.config의 redirects를 쓸 수 없어 페이지에서 리다이렉트합니다.
export default function DocsIndex() {
    redirect('/docs/getting-started/introduction')
}
