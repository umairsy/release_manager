<template>
  <div class="min-h-screen bg-surface-white text-ink-gray-8">
    <header class="border-b px-6 h-14 flex items-center gap-2">
      <router-link to="/" class="font-semibold text-ink-gray-9">Release Manager</router-link>
      <span class="text-ink-gray-4">/</span>
      <span class="text-sm text-ink-gray-5">{{ siteName }}</span>
    </header>
    <router-view />
  </div>
</template>

<script setup>
const siteName = window.site_name || "";
</script>
