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
const error = ref("");
const bases = ref<KnowledgeBase[]>([]);
const documents = ref<KnowledgeDocument[]>([]);
const versions = ref<KnowledgeVersion[]>([]);
const chunks = ref<KnowledgeChunk[]>([]);
const results = ref<RetrievalResult[]>([]);
const selectedResult = ref<RetrievalResult | null>(null);
const selectedBase = ref<KnowledgeBase | null>(null);
const selectedDocument = ref<KnowledgeDocument | null>(null);
const selectedVersion = ref<KnowledgeVersion | null>(null);
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
const saving = ref(false);
const ingesting = ref("");
const retrievalLoading = ref(false);
const retrievalError = ref("");

function userError(value: unknown, fallback: string) {
  return value instanceof Error && /[\u4e00-\u9fff]/.test(value.message) ? fallback : fallback;
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    active: "已启用（active）",
    inactive: "已停用（inactive）",
    draft: "草稿（draft）",
    published: "已发布（published）",
    archived: "已归档（archived）",
    ready: "已就绪（ready）",
    pending: "待处理（pending）",
    processing: "处理中（processing）",
    completed: "已完成（completed）",
    failed: "处理失败（failed）",
  };
  return labels[status] ?? `未知状态（${status}）`;
}

function sourceTypeLabel(sourceType: string) {
  return sourceType === "manual" ? "手动录入（manual）" : `来源类型（${sourceType}）`;
}

function ingestionStatusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: "待处理（pending）",
    processing: "处理中（processing）",
    completed: "已完成（completed）",
    failed: "处理失败（failed）",
  };
  return labels[status] ?? `未知处理状态（${status}）`;
}

function retrievalModeLabel(mode: string) {
  const labels: Record<string, string> = {
    "lexical-v2": "关键词检索 v2（lexical-v2）",
    vector: "向量检索（vector）",
    hybrid: "混合检索（hybrid）",
  };
  return labels[mode] ?? `未知检索方式（${mode}）`;
}

function retrievalSourceLabel(source: string) {
  const labels: Record<string, string> = { lexical: "关键词", vector: "向量" };
  return labels[source] ?? `未知来源（${source}）`;
}

function retrievalErrorMessage(value: unknown, fallback: string) {
  return userError(value, fallback);
}

function isKnowledgeDocument(value: unknown): value is KnowledgeDocument {
  if (!value || typeof value !== "object") return false;
  const row = value as Partial<KnowledgeDocument>;
  return typeof row.id === "string" && typeof row.title === "string";
}

function isKnowledgeVersion(value: unknown): value is KnowledgeVersion {
  if (!value || typeof value !== "object") return false;
  const row = value as Partial<KnowledgeVersion>;
  return typeof row.id === "string" && typeof row.document_id === "string" && typeof row.version === "string";
}

async function loadBases() {
  loading.value = true;
  error.value = "";
  try {
    const page = await listKnowledgeBases();
    bases.value = page.items;
    if (selectedBase.value) selectedBase.value = bases.value.find((item) => item.id === selectedBase.value?.id) ?? null;
  } catch (e) {
    error.value = userError(e, "知识库加载失败，请刷新后重试");
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
    ElMessage.error(userError(e, "文档加载失败，请刷新后重试"));
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
    ElMessage.error(userError(e, "知识库创建失败，请稍后重试"));
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
    ElMessage.error(userError(e, "文档创建失败，请稍后重试"));
  } finally {
    saving.value = false;
  }
}

async function saveVersion() {
  if (!selectedBase.value || !selectedDocument.value || !versionForm.value.version.trim()) return;
  saving.value = true;
  try {
    await createVersion(selectedBase.value.id, selectedDocument.value.id, { ...versionForm.value, source_uri: versionForm.value.source_uri || null });
    versionDialog.value = false;
    await openDocument(selectedDocument.value);
    ElMessage.success("版本创建成功");
  } catch (e) {
    ElMessage.error(userError(e, "版本创建失败，请稍后重试"));
  } finally {
    saving.value = false;
  }
}

async function openDocument(doc: unknown) {
  if (!selectedBase.value || !isKnowledgeDocument(doc)) return;
  selectedDocument.value = doc;
  selectedVersion.value = null;
  chunks.value = [];
  try {
    versions.value = await listVersions(selectedBase.value.id, doc.id);
  } catch (e) {
    ElMessage.error(userError(e, "版本加载失败，请刷新后重试"));
  }
}

async function ingest(version: unknown) {
  if (!isKnowledgeVersion(version)) return;
  ingesting.value = version.id;
  try {
    const out = await ingestVersion(version.id, { max_chars: 1000, overlap_chars: 100 });
    ElMessage.success(`内容切分完成：${out.chunk_count} 个分块（Chunk）`);
    if (selectedDocument.value) await openDocument(selectedDocument.value);
  } catch (e) {
    ElMessage.error(userError(e, "知识版本处理失败，请稍后重试"));
  } finally {
    ingesting.value = "";
  }
}

async function openChunks(version: unknown) {
  if (!isKnowledgeVersion(version)) return;
  selectedVersion.value = version;
  try {
    chunks.value = await listChunks(version.id);
  } catch (e) {
    ElMessage.error(userError(e, "分块加载失败，请刷新后重试"));
  }
}

async function removeDocument(doc: unknown) {
  if (!selectedBase.value || !isKnowledgeDocument(doc)) return;
  try {
    await ElMessageBox.confirm(`确定删除文档「${doc.title}」吗？`, "删除确认", { type: "warning" });
    await deleteDocument(selectedBase.value.id, doc.id);
    await selectBase(selectedBase.value);
    ElMessage.success("文档已删除");
  } catch (e) {
    if (e !== "cancel" && e !== "close") ElMessage.error(userError(e, "文档删除失败，请稍后重试"));
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
    if (!out.results.length) retrievalError.value = "没有命中结果，请尝试调整问题或扩大知识库范围";
  } catch (e) {
    results.value = [];
    retrievalError.value = retrievalErrorMessage(e, "知识检索失败，请稍后重试");
  } finally {
    retrievalLoading.value = false;
  }
}

function selectResult(result: RetrievalResult | null) {
  selectedResult.value = result;
}

function clearRetrieval() {
  query.value = "";
  results.value = [];
  selectedResult.value = null;
  retrievalError.value = "";
}

onMounted(loadBases);
</script>

<template>
  <div class="page">
    <div class="header">
      <div><h1>知识库管理</h1><p>统一管理知识库、文档、版本和内容分块，并支持知识检索调试。</p></div>
      <el-button type="primary" @click="baseDialog = true">新建知识库</el-button>
    </div>
    <el-alert v-if="error" :title="error" type="error" show-icon />

    <div class="grid">
      <el-card class="panel">
        <template #header><b>知识库</b></template>
        <el-table v-loading="loading" :data="bases" highlight-current-row @current-change="selectBase">
          <el-table-column prop="name" label="名称" />
          <el-table-column label="状态" width="150"><template #default="{ row }">{{ statusLabel(row.status) }}</template></el-table-column>
        </el-table>
        <el-empty v-if="!loading && !bases.length" description="暂无知识库" />
      </el-card>

      <el-card class="panel">
        <template #header><div class="panel-head"><b>文档</b><el-button size="small" type="primary" :disabled="!selectedBase" @click="docDialog = true">新建文档</el-button></div></template>
        <el-table :data="documents" @row-click="openDocument">
          <el-table-column prop="title" label="标题" />
          <el-table-column label="来源" width="150"><template #default="{ row }">{{ sourceTypeLabel(row.source_type) }}</template></el-table-column>
          <el-table-column label="状态" width="150"><template #default="{ row }">{{ statusLabel(row.status) }}</template></el-table-column>
          <el-table-column label="操作" width="70"><template #default="{ row }"><el-button link type="danger" @click.stop="removeDocument(row)">删除</el-button></template></el-table-column>
        </el-table>
        <el-empty v-if="selectedBase && !documents.length" description="暂无文档" />
      </el-card>
    </div>

    <el-card v-if="selectedDocument" class="section">
      <template #header><div class="panel-head"><b>版本：{{ selectedDocument.title }}</b><el-button size="small" type="primary" @click="versionDialog = true">新建版本</el-button></div></template>
      <el-table :data="versions">
        <el-table-column prop="version" label="版本" width="100" />
        <el-table-column label="状态" width="150"><template #default="{ row }">{{ statusLabel(row.status) }}</template></el-table-column>
        <el-table-column label="处理状态" width="170"><template #default="{ row }">{{ ingestionStatusLabel(row.ingestion_status) }}</template></el-table-column>
        <el-table-column prop="created_at" label="创建时间" />
        <el-table-column label="操作" width="230"><template #default="{ row }"><el-button link type="success" :loading="ingesting === row.id" @click="ingest(row)">执行切分（Ingest）</el-button><el-button link type="primary" @click="openChunks(row)">查看分块（Chunks）</el-button></template></el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="selectedVersion" class="section">
      <template #header><b>分块：{{ selectedVersion.version }}</b></template>
      <el-table :data="chunks">
        <el-table-column prop="chunk_index" label="序号" width="60" />
        <el-table-column prop="start_offset" label="起始位置" width="100" />
        <el-table-column prop="end_offset" label="结束位置" width="100" />
        <el-table-column prop="content" label="内容" min-width="400" />
      </el-table>
    </el-card>

    <el-card class="section retrieval-panel">
      <template #header><div class="panel-head"><div><b>知识检索调试</b><span class="hint">可查看检索结果、相关度、分块、引用以及混合检索来源。</span></div><el-button v-if="query || results.length" link @click="clearRetrieval">清空</el-button></div></template>
      <div class="search">
        <el-input v-model="query" placeholder="输入检索问题，例如：公司的报销规则是什么？" clearable @keyup.enter="search" />
        <el-select v-model="retrievalMode" class="mode-select">
          <el-option label="关键词检索 v2（lexical-v2）" value="lexical-v2" />
          <el-option label="向量检索（vector）" value="vector" />
          <el-option label="混合检索（hybrid）" value="hybrid" />
        </el-select>
        <el-input-number v-model="topK" :min="1" :max="20" />
        <el-button type="primary" :loading="retrievalLoading" @click="search">检索</el-button>
      </div>
      <div v-if="retrievalMode === 'hybrid'" class="weights">
        <span>关键词权重</span><el-slider v-model="lexicalWeight" :min="0" :max="1" :step="0.1" />
        <span>向量权重</span><el-slider v-model="vectorWeight" :min="0" :max="1" :step="0.1" />
      </div>
      <el-alert v-if="retrievalError" :title="retrievalError" type="warning" show-icon :closable="false" />
      <div v-if="results.length" class="retrieval-grid">
        <el-table :data="results" highlight-current-row class="result-table" @current-change="selectResult">
          <el-table-column prop="source_document" label="来源文档" width="180" />
          <el-table-column prop="relevance_score" label="相关度（Score）" width="130" />
          <el-table-column label="检索方式（Mode）" width="180"><template #default="{ row }">{{ retrievalModeLabel(row.retrieval_mode) }}</template></el-table-column>
          <el-table-column label="检索来源（Sources）" width="180"><template #default="{ row }">{{ row.retrieval_sources?.map(retrievalSourceLabel).join(" + ") || retrievalModeLabel(row.retrieval_mode) }}</template></el-table-column>
          <el-table-column prop="citation" label="引用（Citation）" width="220" />
          <el-table-column prop="content" label="内容" min-width="400" show-overflow-tooltip />
        </el-table>
        <el-card v-if="selectedResult" class="citation-card" shadow="never">
          <template #header><b>引用与检索详情</b></template>
          <div class="citation-meta"><span><b>文档：</b>{{ selectedResult.source_document }}</span><span><b>相关度（Score）：</b>{{ selectedResult.relevance_score }}</span><span><b>检索方式（Mode）：</b>{{ retrievalModeLabel(selectedResult.retrieval_mode) }}</span><span><b>检索来源（Sources）：</b>{{ selectedResult.retrieval_sources?.map(retrievalSourceLabel).join(" + ") || "-" }}</span><span><b>引用（Citation）：</b>{{ selectedResult.citation }}</span></div>
          <div v-if="selectedResult.hybrid_score_breakdown" class="breakdown">
            <b>混合检索评分明细</b>
            <div>关键词相关度：{{ selectedResult.hybrid_score_breakdown.lexical_score ?? "未命中" }} × {{ selectedResult.hybrid_score_breakdown.lexical_weight }}</div>
            <div>向量相关度：{{ selectedResult.hybrid_score_breakdown.vector_score ?? "未命中" }} × {{ selectedResult.hybrid_score_breakdown.vector_weight }}</div>
            <div>融合结果：{{ selectedResult.hybrid_score_breakdown.fused_score }}</div>
          </div>
          <div class="citation-content">{{ selectedResult.content }}</div>
          <div v-if="selectedResult.source_uri" class="citation-source"><b>来源地址（Source URI）：</b>{{ selectedResult.source_uri }}</div>
        </el-card>
      </div>
      <el-empty v-if="!retrievalLoading && query && !results.length && !retrievalError" description="没有命中结果" />
      <el-empty v-if="!query && !results.length" description="输入问题后执行知识检索调试" />
    </el-card>

    <el-dialog v-model="baseDialog" title="新建知识库" width="520px">
      <el-form label-width="90px"><el-form-item label="名称"><el-input v-model="baseForm.name" /></el-form-item><el-form-item label="描述"><el-input v-model="baseForm.description" type="textarea" /></el-form-item></el-form>
      <template #footer><el-button @click="baseDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveBase">创建</el-button></template>
    </el-dialog>
    <el-dialog v-model="docDialog" title="新建文档" width="520px">
      <el-form label-width="90px"><el-form-item label="标题"><el-input v-model="docForm.title" /></el-form-item><el-form-item label="来源类型"><el-input v-model="docForm.source_type" /></el-form-item><el-form-item label="来源地址（URI）"><el-input v-model="docForm.source_uri" /></el-form-item></el-form>
      <template #footer><el-button @click="docDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveDocument">创建</el-button></template>
    </el-dialog>
    <el-dialog v-model="versionDialog" title="新建文档版本" width="620px">
      <el-form label-width="90px"><el-form-item label="版本"><el-input v-model="versionForm.version" /></el-form-item><el-form-item label="来源地址（URI）"><el-input v-model="versionForm.source_uri" /></el-form-item><el-form-item label="正文"><el-input v-model="versionForm.content_text" type="textarea" :rows="10" /></el-form-item></el-form>
      <template #footer><el-button @click="versionDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveVersion">创建</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { padding: 32px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 22px; }
.header p { color: #667085; }
.grid { display: grid; grid-template-columns: 1fr 1.6fr; gap: 18px; }
.panel, .section { margin-bottom: 18px; }
.panel-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.hint { margin-left: 10px; color: #667085; font-size: 12px; font-weight: normal; }
.search { display: flex; gap: 10px; margin-bottom: 16px; }
.search .el-input { flex: 1; }
.mode-select { width: 190px; }
.weights { display: grid; grid-template-columns: 100px 1fr 100px 1fr; gap: 12px; align-items: center; margin-bottom: 16px; color: #475467; font-size: 13px; }
.retrieval-grid { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(280px, 0.8fr); gap: 16px; margin-top: 16px; }
.result-table, .citation-card { min-width: 0; }
.citation-meta { display: grid; gap: 8px; color: #475467; font-size: 13px; }
.breakdown { margin-top: 16px; padding: 12px; border: 1px solid #e4e7ec; border-radius: 6px; line-height: 1.8; color: #344054; }
.citation-content { margin-top: 16px; padding: 14px; white-space: pre-wrap; line-height: 1.7; background: #f8fafc; border-radius: 6px; }
.citation-source { margin-top: 12px; color: #667085; font-size: 12px; word-break: break-all; }
@media (max-width: 1100px) { .retrieval-grid { grid-template-columns: 1fr; } .weights { grid-template-columns: 100px 1fr; } }
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } .page { padding: 16px; } .search { flex-wrap: wrap; } }
</style>
