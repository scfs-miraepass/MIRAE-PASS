import nextra from 'nextra'

const withNextra = nextra({
    latex: true,
    search: {
        codeblocks: false
    },
    defaultShowCopyCode: true,
    contentDirBasePath: '/',

})

// GitHub Pages 프로젝트 사이트는 /<저장소 이름> 아래에서 서비스되므로, 배포 시 하위 경로를 주입합니다.
const basePath = process.env.PAGES_BASE_PATH ?? ''

export default withNextra({
    output: 'export',
    basePath,
    images: {
        unoptimized: true
    },
    reactStrictMode: true,
    agentRules: false
})
