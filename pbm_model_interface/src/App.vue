
<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();


const layoutClass = computed(() => {
  if (route.meta.layout === 'full-width') {
    return 'layout-full';
  }
  return 'layout-container';
});
</script>

<template>

  

  <div :class="layoutClass">
    <router-view />
  </div>
</template>

<style>

body {
  margin: 0;
  background-color: #f0f2f5;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}


.layout-container {
  max-width: 1200px;
  margin: 40px auto;
  padding: 2rem;
}


.layout-full {
  height: 100vh;
}
</style>