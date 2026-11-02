// manual_version으로 실행한 릴리스를 semantic-release가 만든 것과 같은 형태로 남깁니다.
// 버전 파일과 CHANGELOG.md를 커밋하고 태그와 git note를 푸시해, 다음 semantic-release가 이 버전을 이어받게 합니다.
import { execFileSync } from "node:child_process";
import { appendFileSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import { generateNotes } from "@semantic-release/release-notes-generator";
import semver from "semver";

const version = process.env.MANUAL_VERSION;
const branch = process.env.GITHUB_REF_NAME;
const tag = `v${version}`;

const git = (...args) => execFileSync("git", args, { encoding: "utf8" }).trim();
const setOutput = (created) => {
  if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT, `created=${created}\n`);
};
const fail = (message) => {
  console.error(`[수동 릴리스] ${message}`);
  process.exit(1);
};

const formats = {
  master: /^\d+\.\d+\.\d+$/,
  dev: /^\d+\.\d+\.\d+(-dev\.\d+)?$/,
};
if (!formats[branch]) fail(`master 또는 dev 브랜치에서만 실행할 수 있습니다: ${branch}`);
if (!formats[branch].test(version) || !semver.valid(version)) {
  fail(`${branch} 브랜치에서 사용할 수 없는 버전 형식입니다: ${version}`);
}

// 이미 있는 태그는 그대로 두고 해당 버전의 이미지만 다시 빌드합니다.
if (git("tag", "--list", tag)) {
  console.log(`[수동 릴리스] ${tag} 태그가 이미 있어 이미지만 다시 빌드합니다.`);
  setOutput(false);
  process.exit(0);
}

const lastVersion = git("tag", "--merged", "HEAD", "--list", "v*")
  .split("\n")
  .map((name) => name.slice(1))
  .filter((name) => semver.valid(name))
  .sort(semver.rcompare)[0];
// semantic-release는 가장 높은 버전을 기준으로 삼으므로, 낮은 버전은 태그를 만들어도 이어지지 않습니다.
if (lastVersion && !semver.gt(version, lastVersion)) {
  fail(`${version}은(는) 마지막 릴리스 ${lastVersion}보다 높아야 합니다.`);
}

const lastTag = lastVersion && `v${lastVersion}`;
const commits = git("log", "--format=%H%x00%B%x01", lastTag ? `${lastTag}..HEAD` : "HEAD")
  .split("\x01")
  .map((entry) => entry.trim())
  .filter(Boolean)
  .map((entry) => {
    const [hash, message] = entry.split("\0");
    return { hash, message };
  });

const notes = await generateNotes(
  {},
  {
    cwd: process.cwd(),
    commits,
    lastRelease: lastTag ? { gitTag: lastTag, version: lastVersion } : {},
    nextRelease: { gitTag: tag, version },
    options: { repositoryUrl: git("remote", "get-url", "origin") },
  },
);

const changelog = existsSync("CHANGELOG.md") ? readFileSync("CHANGELOG.md", "utf8") : "";
writeFileSync("CHANGELOG.md", `${notes.trim()}\n\n${changelog}`);
writeFileSync("release-notes.md", notes);

execFileSync("sh", [".github/scripts/bump-version.sh", version], { stdio: "inherit" });

git("add", "CHANGELOG.md", "client/package.json", "admin/package.json", "server/pyproject.toml", "server/uv.lock");
git(
  "-c", "user.name=github-actions[bot]",
  "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
  "commit", "-m", `chore(release): ${version} [skip ci]`,
);
git("tag", tag);

// semantic-release는 사전 릴리스 태그의 채널을 이 note로 판단합니다. note가 없으면 dev 브랜치에서 태그를 무시합니다.
const noteRef = `semantic-release-${tag}`;
const channel = semver.prerelease(version) ? "dev" : null;
git("notes", "--ref", noteRef, "add", "-f", "-m", JSON.stringify({ channels: [channel] }), tag);

// 커밋, 태그, note 중 일부만 올라가는 일이 없도록 한 번에 푸시합니다.
git("push", "--atomic", "origin", `HEAD:refs/heads/${branch}`, `refs/tags/${tag}`, `refs/notes/${noteRef}`);

setOutput(true);
console.log(`[수동 릴리스] ${tag} 릴리스를 만들었습니다.`);
