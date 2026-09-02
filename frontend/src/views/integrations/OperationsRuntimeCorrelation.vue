<template>
  <SurfaceCard title="Runtime durable correlation" description="从当前租户运维审计中读取后端明确返回的 Execution 关联事实；没有明确关联 ID 时不做推断。">
    <StatePanel v-if="state === 'loading'" state="loading" title="正在加载 Runtime 关联事实" description="正在读取运维审计记录。" />
    <StatePanel v-else-if="state === 'permission'" state="permission" title="无权查看 Runtime 关联" description="当前账号没有读取运维审计所需权限。" />
    <StatePanel v-else-if="state === 'error'" state="error" title="Runtime 关联加载失败" description="无法读取运维审计关联事实，请稍后重试。" action-label="重试" @action="load" />
    <StatePanel v-else-if="!rows.length" state="empty" title="暂无可关联的 Execution" description="当前窗口没有包含明确 workflow_execution_id 的审计事实；不会根据时间、顺序或字符串猜测关联对象。" />
    <el-table v-else :data="rows" size="small" show-overflow-tooltip>
      <el-table-column prop="action" label="操作" min-width="220" />
      <el-table-column prop="resource_type" label="资源类型" width="150" />
      <el-table-column prop="resource_id" label="资源标识" min-width="180" />
      <el-table-column label="Execution" min-width="240">
        <template #default="{ row }">
          <el-button link type="primary" @click="openExecution(row.executionId)">{{ row.executionId }}</el-button>
        </template>
      </el-table-column>
      <el-table-column prop="outcome" label="结果" width="100" />
      <el-table-column prop="created_at" label="时间" min-width="180" />
    </el-table>
  </SurfaceCard>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";
import StatePanel from "@/components/ui/StatePanel.vue";
import { runtimeOperationsApi, type RuntimeAudit } from "@/api/runtimeOperations";

type CorrelationRow = RuntimeAudit & { executionId: string };
const router = useRouter();
const state = ref<"loading" | "success" | "empty" | "error" | "permission">("loading");
const rows = ref<CorrelationRow[]>([]);

function executionIdOf(audit: RuntimeAudit): string | null {
  const value = audit.details?.workflow_execution_id;
  return typeof value === "string" && value.length > 0 ? value : null;
}

async function load() {
  state.value = "loading";
  rows.value = [];
  try {
    const result = await runtimeOperationsApi.auditQuery({ page: 1, page_size: 100 });
    rows.value = result.data.items.flatMap((audit) => {
      const executionId = executionIdOf(audit);
      return executionId ? [{ ...audit, executionId }] : [];
    });
    state.value = rows.value.length ? "success" : "empty";
  } catch (error: any) {
    state.value = error?.response?.status === 403 ? "permission" : "error";
  }
}

function openExecution(executionId: string) {
  void router.push({ path: "/runtime", query: { execution_id: executionId, source: "runtime-operations-audit" } });
}

onMounted(load);
</script>
