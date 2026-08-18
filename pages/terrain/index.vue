<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">地图地形</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
      当前发布版本的固定地形
      <span class="font-medium text-gray-700 dark:text-gray-300">Mar Sara Wastelands（马萨拉废土）</span>。
      小地图与候选斜坡直接从地图文件提取；「模拟一局」按游戏内石头生成算法复刻一局随机布局。
    </p>

    <TerrainMap />
  </div>
</template>

<script setup lang="ts">
useHead({ title: '地图地形 · 凯瑞甘生存2 Wiki' })
</script>
