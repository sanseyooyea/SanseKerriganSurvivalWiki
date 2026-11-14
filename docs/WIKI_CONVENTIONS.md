# Wiki 投稿规范

本文档说明在 KS2 Wiki 创建或编辑页面时，URL 标识（slug）和分类（category）的命名规范。

## Slug（URL 标识）

Slug 是页面在浏览器地址栏中显示的标识，如 `wiki.ks2.top/wiki/rattlesnake-guide`。

### 规则

- 只允许**小写字母** `a-z`、**数字** `0-9` 和**连字符** `-`
- 不能以连字符开头或结尾
- 长度 2–80 个字符
- 不允许空格、大写字母、中文、下划线、特殊符号

### 命名建议

| 类型 | 格式 | 示例 |
|------|------|------|
| 英雄教学 | `{英雄名}-{主题}` | `rattlesnake-guide`、`ascendant-basics` |
| 系统机制 | `{机制名}` | `veterancy-system`、`salvage-mechanics` |
| 通用指南 | `{描述性名称}` | `getting-started`、`markdown-guide` |

### 错误示例

| 错误 | 原因 | 正确写法 |
|------|------|----------|
| `Rattlesnake guide` | 含大写和空格 | `rattlesnake-guide` |
| `WIKI ENTRY  ·  general` | 含大写、空格、特殊字符 | `ascendant-basics` |
| `quick-start`（用于南丁格尔教学） | slug 与内容不符 | `nightingale-guide` |

编辑器会自动将输入转换为合法格式（小写化、空格转连字符、去除非法字符），但仍请注意让 slug **反映页面实际内容**。

---

## Category（分类）

分类用于将文章归类展示。编辑器提供下拉选择，分为两组：

### 英雄教学

英雄教学类文章请选择对应英雄的分类。分类值为英雄英文名的 kebab-case 形式：

| 分类值 | 英雄 |
|--------|------|
| `kerrigan` | 凯瑞甘 |
| `scientist` | 科学家 |
| `dark-templar` | 黑暗圣堂武士 |
| `ascendant` | 晋升者 |
| `spirit` | 灵魂 |
| `ares` | 阿瑞斯 |
| `prophet` | 先知 |
| `stukov` | 斯托科夫 |
| `artanis` | 阿塔尼斯 |
| `zagara` | 扎加拉 |
| `engineer` | 工程师 |
| `team-nova` | 诺娃团队 |
| `nomad` | 游牧民 |
| `dehaka` | 德哈卡 |
| `helios` | 赫利俄斯 |
| `thakras` | 塔克拉斯 |
| `swann` | 斯旺 |
| `warden` | 监管者 |
| `selendis` | 塞兰迪斯 |
| `niadra` | 尼亚德拉 |
| `mira` | 米拉 |
| `scion` | 赛恩 |
| `technician` | 技术员 |
| `warfield` | 沃菲尔德 |
| `champion` | 冠军 |
| `elementalist` | 元素使 |
| `brakk` | 巴拉克 |
| `glevig` | 格里维格 |
| `delta-squad` | 三角洲小队 |
| `phaegore` | 菲戈尔 |
| `alarak` | 阿拉纳克 |
| `izsha` | 伊兹莎 |
| `malus` | 马吕斯 |
| `kraith` | 克雷斯 |
| `energizer` | 激励者 |
| `andor` | 亚顿 |
| `dj` | DJ |
| `rattlesnake` | 响尾蛇 |
| `sgthammer` | 重锤军士 |
| `chew` | 秋伊 |
| `aewyn` | 艾尔文 |
| `critter-lord` | 小动物主宰 |
| `nightingale` | 南丁格尔 |
| `sjlerk` | 斯加拉克 |
| `sophia` | 索菲亚 |
| `jinara` | 吉娜拉 |
| `sir-roachington` | 洛奇顿 |
| `skitter` | 斯基特 |
| `visionary` | 魔法视野化 |
| `junker` | 拾荒者 |
| `horner` | 霍纳（暂时下线） |
| `ghost` | 幽灵（阵亡复活形态） |

> 该列表**不需要手工维护**：前端 `composables/useWikiCategories.ts` 与后端 `server/utils/wiki-categories.ts` 都从 `data/roles.json` 自动生成（排除「随机」），新英雄进 roles 后即可选。上表为 2026-11 的快照。

### 通用分类

| 分类值 | 说明 |
|--------|------|
| `guide` | 通用指南/教程 |
| `system` | 系统机制分析 |
| `governance` | 社区治理/开发者文档 |
| `general` | 其他（默认） |

---

## 标题

- 使用简洁的中文标题
- 不要把分类信息重复写进标题（如不要写「[响尾蛇] 响尾蛇教学」，直接写「响尾蛇教学」）
- 标题应能独立表达文章主题

---

## 提交与审核

- 任何登录用户都可以新建或编辑文章。
- 非管理员点「提交审核」后，内容进入待审队列，**线上页面不会立刻变化**；管理员通过后才发布，署名记为投稿人。
- 投稿的审核状态和管理员备注可在「个人设置 → 我的投稿」查看；被驳回时按备注修改后重新提交即可。
- 每次发布前旧版本都会存入修订历史，可在文章的「历史」页查看。
