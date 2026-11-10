# 多端同步（Supabase）

## 同步什么（用户明确要求，别擅自扩大）

| kind | item | 内容 |
|---|---|---|
| `w` | 单词 | 划线，每词独立，最新时间戳为准（LWW）；取消划线写 `v:0` |
| `mark` | 旧序号 | 旧版设备写的划线，经 `LEGACY_V1` 翻译（见下） |
| `rev` | 单词 | 复习记录：`v` = 通过次数（`-1` = 没记住被清零、仍到期），`t` = 上次复习时间；整条按 `t` 取最新（LWW），见 [review.md](review.md) |
| `color` | 去掉 `#` 的色号 | 自定义色号，取并集 |
| `time` | `设备id\|YYYY-MM-DD` | 学习时长：`t` 列存这台设备当天的毫秒数（不是时间戳）；各设备各写各的，本机取 max 只增不减 |
| `rtime` | `设备id\|YYYY-MM-DD` | 其中复习词表上的那部分，规则同 `time`（`time` 仍是总数），见 [stats.md](stats.md) |
| `rlog` | `单词\|YYYY-MM-DD` | 复习里哪天划掉了哪个词（统计用），`v:1` 划掉 / `v:0` 取消，LWW |
| `tlog` / `tev` | 见 [stats.md](stats.md#计时诊断排查记少了用) | 计时诊断，开关开着才传 |

其余设置一概不同步，包括当前背景色、状态池。

## 机制

- 纯 REST（fetch），不引 SDK。localStorage 是本地事实源，联网时与云端双向合并（`reconcile()`）。
- 触发：打开、定时轮询、重新聚焦、本地改动后防抖。
- **拉取必须分页**：PostgREST 的 `db-max-rows` 会静默截断。`pullAll()` 按实际返回行数翻页直到空页，不写死页大小。别退回单次 GET。
- 换同步码时清空 `studyOthers`。

## 云端表与函数（已在 Supabase SQL Editor 建好）

```sql
create table public.progress (
  code text, kind text, item text,
  v smallint default 1, t bigint default 0,
  primary key (code, kind, item));
alter table public.progress enable row level security;   -- 不建 policy、不给 anon 表权限

create or replace function public.sync_pull(p_code text, p_offset int default 0)
returns setof public.progress
language sql stable security definer set search_path = public as $$
  select * from public.progress where code = p_code
  order by kind, item offset p_offset limit 1000;
$$;
create or replace function public.sync_push(p_code text, p_rows jsonb)
returns void
language sql security definer set search_path = public as $$
  insert into public.progress (code, kind, item, v, t)
  select p_code, r->>'kind', r->>'item', (r->>'v')::smallint, (r->>'t')::bigint
  from jsonb_array_elements(p_rows) r
  on conflict (code, kind, item) do update set v = excluded.v, t = excluded.t;
$$;
grant execute on function public.sync_pull(text, int) to anon;
grant execute on function public.sync_push(text, jsonb) to anon;
```

客户端只调 `POST /rest/v1/rpc/sync_pull` 和 `rpc/sync_push`。两个函数不看 kind，加新 kind 不用改库。不直接读写表，是因为那样拿公开 key 就能列出所有人的同步码。

## 安全

- 客户端只用 publishable key（`web/supabase-config.json`，本来就公开）。**`sb_secret_...` 绝不能进客户端**；它曾在对话里出现过，应在 Supabase 轮换作废。
- 安全只靠「不知道同步码就碰不到数据」，所以同步码要不好猜。没有账号鉴权。

## 身份键：按单词，不按序号

划线和自测解锁按**单词**存，词表重排、换六级都不会对错词。

- `web/legacy_rank_v1.json`：最初那份词表的 `rank → 单词`，旧数据只通过它翻译。**这个文件永远不许改。**
- 本地迁移（`keysV` 1→2，启动时一次）：先把原始存档另存到 `cet4_reader_v3_backup_rankkeys`（只写一次），再把 `marks` / `revealed` 的键换成单词。`poolMax`、`list`、`anchor` 表示当前词表里的位置，有意不动。
- 云端双轨：读 `w` 和 `mark` 两种行、按单词合并；本地较新时**两种都写**，让还没升级的旧版设备照常互通。所有设备升级后可删掉写 `kind:"mark"` 的那一行，读旧行的逻辑建议保留。
