import Link from 'next/link'

export const metadata = {
    title: '페이지를 찾을 수 없습니다'
}

export default function NotFound() {
    return (
        <main className="flex min-h-[calc(100vh-var(--nextra-navbar-height,4rem))] flex-col items-center justify-center gap-4 px-6 py-16 text-center">
            <p className="m-0 text-[clamp(4.5rem,15vw,8rem)] leading-none font-extrabold tracking-[-0.04em] text-[hsl(var(--nextra-primary-hue)_var(--nextra-primary-saturation)_var(--nextra-primary-lightness,45%))]">
                404
            </p>
            <h1 className="m-0 text-[1.5rem] font-bold">페이지를 찾을 수 없습니다</h1>
            <p className="m-0 max-w-md leading-[1.7] opacity-70">
                요청하신 페이지가 존재하지 않거나 이동되었을 수 있습니다.
                <br />
                주소를 다시 확인하시거나 아래 링크를 이용해 주세요.
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-3">
                <Link
                    href="/"
                    className="rounded-lg bg-[hsl(var(--nextra-primary-hue)_var(--nextra-primary-saturation)_var(--nextra-primary-lightness,45%))] px-5 py-2.5 font-semibold text-white no-underline"
                >
                    홈으로 돌아가기
                </Link>
                <Link
                    href="/docs"
                    className="rounded-lg border border-current px-5 py-2.5 font-semibold text-inherit no-underline opacity-80"
                >
                    문서 보기
                </Link>
            </div>
        </main>
    )
}
