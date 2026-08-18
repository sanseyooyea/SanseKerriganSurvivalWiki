<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">地图地形</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
      KS2 每次发布只烘焙地图池里的<span class="font-medium text-gray-700 dark:text-gray-300">一张地形</span>，此处汇集了历史各版本的全部地形。
      顶部缩略图切换地图，小地图与候选斜坡直接从各地图文件提取；「模拟一局」按游戏内石头生成算法复刻一局随机布局。
    </p>

    <TerrainMap />
  </div>
</template>

<script setup lang="ts">
useHead({ title: '地图地形 · 凯瑞甘生存2 Wiki' })
</script>
