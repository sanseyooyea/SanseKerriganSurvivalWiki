<template>
  <div />
</template>

<script setup lang="ts">
// 「版本Meta」已并入 /balance 的「跨版本走势」标签页。
// 保留此路由做重定向，避免旧链接 / 书签 404。SSR 与客户端均生效。
await navigateTo({ path: '/balance', query: { tab: 'trends' } }, { replace: true, redirectCode: 301 })
</script>
