<template>
  <div class="login-page">
    <el-card class="login-card">
      <template #header><strong>Enterprise AI Agent Platform</strong></template>
      <el-form :model="form" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password autocomplete="current-password" @keyup.enter="submit" />
        </el-form-item>
        <el-alert v-if="error" :title="error" type="error" :closable="false" class="error" />
        <el-button type="primary" :loading="loading" native-type="submit" style="width: 100%">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { login } from "../api/auth";

const router = useRouter();
const form = reactive({ username: "", password: "" });
const loading = ref(false);
const error = ref("");

async function submit() {
  error.value = "";
  if (!form.username || !form.password) {
    error.value = "请输入用户名和密码";
    return;
  }
  loading.value = true;
  try {
    await login(form.username, form.password);
    await router.replace("/dashboard");
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "登录失败，请检查用户名和密码";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page { min-height: 100vh; display: grid; place-items: center; background: #f5f7fa; }
.login-card { width: min(420px, calc(100vw - 32px)); }
.error { margin-bottom: 16px; }
</style>
