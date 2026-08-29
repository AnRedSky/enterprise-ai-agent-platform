<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  createDocument,
  createKnowledgeBase,
  createVersion,
  deleteDocument,
  ingestVersion,
  listChunks,
  listDocuments,
  listKnowledgeBases,
  listVersions,
  retrieveKnowledge,
  type KnowledgeBase,
  type KnowledgeChunk,
  type KnowledgeDocument,
  type KnowledgeVersion,
  type RetrievalResult,
} from "@/api/knowledge";

const loading = ref(false);
const saving = ref(false);
const ingesting = ref("");
const retrievalLoading = ref(false);
const error = ref("");
const retrievalError = ref("");
const bases = ref<KnowledgeBase[]>([]);
const documents = ref<KnowledgeDocument[]>([]);
const versions = ref<KnowledgeVersion[]>([]);
const chunks = ref<KnowledgeChunk[]>([]);
const results = ref<RetrievalResult[]>([]);
const selectedBase = ref<KnowledgeBase | null>(null);
const selectedDocument = ref<KnowledgeDocument | null>(null);
const selectedVersion = ref<KnowledgeVersion | null>(null);
const selectedResult = ref<RetrievalResult | null>(null);
const baseDialog = ref(false);
const docDialog = ref(false);
const versionDialog = ref(false);
const baseForm = ref({ name: "企业知识库", description: "", status: "active" });
const docForm = ref({ title: "", source_type: "manual", source_uri: "" });
const versionForm = ref({ version: "v1", content_text: "", source_uri: "" });
const query = ref("");
const topK = ref(5);
const retrievalMode = ref<"lexical-v2" | "vector" | "hybrid">("lexical-v2");
const lexicalWeight = ref(0.5);
const vectorWeight = ref(0.5);

async function loadBases() {
  loading.value = true;
  error.value = "";
  try {
    const page = await listKnowledgeBases();
    bases.value = page.items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "知识库加载失败";
  } finally {
    loading.value = false;
  }
}

async function selectBase(base: KnowledgeBase | null) {
  selectedBase.value = base;
  selectedDocument.value = null;
  selectedVersion.value = null;
  documents.value = [];
  versions.value = [];
  chunks.value = [];
  results.value = [];
  selectedResult.value = null;
  if (!base) return;
  try {
    documents.value = (await listDocuments(base.id)).items;
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "文档加载失败");
  }
}

async function openDocument(doc: KnowledgeDocument) {
  if (!selectedBase.value) return;
  selectedDocument.value = doc;
  selectedVersion.value = null;
  chunks.value = [];
  try {
    versions.value = await listVersions(selectedBase.value.id, doc.id);
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "版本加载失败");
  }
}

async function saveBase() {
  if (!baseForm.value.name.trim()) return;
  saving.value = true;
  try {
    await createKnowledgeBase(baseForm.value);
    baseDialog.value = false;
    await loadBases();
    ElMessage.success("知识库创建成功");
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "知识库创建失败");
  } finally {
    saving.value = false;
  }
}

async function saveDocument() {
  if (!selectedBase.value || !docForm.value.title.trim()) return;
  saving.value = true;
  try {
    await createDocument(selectedBase.value.id, { ...docForm.value, source_uri: docForm.value.source_uri || null });
    docDialog.value = false;
    await selectBase(selectedBase.value);
    ElMessage.success("文档创建成功");
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "文档创建失败");
  } finally {
    saving.value = false;
  }
}

async function saveVersion() {
  if (!selectedBase.value || !selectedDocument.value || !versionForm.value.version.trim()) return;
  saving.value = true;
  try {
    await createVersion(selectedBase.value.id, selectedDocument.value.id, {
      ...versionForm.value,
      source_uri: versionForm.value.source_uri || null,
    });
    versionDialog.value = false;
    await openDocument(selectedDocument.value);
    ElMessage.success("版本创建成功");
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "版本创建失败");
  } finally {
    saving.value = false;
  }
}

async function processVersion(version: KnowledgeVersion) {
  ingesting.value = version.id;
  try {
    const out = await ingestVersion(version.id, { max_chars: 1000, overlap_chars: 100 });
    ElMessage.success(`内容切分完成，共生成 ${out.chunk_count} 个内容分片`);
    if (selectedDocument.value) await openDocument(selectedDocument.value);
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "版本处理失败");
  } finally {
    ingesting.value = "";
  }
}

async function openChunks(version: KnowledgeVersion) {
  selectedVersion.value = version;
  try {
    chunks.value = await listChunks(version.id);
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "内容分片加载失败");
  }
}

async function removeDocument(doc: KnowledgeDocument) {
  if (!selectedBase.value) return;
  try {
    await ElMessageBox.confirm(`确定删除文档「${doc.title}」吗？`, "删除确认", { type: "warning" });
    await deleteDocument(selectedBase.value.id, doc.id);
    await selectBase(selectedBase.value);
    ElMessage.success("文档已删除");
  } catch (e) {
    if (e !== "cancel" && e !== "close") ElMessage.error(e instanceof Error ? e.message : "删除失败");
  }
}

async function search() {
  const text = query.value.trim();
  if (!text) {
    retrievalError.value = "请输入检索问题";
    results.value = [];
    selectedResult.value = null;
    return;
  }
  retrievalLoading.value = true;
  retrievalError.value = "";
  selectedResult.value = null;
  try {
    const out = await retrieveKnowledge({
      query: text,
      top_k: topK.value,
      knowledge_base_id: selectedBase.value?.id,
      mode: retrievalMode.value,
      lexical_weight: retrievalMode.value === "hybrid" ? lexicalWeight.value : undefined,
      vector_weight: retrievalMode.value === "hybrid" ? vectorWeight.value : undefined,
    });
    results.value = out.results;
    if (!results.value.length) retrievalError.value = "没有找到相关内容，请调整问题或扩大知识库范围";
  } catch (e) {
    results.value = [];
    retrievalError.value = e instanceof Error ? e.message : "检索失败";
  } finally {
    retrievalLoading.value = false;
  }
}

function clearSearch() {
  query.value = "";
  results.value = [];
  selectedResult.value = null;
  retrievalError.value = "";
}

onMounted(loadBases);
</script>

<template>
  <div class="page">
    <header class="header">
      <div>
        <h1>知识库管理</h1>
        <p>统一管理知识库、文档、版本、内容分片，并提供可追溯的知识检索。</p>
      </div>
      <el-button type="primary" @click="baseDialog = true">新建知识库</el-button>
    </header>

    <el-alert v-if="error" :title="error" type="error" show-icon />

    <div class="grid">
      <el-card>
        <template #header><b>知识库</b></template>
        <el-table v-loading="loading" :data="bases" highlight-current-row @current-change="selectBase">
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="status" label="状态" width="100" />
        </el-table>
        <el-empty v-if="!loading && !bases.length" description="暂无知识库" />
      </el-card>

      <el-card>
        <template #header>
          <div class="panel-head"><b>文档</b><el-button size="small" type="primary" :disabled="!selectedBase" @click="docDialog = true">新建文档</el-button></div>
        </template>
        <el-table :data="documents" @row-click="openDocument">
          <el-table-column prop="title" label="标题" />
          <el-table-column prop="source_type" label="来源类型" width="100" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column label="操作" width="80"><template #default="{ row }"><el-button link type="danger" @click.stop="removeDocument(row)">删除</el-button></template></el-table-column>
        </el-table>
        <el-empty v-if="selectedBase && !documents.length" description="暂无文档" />
      </el-card>
    </div>

    <el-card v-if="selectedDocument" class="section">
      <template #header>
        <div class="panel-head"><b>文档版本：{{ selectedDocument.title }}</b><el-button size="small" type="primary" @click="versionDialog = true">新建版本</el-button></div>
      </template>
      <el-table :data="versions">
        <el-table-column prop="version" label="版本" width="100" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="ingestion_status" label="处理状态" width="110" />
        <el-table-column prop="created_at" label="创建时间" />
        <el-table-column label="操作" width="190">
          <template #default="{ row }">
            <el-button link type="success" :loading="ingesting === row.id" @click="processVersion(row)">处理版本</el-button>
            <el-button link type="primary" @click="openChunks(row)">查看分片</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="selectedVersion" class="section">
      <template #header><b>内容分片：{{ selectedVersion.version }}</b></template>
      <el-table :data="chunks">
        <el-table-column prop="chunk_index" label="序号" width="70" />
        <el-table-column prop="start_offset" label="起始位置" width="100" />
        <el-table-column prop="end_offset" label="结束位置" width="100" />
        <el-table-column prop="content" label="内容" min-width="400" />
      </el-table>
    </el-card>

    <el-card class="section">
      <template #header>
        <div class="panel-head">
          <div><b>知识检索调试</b><span class="hint">查看相关度、内容分片、引用位置和检索来源，便于定位检索效果。</span></div>
          <el-button v-if="query || results.length" link @click="clearSearch">清空</el-button>
        </div>
      </template>
      <div class="search">
        <el-input v-model="query" placeholder="输入检索问题，例如：公司的报销规则是什么？" clearable @keyup.enter="search" />
        <el-select v-model="retrievalMode" class="mode-select">
          <el-option label="关键词检索 v2" value="lexical-v2" />
          <el-option label="向量检索" value="vector" />
          <el-option label="混合检索" value="hybrid" />
        </el-select>
        <el-input-number v-model="topK" :min="1" :max="20" />
        <el-button type="primary" :loading="retrievalLoading" @click="search">检索</el-button>
      </div>
      <div v-if="retrievalMode === 'hybrid'" class="weights">
        <span>关键词权重</span><el-slider v-model="lexicalWeight" :min="0" :max="1" :step="0.1" />
        <span>向量权重</span><el-slider v-model="vectorWeight" :min="0" :max="1" :step="0.1" />
      </div>
      <el-alert v-if="retrievalError" :title="retrievalError" type="warning" show-icon :closable="false" />
      <div v-if="results.length" class="results">
        <el-table :data="results" highlight-current-row @current-change="(row) => selectedResult = row">
          <el-table-column prop="source_document" label="来源文档" width="180" />
          <el-table-column prop="relevance_score" label="相关度" width="100" />
          <el-table-column label="检索方式" width="110">
            <template #default="{ row }">{{ row.retrieval_mode === 'lexical-v2' ? '关键词检索' : row.retrieval_mode === 'vector' ? '向量检索' : '混合检索' }}</template>
          </el-table-column>
          <el-table-column label="检索来源" width="150"><template #default="{ row }">{{ row.retrieval_sources?.join(" + ") || "默认来源" }}</template></el-table-column>
          <el-table-column prop="citation" label="引用位置" width="220" />
          <el-table-column prop="content" label="内容" min-width="400" show-overflow-tooltip />
        </el-table>
        <el-card v-if="selectedResult" class="detail" shadow="never">
          <template #header><b>引用与检索详情</b></template>
          <div class="meta">
            <span><b>文档：</b>{{ selectedResult.source_document }}</span>
            <span><b>相关度：</b>{{ selectedResult.relevance_score }}</span>
            <span><b>检索方式：</b>{{ selectedResult.retrieval_mode }}</span>
            <span><b>检索来源：</b>{{ selectedResult.retrieval_sources?.join(" + ") || "-" }}</span>
            <span><b>引用位置：</b>{{ selectedResult.citation }}</span>
          </div>
          <div v-if="selectedResult.hybrid_score_breakdown" class="breakdown">
            <b>混合检索评分明细</b>
            <div>关键词评分：{{ selectedResult.hybrid_score_breakdown.lexical_score ?? "未命中" }} × {{ selectedResult.hybrid_score_breakdown.lexical_weight }}</div>
            <div>向量评分：{{ selectedResult.hybrid_score_breakdown.vector_score ?? "未命中" }} × {{ selectedResult.hybrid_score_breakdown.vector_weight }}</div>
            <div>综合评分：{{ selectedResult.hybrid_score_breakdown.fused_score }}</div>
          </div>
          <div class="content">{{ selectedResult.content }}</div>
          <div v-if="selectedResult.source_uri" class="source"><b>来源地址：</b>{{ selectedResult.source_uri }}</div>
        </el-card>
      </div>
      <el-empty v-if="!retrievalLoading && query && !results.length && !retrievalError" description="没有找到相关内容" />
      <el-empty v-if="!query && !results.length" description="输入问题后开始检索" />
    </el-card>

    <el-dialog v-model="baseDialog" title="新建知识库" width="520px">
      <el-form label-width="90px"><el-form-item label="名称"><el-input v-model="baseForm.name" /></el-form-item><el-form-item label="描述"><el-input v-model="baseForm.description" type="textarea" /></el-form-item></el-form>
      <template #footer><el-button @click="baseDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveBase">创建</el-button></template>
    </el-dialog>
    <el-dialog v-model="docDialog" title="新建文档" width="520px">
      <el-form label-width="90px"><el-form-item label="标题"><el-input v-model="docForm.title" /></el-form-item><el-form-item label="来源类型"><el-input v-model="docForm.source_type" /></el-form-item><el-form-item label="来源地址"><el-input v-model="docForm.source_uri" /></el-form-item></el-form>
      <template #footer><el-button @click="docDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveDocument">创建</el-button></template>
    </el-dialog>
    <el-dialog v-model="versionDialog" title="新建文档版本" width="620px">
      <el-form label-width="90px"><el-form-item label="版本"><el-input v-model="versionForm.version" /></el-form-item><el-form-item label="来源地址"><el-input v-model="versionForm.source_uri" /></el-form-item><el-form-item label="正文"><el-input v-model="versionForm.content_text" type="textarea" :rows="10" /></el-form-item></el-form>
      <template #footer><el-button @click="versionDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveVersion">创建</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { padding: 32px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 22px; }
.header p { color: #667085; }
.grid { display: grid; grid-template-columns: 1fr 1.6fr; gap: 18px; }
.section { margin-bottom: 18px; }
.panel-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.hint { margin-left: 10px; color: #667085; font-size: 12px; font-weight: normal; }
.search { display: flex; gap: 10px; margin-bottom: 16px; }
.search .el-input { flex: 1; }
.mode-select { width: 150px; }
.weights { display: grid; grid-template-columns: 100px 1fr 100px 1fr; gap: 12px; align-items: center; margin-bottom: 16px; color: #475467; font-size: 13px; }
.results { margin-top: 16px; }
.detail { margin-top: 16px; }
.meta { display: grid; gap: 8px; color: #475467; font-size: 13px; }
.breakdown { margin-top: 16px; padding: 12px; border: 1px solid #e4e7ec; border-radius: 6px; line-height: 1.8; color: #344054; }
.content { margin-top: 16px; padding: 14px; white-space: pre-wrap; line-height: 1.7; background: #f8fafc; border-radius: 6px; }
.source { margin-top: 12px; color: #667085; font-size: 12px; word-break: break-all; }
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } .page { padding: 16px; } .search { flex-wrap: wrap; } }
</style>
