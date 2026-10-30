---
name: sync-upstream
description: >-
  Opens a dp-router pull request that merges QuantumNous/new-api main into our
  main by running the sync_upstream.py script. Ledger paths keep our overlapping
  lines. Every other overlapping line follows upstream. Lockfiles and locale
  files are regenerated instead of line-merged. Use when the user invokes
  sync-upstream, or asks to update, pull, or merge upstream new-api into
  dp-router (更新上游, 合并上游, 同步 QuantumNous/new-api). Also use when they
  ask to record a new focus change in this skill. Do not use for ordinary
  feature work that does not mention upstream sync or this ledger.
disable-model-invocation: true
---

# 同步上游 new-api

在 `dp-router` 仓库根目录执行脚本。不要自己拼 `git merge`，不要 `git checkout --ours` 整文件，不要加 `--skip-build`，不要在脚本失败后换一种合并方式再试。脚本使用已经配置好的 git 身份，不会改 git config。

```bash
python3 .agents/skills/sync-upstream/scripts/sync_upstream.py
```

脚本把规则定死在一处。台账路径见脚本里的 `LEDGER_PREFIXES`。要保住新的长期行为，把路径加进这个元组，并在 `assert_ledger` 里加一条对应检查，同时补测试。

退出码：

- `0`：同步分支上已经有一次合并提交。标准输出有 `BRANCH=` 和 `REPORT=`。只推送这个分支名：`git push -u origin` 后面跟 `BRANCH` 的值。用 `gh pr create --repo deeppatternai/dp-router --base main --head` 这个分支名开 PR。正文贴上 `REPORT` 文件，并写上「请用 merge commit 合并，不要 squash 或 rebase」。不要改仓库设置，不要自己合并 PR。`--ledger-only` 成功时只输出 `BRANCH=`。
- `2`：`origin/main` 已经包含上游。不要开 PR。
- `3`：还有脚本不能安全处理的冲突。不要猜，把脚本输出交给用户。不要提交。合并如果已经开始，就留在进行中。
- `1`：预检、台账或构建失败。不要推送，不要提交。合并如果已经开始，就留在进行中，不要清空已经暂存的结果。

只记台账时，先改 `LEDGER_PREFIXES`、`assert_ledger` 和本说明，再执行：

```bash
python3 .agents/skills/sync-upstream/scripts/sync_upstream.py --ledger-only
```

脚本会从 `origin/main` 建 `docs/sync-ledger-日期`，并且只提交 `.agents/skills/sync-upstream/` 里的改动。然后推送它打印的 `BRANCH`，向 `deeppatternai/dp-router` 开 PR。不要把这些改动留在 `main`。

策略只有这一套：

- 台账文件里双方都改过的等长行留下我们这一侧，上游那一侧写入报告。只有一侧改过的行仍然保留。两边不等长的替换如果在基线上范围重叠，整段只输出一次，留下我们这一侧。多行删除也算这种替换。只有一侧的替换还能按行对上基线时，对得上的行仍按行合并，对不上的新行保留。
- 其他文本文件里双方都改过的等长行留下上游那一侧。只有一侧改过的行仍然保留。两边不等长的替换如果在基线上范围重叠，整段只输出一次，留下上游那一侧。范围只相邻、不重叠的替换两边都留。同一位置双方各自插入的内容都保留，先上游，后我们；一侧的插入是另一侧的完整前缀时只留较长的那一段，否则两段都完整保留。双方无换行的文末插入、复用或移动了被对方修改的唯一基线行，都停在退出码 3。插在删除范围边界的行保留；严格插在整段删除内部的行停在退出码 3，不生成孤儿行。
- `web/src/i18n/locales/*.json` 按 key 做三方合并：只有一侧改过的 key 跟随那一侧，双方都改过的 key 用我们的文案。
- `go.sum` 和 `web/bun.lock` 不手改。清单处理完后由 `go mod tidy` 或 `bun install` 重写。tidy 可以删掉合并后没有引用的 require，删掉的模块写入报告。`pins.txt` 里已经进入合并清单的模块，tidy 之后必须还在，版本也必须仍是钉住的版本，否则停。
- `go.mod` 只要两边原文不同，就在处理其他冲突之前按两边父提交重做，不沿用 Git 自动合并的结果。单行 `require` 和 `require` 块都认，比较「require 以外」时两种写法同等抹掉。`module`、`go`、`toolchain` 等 require 以外的行不一致时停。`require` 先取并集，版本用上游，除非 `scripts/pins.txt` 钉住。注释行不会当成模块。人工解决 require 以外差异后恢复，脚本接受已暂存结果并写入报告。
- 除语言包以外的 JSON、YAML、TOML 出现冲突就停。
- 上游删了台账文件就保留，包括没有形成冲突、直接删掉的情况。删除台账路径同时新增文件时视为可能改名，第一次停在退出码 3 并写入报告；人工确认后恢复会接受改名，不再循环停止。上游删了别的文件就接受删除。我们删了、上游又改了的非台账文件取上游。非普通文件冲突不做文本写入。
- 新开的合并先清空报告。处理中途失败时，已经记下的丢弃内容留在报告里。恢复时接着写，不用「no conflict hunks」覆盖已有记录。一次没有冲突的新合并才写「no conflict hunks」。
- 冲突标记清掉、台账检查通过、点名的测试各自出现一次顶层 `--- PASS:`（名字里带 `/` 的子测试不算）、并且 `go build ./...` 通过之后，脚本才做一次合并提交。
