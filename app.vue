<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<script setup lang="ts">
const { init: initColorMode } = useColorMode()
const { init: initAuth } = useAuth()
onMounted(() => {
  initColorMode()
  initAuth()
})
</script>
