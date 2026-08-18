<template>
  <div class="page">
    <div class="header"><div><h1>Agent 管理</h1><p>创建并测试 Agent</p></div><el-button type="primary" @click="dialogVisible=true">创建 Agent</el-button></div>
    <el-table :data="agents" border>
      <el-table-column prop="name" label="名称"/>
      <el-table-column prop="model" label="模型"/>
      <el-table-column prop="version" label="版本"/>
      <el-table-column prop="status" label="状态"/>
      <el-table-column label="操作"><template #default="{row}"><el-button link type="primary" @click="openChat(row.id)">测试</el-button></template></el-table-column>
    </el-table>
    <el-dialog v-model="dialogVisible" title="创建 Agent" width="520px">
      <el-form label-width="110px">
        <el-form-item label="名称"><el-input v-model="form.name"/></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description"/></el-form-item>
        <el-form-item label="System Prompt"><el-input v-model="form.system_prompt" type="textarea" :rows="4"/></el-form-item>
        <el-form-item label="模型"><el-input v-model="form.model"/></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" @click="create">创建</el-button></template>
    </el-dialog>
    <el-dialog v-model="chatVisible" title="Agent 测试" width="650px">
      <el-input v-model="input" type="textarea" :rows="5" placeholder="输入消息..."/>
      <div class="answer" v-if="answer">{{answer}}</div>
      <template #footer><el-button @click="chatVisible=false">关闭</el-button><el-button type="primary" :loading="loading" @click="execute">执行</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import {onMounted,ref} from "vue";
import {ElMessage} from "element-plus";
import {listAgents,createAgent,executeAgent,type Agent} from "../api/agents";
const agents=ref<Agent[]>([]),dialogVisible=ref(false),chatVisible=ref(false),loading=ref(false),input=ref(""),answer=ref(""),selected=ref<Agent|null>(null);
const form=ref({name:"企业智能助手",description:"Phase 1.2 默认 Agent",system_prompt:"你是一个企业级 AI 助手，请准确、简洁地回答用户问题。",model:"mock-model"});
async function load(){agents.value=await listAgents()}
async function create(){await createAgent(form.value);dialogVisible.value=false;await load();ElMessage.success("Agent 创建成功")}
function openChat(agentId:string){selected.value=agents.value.find((agent)=>agent.id===agentId) ?? null;answer.value="";input.value="";chatVisible.value=true}
async function execute(){if(!selected.value||!input.value.trim())return;loading.value=true;try{answer.value=(await executeAgent(selected.value.id,input.value)).answer}finally{loading.value=false}}
onMounted(load);
</script>
<style scoped>.page{padding:40px}.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}.answer{white-space:pre-wrap;margin-top:20px;padding:16px;background:#f5f7fa;border-radius:8px}</style>
