<template>
  <div>
    <header class="mb-5">
      <h1 class="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">皮肤模型预览</h1>
      <p class="mt-1.5 max-w-3xl text-sm leading-relaxed text-gray-500 dark:text-gray-400">
        商店皮肤不只是换本体：多数皮肤同时替换兵种模型与建筑外观。
        选择皮肤后可在左侧按「本体 / 兵种 / 建筑 / 死亡特效」逐项查看，共 {{ totalSkins }} 个皮肤、{{ totalParts }} 个模型。
      </p>
    </header>

    <section class="wiki-card p-0 overflow-hidden">
      <div class="flex flex-col lg:flex-row">
        <!-- 左侧选择区 -->
        <aside class="lg:w-72 shrink-0 border-b lg:border-b-0 lg:border-r border-surface-200 dark:border-gray-700
                      flex flex-col max-h-[70vh] lg:max-h-[640px]">
          <div class="p-3 border-b border-surface-200 dark:border-gray-700">
            <label class="block text-[0.65rem] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1.5">皮肤</label>
            <select
              v-model="currentSkinId"
              class="w-full rounded-md border border-surface-200 bg-transparent px-2.5 py-1.5 text-sm
                     focus:border-survivor-400 focus:outline-none focus:ring-2 focus:ring-survivor-500/20
                     dark:border-gray-700 dark:bg-gray-900"
            >
              <option v-for="s in skinList" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </div>

          <div class="flex-1 overflow-y-auto p-2">
            <template v-for="g in groupedParts" :key="g.role">
              <div class="px-2 mt-3 mb-1 text-[0.65rem] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                {{ ROLE_LABEL[g.role] }} ({{ g.items.length }})
              </div>
              <button
                v-for="c in g.items"
                :key="c.glb"
                type="button"
                class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-left text-sm transition-colors"
                :class="c.glb === currentGlb
                  ? 'bg-survivor-50 text-survivor-700 dark:bg-survivor-900/40 dark:text-survivor-300 font-medium'
                  : 'text-gray-600 dark:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-800'"
                @click="loadModel(c)"
              >
                <span class="truncate">{{ c.label }}</span>
              </button>
            </template>
            <p v-if="!groupedParts.length" class="px-2 py-6 text-xs text-gray-400">该皮肤没有可展示的模型</p>
          </div>

          <div class="p-3 border-t border-surface-200 dark:border-gray-700 text-[0.7rem] leading-relaxed text-gray-400 dark:text-gray-500">
            <template v-if="stats">
              {{ stats.meshes }} 网格 · {{ fmt(stats.verts) }} 顶点 · {{ fmt(stats.tris) }} 三角<br>
              {{ stats.mats }} 材质 · {{ stats.texs }} 贴图
            </template>
            <template v-else>—</template>
          </div>
        </aside>

        <!-- 3D 视口 -->
        <div class="relative flex-1 min-h-[420px] lg:min-h-[640px] bg-[#0b0d12]">
          <div ref="viewerEl" class="absolute inset-0" />

          <div class="absolute top-3 right-3 flex gap-1.5">
            <button type="button" class="viewer-btn" :class="{ on: autoRotate }" @click="toggleRotate">自动旋转</button>
            <button type="button" class="viewer-btn" :class="{ on: wireframe }" @click="toggleWire">线框</button>
            <button type="button" class="viewer-btn" @click="resetView">复位</button>
          </div>

          <div v-if="loading" class="absolute inset-0 grid place-content-center gap-3 bg-[#0b0d12]">
            <div class="mx-auto h-8 w-8 rounded-full border-[3px] border-gray-700 border-t-survivor-400 animate-spin" />
            <p class="text-xs text-gray-400">{{ loadingText }}</p>
          </div>

          <p v-if="error" class="absolute left-3 bottom-3 right-3 text-xs text-red-400">{{ error }}</p>
          <p class="absolute right-3 bottom-3 text-[0.65rem] text-gray-500 pointer-events-none">
            拖拽旋转 · 滚轮缩放 · 右键平移
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import skinsData from '~/data/skins.json'

type Part = { role: string; label: string; model: string | null; m3: string; glb: string }
type Skin = { id: string; name: string; components: Part[]; counts: Record<string, number> }

const ROLE_LABEL: Record<string, string> = {
  body: '本体',
  unit: '兵种',
  building: '建筑',
  death: '死亡特效',
  other: '其他部件',
}
const ROLE_ORDER = ['body', 'unit', 'building', 'other', 'death']

const skins = (skinsData as any).skins as Record<string, Skin>
const skinList = Object.keys(skins)
  .map(id => skins[id])
  .sort((a, b) => a.name.localeCompare(b.name, 'zh'))

const totalSkins = skinList.length
const totalParts = skinList.reduce((n, s) => n + s.components.filter(c => c.glb).length, 0)

useHead({ title: '皮肤模型预览 - 凯瑞甘生存2 Wiki' })

const currentSkinId = ref(skinList[0]?.id ?? '')
const currentGlb = ref('')
const loading = ref(true)
const loadingText = ref('加载中…')
const error = ref('')
const autoRotate = ref(true)
const wireframe = ref(false)
const stats = ref<{ meshes: number; verts: number; tris: number; mats: number; texs: number } | null>(null)

const viewerEl = ref<HTMLElement | null>(null)

const currentSkin = computed(() => skins[currentSkinId.value])

const groupedParts = computed(() => {
  const skin = currentSkin.value
  if (!skin) return []
  const groups: Record<string, Part[]> = {}
  for (const c of skin.components) {
    if (!c.glb) continue
    ;(groups[c.role] = groups[c.role] || []).push(c)
  }
  return ROLE_ORDER.filter(r => groups[r]).map(role => ({ role, items: groups[role] }))
})

function fmt(n: number) {
  return Math.round(n).toLocaleString('zh-CN')
}

// ---- three.js 运行时（仅客户端） ----
let THREE: any = null
let renderer: any = null
let scene: any = null
let camera: any = null
let controls: any = null
let root: any = null
let grid: any = null

async function initViewer() {
  if (!viewerEl.value || renderer) return
  const three = await import('three')
  const { OrbitControls } = await import('three/addons/controls/OrbitControls.js')
  const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js')
  THREE = three

  const el = viewerEl.value
  renderer = new three.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(el.clientWidth, el.clientHeight)
  renderer.outputColorSpace = three.SRGBColorSpace
  renderer.toneMapping = three.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1
  el.appendChild(renderer.domElement)

  scene = new three.Scene()
  scene.background = new three.Color(0x0b0d12)

  camera = new three.PerspectiveCamera(38, el.clientWidth / el.clientHeight, 0.01, 4000)
  camera.position.set(3.2, 2, 4.2)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.075
  controls.autoRotate = autoRotate.value
  controls.autoRotateSpeed = 1.4

  const key = new three.DirectionalLight(0xffffff, 2.4)
  key.position.set(4, 6, 5)
  scene.add(key)
  const fillLight = new three.DirectionalLight(0xbcd0ff, 0.9)
  fillLight.position.set(-5, 1.5, 3)
  scene.add(fillLight)
  const rim = new three.DirectionalLight(0x9ab4ff, 1.6)
  rim.position.set(-2, 3.5, -6)
  scene.add(rim)
  scene.add(new three.AmbientLight(0xffffff, 0.35))

  grid = new three.GridHelper(12, 24, 0x2a3346, 0x171d29)
  grid.material.transparent = true
  grid.material.opacity = 0.5
  scene.add(grid)

  const loader = new GLTFLoader()
  ;(window as any).__ks2Loader = loader

  const tick = () => {
    controls.update()
    renderer.render(scene, camera)
    requestAnimationFrame(tick)
  }
  tick()

  window.addEventListener('resize', resize)
  loading.value = false
}

function resize() {
  const el = viewerEl.value
  if (!el || !renderer || !camera) return
  renderer.setSize(el.clientWidth, el.clientHeight)
  camera.aspect = el.clientWidth / el.clientHeight
  camera.updateProjectionMatrix()
}

function disposeRoot() {
  if (!root || !scene) return
  scene.remove(root)
  root.traverse((o: any) => {
    if (o.geometry) o.geometry.dispose()
    if (o.material) {
      const mats = Array.isArray(o.material) ? o.material : [o.material]
      for (const m of mats) {
        for (const k of Object.keys(m)) {
          const v = m[k]
          if (v && v.isTexture) v.dispose()
        }
        m.dispose()
      }
    }
  })
  root = null
}

function frameObject(obj: any) {
  const box = new THREE.Box3().setFromObject(obj)
  const size = box.getSize(new THREE.Vector3())
  const center = box.getCenter(new THREE.Vector3())
  const radius = Math.max(size.x, size.y, size.z) * 0.5 || 1

  obj.position.x -= center.x
  obj.position.z -= center.z
  obj.position.y -= box.min.y

  const dist = radius / Math.tan(THREE.MathUtils.degToRad(camera.fov * 0.5)) * 1.35
  camera.position.set(dist * 0.72, radius * 0.95, dist * 0.82)
  camera.near = Math.max(radius / 500, 0.001)
  camera.far = radius * 200
  camera.updateProjectionMatrix()

  controls.target.set(0, radius * 0.55, 0)
  controls.minDistance = radius * 0.6
  controls.maxDistance = radius * 25
  controls.update()

  grid.position.y = 0
  grid.scale.setScalar(Math.max(radius / 3, 0.5))
}

/** 用 32×32 降采样估算贴图平均亮度，据此调曝光，避免深色模型糊成一团。 */
function textureMeanLuma(tex: any): number | null {
  const img = tex && tex.image
  if (!img) return null
  const c = document.createElement('canvas')
  c.width = c.height = 32
  const ctx = c.getContext('2d', { willReadFrequently: true })
  if (!ctx) return null
  try { ctx.drawImage(img, 0, 0, 32, 32) } catch { return null }
  let d: Uint8ClampedArray
  try { d = ctx.getImageData(0, 0, 32, 32).data } catch { return null }
  let s = 0, n = 0
  for (let i = 0; i < d.length; i += 4) {
    s += 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2]
    n++
  }
  return n ? (s / n) / 255 : null
}

function loadModel(c: Part) {
  if (!c || !c.glb) return
  const loader = (window as any).__ks2Loader
  if (!loader) return

  currentGlb.value = c.glb
  loading.value = true
  loadingText.value = '加载 ' + c.label + ' …'
  error.value = ''
  disposeRoot()

  loader.load('/skins/models/' + c.glb, (gltf: any) => {
    root = gltf.scene
    let meshes = 0, verts = 0, tris = 0, mats = 0, texs = 0
    const seenMat = new Set<string>(), seenTex = new Set<any>()
    const texList: any[] = []

    root.traverse((o: any) => {
      if (!o.isMesh) return
      meshes++
      const g = o.geometry
      if (g) {
        verts += g.attributes.position ? g.attributes.position.count : 0
        tris += g.index ? g.index.count / 3 : (g.attributes.position ? g.attributes.position.count / 3 : 0)
      }
      o.frustumCulled = false
      const ms = Array.isArray(o.material) ? o.material : [o.material]
      for (const m of ms) {
        if (!m) continue
        if (!seenMat.has(m.uuid)) { seenMat.add(m.uuid); mats++ }
        if ('envMapIntensity' in m) m.envMapIntensity = 0.55
        if (m.map) {
          m.map.anisotropy = renderer.capabilities.getMaxAnisotropy()
          m.map.colorSpace = THREE.SRGBColorSpace
          if (!seenTex.has(m.map)) { seenTex.add(m.map); texs++; texList.push(m.map) }
        }
        m.side = THREE.FrontSide
        m.wireframe = wireframe.value
        m.needsUpdate = true
      }
    })

    let sum = 0, n = 0
    for (const t of texList) {
      const l = textureMeanLuma(t)
      if (l !== null) { sum += l; n++ }
    }
    const luma = n ? sum / n : 0.35
    renderer.toneMappingExposure =
      THREE.MathUtils.clamp(Math.pow(0.42 / Math.max(luma, 0.05), 0.75), 0.7, 3.2)

    scene.add(root)
    frameObject(root)
    stats.value = { meshes, verts, tris, mats, texs }
    loading.value = false
  }, undefined, (err: any) => {
    loading.value = false
    error.value = '加载失败：' + (err && err.message ? err.message : String(err))
  })
}

function toggleRotate() {
  autoRotate.value = !autoRotate.value
  if (controls) controls.autoRotate = autoRotate.value
}

function toggleWire() {
  wireframe.value = !wireframe.value
  if (!root) return
  root.traverse((o: any) => {
    if (!o.isMesh) return
    const ms = Array.isArray(o.material) ? o.material : [o.material]
    for (const m of ms) {
      if (!m) continue
      m.wireframe = wireframe.value
      m.needsUpdate = true
    }
  })
}

function resetView() {
  if (root) frameObject(root)
}

watch(currentSkinId, () => {
  const parts = groupedParts.value.flatMap(g => g.items)
  if (parts.length) loadModel(parts[0])
  else { disposeRoot(); stats.value = null; currentGlb.value = '' }
})

onMounted(async () => {
  await initViewer()
  const parts = groupedParts.value.flatMap(g => g.items)
  if (parts.length) loadModel(parts[0])
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  disposeRoot()
  if (renderer) renderer.dispose()
  renderer = null
  scene = null
  camera = null
  controls = null
})
</script>

<style scoped>
.viewer-btn {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  color: #cfd6e6;
  background: rgba(27, 33, 48, .85);
  border: 1px solid #2a3346;
  transition: all .15s;
}
.viewer-btn:hover { background: #232c3f; border-color: #3b4a68; }
.viewer-btn.on { background: #2f4d8a; border-color: #4a72c4; color: #fff; }
</style>
