// dev의 변경 사항을 master로 보내는 릴리스 PR을 만들거나, 이미 열려 있으면 본문을 갱신합니다.
// 본문에는 커밋 type으로 계산한 예상 버전과 변경 목록을 적습니다. 실제 버전은 머지 후 semantic-release가 정합니다.
// DRY_RUN=1이면 PR을 만들지 않고 제목과 본문만 출력합니다.
import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";

const base = process.env.BASE_BRANCH ?? "master";
const head = process.env.HEAD_BRANCH ?? "dev";
const dryRun = process.env.DRY_RUN === "1";

const run = (command, args) => execFileSync(command, args, { encoding: "utf8" }).trim();
const git = (...args) => run("git", args);

// 정식 버전 태그(vX.Y.Z) 중 가장 높은 버전을 마지막 릴리스로 봅니다.
const parse = (version) => version.split(".").map(Number);
const compare = (a, b) => {
  const [x, y] = [parse(a), parse(b)];
  return x[0] - y[0] || x[1] - y[1] || x[2] - y[2];
};
const lastVersion =
  git("tag", "--merged", `origin/${base}`, "--list", "v*")
    .split("\n")
    .filter((tag) => /^v\d+\.\d+\.\d+$/.test(tag))
    .map((tag) => tag.slice(1))
    .sort(compare)
    .at(-1) ?? "0.0.0";

// 릴리스 커밋과 merge 커밋은 변경 목록에서 뺍니다.
const commits = git("log", "--no-merges", "--format=%h%x00%s%x00%b%x01", `origin/${base}..origin/${head}`)
  .split("\x01")
  .map((entry) => entry.trim())
  .filter(Boolean)
  .map((entry) => {
    const [hash, subject, body] = entry.split("\0");
    return { hash, subject, body: body ?? "" };
  })
  .filter(({ subject }) => !subject.startsWith("chore(release):"));

if (commits.length === 0) {
  console.log(`[릴리스 PR] ${head}에 ${base}로 보낼 변경 사항이 없습니다.`);
  process.exit(0);
}

const typeOf = ({ subject }) => subject.match(/^(\w+)(\([^)]*\))?(!)?:/);
const isBreaking = (commit) => typeOf(commit)?.[3] === "!" || /^BREAKING[ -]CHANGE:/m.test(commit.body);
const groups = { breaking: [], feat: [], fix: [], other: [] };
for (const commit of commits) {
  const type = typeOf(commit)?.[1];
  if (isBreaking(commit)) groups.breaking.push(commit);
  else if (type === "feat") groups.feat.push(commit);
  else if (type === "fix" || type === "perf") groups.fix.push(commit);
  else groups.other.push(commit);
}

const [major, minor, patch] = parse(lastVersion);
let nextVersion = null;
if (groups.breaking.length) nextVersion = `${major + 1}.0.0`;
else if (groups.feat.length) nextVersion = `${major}.${minor + 1}.0`;
else if (groups.fix.length) nextVersion = `${major}.${minor}.${patch + 1}`;

const list = (items) => items.map(({ hash, subject }) => `- ${subject} (${hash})`).join("\n");
const section = (title, items) => (items.length ? `### ${title}\n${list(items)}\n` : "");

// 제목은 Conventional Commits 형식이 아니어야 합니다. merge 커밋 메시지로 쓰여 semantic-release가 읽기 때문입니다.
const title = nextVersion ? `v${nextVersion} 릴리스` : `${head} 변경 사항 반영 (릴리스 없음)`;
const body = `<!-- 이 본문은 Release PR 워크플로가 자동으로 작성합니다. 다시 실행하면 덮어씁니다. -->

## 릴리스 요약

| 항목 | 내용 |
| --- | --- |
| 현재 버전 | \`${lastVersion}\` |
| 예상 다음 버전 | ${nextVersion ? `\`${nextVersion}\`` : "없음 (버전이 바뀌는 커밋이 없습니다)"} |
| 포함된 커밋 | ${commits.length}개 |

예상 버전은 커밋 type으로 계산한 값입니다. 실제 버전은 머지 후 semantic-release가 정합니다.

## 변경 사항

${[
  section("호환성이 깨지는 변경 (Major)", groups.breaking),
  section("새 기능 (Minor)", groups.feat),
  section("버그 수정 (Patch)", groups.fix),
  section("그 밖의 변경 (버전 변화 없음)", groups.other),
]
  .filter(Boolean)
  .join("\n")}
## 머지 방법

- **Create a merge commit**으로 머지합니다. Squash나 Rebase로 머지하면 커밋 type이 사라지거나 dev 자동 동기화가 실패합니다.
- 머지하면 정식 릴리스와 Docker 이미지 배포가 진행되고, 끝나면 dev가 자동으로 master와 맞춰집니다.

자세한 내용은 [배포 문서](https://docs.miraepass.xyz/docs/development/deploy)를 참고하세요.
`;

if (dryRun) {
  console.log(`# ${title}\n\n${body}`);
  process.exit(0);
}

const bodyFile = "release-pr-body.md";
writeFileSync(bodyFile, body);

const existing = run("gh", ["pr", "list", "--base", base, "--head", head, "--state", "open", "--json", "number", "--jq", ".[0].number"]);
if (existing) {
  run("gh", ["pr", "edit", existing, "--title", title, "--body-file", bodyFile]);
  console.log(`[릴리스 PR] 열려 있는 #${existing}의 제목과 본문을 갱신했습니다.`);
} else {
  const url = run("gh", ["pr", "create", "--base", base, "--head", head, "--title", title, "--body-file", bodyFile]);
  console.log(`[릴리스 PR] 릴리스 PR을 만들었습니다: ${url}`);
}
