<template>
  <div class="page">
    <h1>企业级 AI Agent 平台</h1>
    <p>Phase 1.2 · Vue 3 + FastAPI</p>
    <div class="cards">
      <el-card><template #header>Agent Runtime</template><b>Ready</b></el-card>
      <el-card><template #header>Model Gateway</template><b>Ready</b></el-card>
      <el-card><template #header>API</template><b>/api/v1</b></el-card>
    </div>
    <el-button type="primary" @click="$router.push('/agents')">进入 Agent 管理</el-button>
  </div>
</template>
<style scoped>.page{padding:40px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;max-width:900px;margin:30px 0}</style>
