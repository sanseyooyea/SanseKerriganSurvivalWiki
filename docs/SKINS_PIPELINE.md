# 皮肤模型管线（m3 → GLB → 前端 3D 预览）

`/skins` 页面的模型不是手绘的，全部从地图数据解析后在离线环境里转成 GLB，再作为静态资源随站点发布。本文件记录完整链路与踩过的坑。

## 为什么皮肤有多部件

`Shop.xml` 里一个 `CSkin` 除了 `DisplayModel`（本体）之外，还有多条：

```xml
<ReplacementArray Catalog="Model" From="Marine" To="MengskMarine"/>
```

意思是「这个皮肤把陆战队员的模型也换掉」。所以一个商店皮肤往往同时替换本体、兵种、建筑与死亡特效——例如 DOM 科学家有 23 个部件，全息游牧 17 个，原始塔克拉兹 17 个。

当前覆盖：**27 个 CSkin / 109 个部件**。

## 数据链路

```
SC2Map (Shop.xml)
   └─ build_skin_index.py   → skins_index.json    CSkin → 替换表 → CModel → .m3 路径
        └─ build_skin_manifest.py → skins_manifest.json  按 role 分组，带 from 字段
             ├─ batch_pull_models.py  → models/*.m3       CASC / 地图 MPQ 拉取
             ├─ batch_dump_tex.py / batch_extract_tex.py / batch_convert_tex.py → textures_all_png/
             └─ batch_export_glb.py   → glb_all/*.glb     Blender headless (m3studio)
                  └─ link_manifest_glb.py → 补 glb 字段，m3 路径扁平化为 a__b__c.glb
                       └─ optimize_glb.py  → RGBA→RGB / 最大边 1024 / JPEG q90
                            └─ Wiki: data/skins.json + public/skins/models/
                                 └─ scripts/enrich_skins.py  补 hero / unitId 跳转
```

原始工具链在仓库外的 `D:/starcraft2/m3render/`（依赖 Blender 4.5.9 + m3studio 插件 + CascLib）。

## 关键实现细节

### 模板路径必须就地展开

`CModel` 的模型路径里可能有 SC2 运行时占位符：

```
Assets/##Prefix####Race##/##id##/##id##.m3
```

`##Prefix##` → `Units`，`##Race##` 取单位 Race 属性（`Zerg` / `Terran` / `Protoss`），`##id##` 是模型 id。不能直接丢弃整条路径，必须替换后使用。

### 角色判定要先统一斜杠

CASC 返回的路径是**反斜杠**，而地图 MPQ 里是正斜杠。`role_of()` 必须先 `m3.replace('\\','/').lower()`，否则兵种和建筑会被全部误判成 `other`。

角色规则：

| role | 判定 |
|---|---|
| `death` | 文件名含 `death` |
| `building` | 路径含 `/buildings/` |
| `unit` | 路径含 `/units/` 或 `/coop/`，或含 `storymode` |
| `other` | 其余 |

`body` 单独来自 `DisplayModel`，不参与上面的判定。

### DisplayModel 为空的皮肤

少数皮肤只替换死亡特效或兵种，本体沿用英雄默认模型（`DisplayModel` 为空）。`build_skin_manifest.py` 里的 `BODY_OVERRIDE` 手工补本体，否则查看器里该皮肤一个可加载模型都没有。目前只有虚空纳鲁德需要：

```python
BODY_OVERRIDE = {
    'ShopAscendantNarud': ('AscendantNarudVoidAscendant',
                           'Assets/CustomModels/Ascendant_Void_Narud.m3'),
}
```

### 纯自发光材质要退回 emis1

广告屏、灯带这类材质**没有 `layer_diff`**，只有 `layer_emis1`。导出时如果只找 diffuse，Principled BSDF 会退化成灰色，渲染出一块死白。导出脚本按 `layer_diff` → `layer_emis1` 顺序回退。

### .ogv 视频贴图要抽首帧

部分广告贴图是 Theora 视频（`.ogv`），无法直接静态导出。先用 Blender 的 image loader 把第一帧存成同名 PNG（`extract_ogv_frames.py`），导出脚本按「同名换 .png」自动找到它。

### GLB 压缩的安全前提

把所有贴图从 RGBA 转成 RGB 前，必须确认**所有材质的 `alphaMode` 都是 `OPAQUE`**，否则会丢掉透明效果。`scan_alpha.py` 负责这个检查，当前 106 个文件全部 OPAQUE。

压缩效果：107 MB → 45 MB（最大边 1024、JPEG q90）。

## Wiki 侧

- `data/skins.json`：页面直接 import 的数据文件，含 `hero`（`{name, nameZh, roleId}`）与每个部件的 `unitId`。
- `scripts/enrich_skins.py`：补这两类跳转字段。英雄判定优先看本体部件的 `from`，再退回皮肤 id 里的英雄名；部件优先精确 id，其次「以 `from` 结尾且属于该英雄」的最短 id。`death` / `other` 不挂兵种链接。
- `public/skins/models/*.glb`：106 个模型，约 45 MB。

## 前端

- 页面 `pages/skins/index.vue`，`three` 通过 npm 打包（CSP 不允许 CDN 脚本）。
- three.js 在 `onMounted` 内动态 `import()`，避免 SSR 阶段触碰 WebGL。
- URL 状态：`?skin=<CSkin id>&part=<glb 文件名>`，可直接分享到具体部件。
- 曝光补偿：把贴图降采样到 32×32 估算平均亮度，按 `clamp(pow(0.42/luma, 0.75), 0.7, 3.2)` 调整 `toneMappingExposure`，深色模型才不会糊成一团。

### ⚠️ CSP：两个指令都要放行 blob:

`nuxt.config.ts` 的 CSP 里，`img-src` 与 `connect-src` **都必须包含 `blob:`**。

原因：`GLTFLoader` 对 GLB 内嵌贴图的处理是

```js
const blob = new Blob([bufferView], { type: sourceDef.mimeType });
sourceURI = URL.createObjectURL(blob);   // 然后交给 ImageBitmapLoader
```

`ImageBitmapLoader` 通过 `fetch()` 读取这个 blob URL，而 **`fetch` 受 `connect-src` 约束，不受 `img-src` 约束**。只在 `img-src` 加 `blob:` 时，模型会渲染成无贴图白模，且网格正常显示、控制台只有 CSP 报错。

本地 `serve.py` 不发送 CSP 头，所以这个问题**只在线上暴露**——排查时先看是否线上线下表现不一致。

## 地图更新后怎么重跑

1. 重新解包地图 XML，更新 `_mpqxml/`。
2. `python build_skin_index.py` → `python build_skin_manifest.py` → `python link_manifest_glb.py`
3. 新出现的 m3：`python batch_pull_models.py` → 贴图三步 → `python batch_export_glb.py`
4. `python scan_alpha.py` 确认全部 OPAQUE → `python optimize_glb.py web/models/*.glb`
5. 复制 `web/skins_manifest.json` 到 wiki 的 `data/skins.json`，模型到 `public/skins/models/`
6. `python scripts/enrich_skins.py`（wiki 仓库内）
7. `npm run build` 验证
