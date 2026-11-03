import nextra from 'nextra'

const withNextra = nextra({
    latex: true,
    search: {
        codeblocks: false
    },
    defaultShowCopyCode: true,
    contentDirBasePath: '/',

})

export default withNextra({
    reactStrictMode: true,
    agentRules: false
})