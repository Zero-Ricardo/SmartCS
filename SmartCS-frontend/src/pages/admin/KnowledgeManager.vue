<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from "vue";
import {
  listDocuments,
  uploadDocument,
  triggerProcess,
  triggerIngest,
  deleteVectors,
  deleteDocument,
  getDocument,
  batchProcessDocuments,
  type KnowledgeDocument,
} from "@/shared/api/adminApi";
import { ElMessage, ElMessageBox } from "element-plus";

const documents = ref<KnowledgeDocument[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const uploading = ref(false);
const selectedDocs = ref<KnowledgeDocument[]>([]);  // 选中的文档

// 进度轮询
const pollingIds = ref<Set<string>>(new Set());
let pollingTimer: ReturnType<typeof setInterval> | null = null;

const fetchDocuments = async () => {
  loading.value = true;
  try {
    const skip = (page.value - 1) * pageSize.value;
    const res = await listDocuments(skip, pageSize.value);
    documents.value = res.documents;
    total.value = res.total;

    // 检查哪些需要轮询进度
    pollingIds.value.clear();
    for (const doc of res.documents) {
      if (["parsing", "ingesting"].includes(doc.status)) {
        pollingIds.value.add(doc.id);
      }
    }
    updatePolling();
  } catch {
    ElMessage.error("获取文档列表失败");
  } finally {
    loading.value = false;
  }
};

const updatePolling = () => {
  if (pollingIds.value.size > 0 && !pollingTimer) {
    pollingTimer = setInterval(pollProgress, 2000);
  } else if (pollingIds.value.size === 0 && pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
};

const pollProgress = async () => {
  for (const docId of pollingIds.value) {
    try {
      const updated = await getDocument(docId);
      const idx = documents.value.findIndex((d) => d.id === docId);
      if (idx !== -1) {
        documents.value[idx] = updated;
      }
      if (updated.status !== "parsing" && updated.status !== "ingesting") {
        pollingIds.value.delete(docId);
        if (updated.status === "ingested") {
          ElMessage.success(`${updated.filename} 处理完成`);
        } else if (updated.status === "failed") {
          ElMessage.error(`${updated.filename} 处理失败: ${updated.error_message}`);
        }
      }
    } catch {
      // 忽略单次轮询失败
    }
  }
  updatePolling();
};

// 上传
const handleUpload = async (options: { file: File }) => {
  uploading.value = true;
  try {
    await uploadDocument(options.file);
    ElMessage.success("上传成功");
    await fetchDocuments();
  } catch (e: any) {
    ElMessage.error(e.message || "上传失败");
  } finally {
    uploading.value = false;
  }
};

// 一键处理（解析+入库）
const handleProcess = async (doc: KnowledgeDocument) => {
  try {
    await triggerProcess(doc.id);
    ElMessage.success("自动化处理管线已启动");
    // MD 文件跳过解析直接入库，其他需要解析
    doc.status = doc.file_type === "md" ? "ingesting" : "parsing";
    doc.ingest_progress = 0;
    pollingIds.value.add(doc.id);
    updatePolling();
  } catch (e: any) {
    ElMessage.error(e.message || "启动失败");
  }
};

// 表格选择变化
const handleSelectionChange = (selection: KnowledgeDocument[]) => {
  selectedDocs.value = selection;
};

// 批量处理
const handleBatchProcess = async () => {
  // 只处理 uploaded/parsed/failed 状态的文档
  const toProcess = selectedDocs.value.filter(
    doc => ['uploaded', 'parsed', 'failed'].includes(doc.status)
  );

  if (toProcess.length === 0) {
    ElMessage.warning("没有可处理的文档（仅支持待处理/待入库/失败状态）");
    return;
  }

  try {
    const result = await batchProcessDocuments(toProcess.map(d => d.id));
    ElMessage.success(result.message);

    // 将这些文档加入轮询
    for (const doc of toProcess) {
      doc.status = doc.file_type === "md" ? "ingesting" : "parsing";
      doc.ingest_progress = 0;
      pollingIds.value.add(doc.id);
    }
    updatePolling();
  } catch (e: any) {
    ElMessage.error(e.message || "批量处理失败");
  }
};

// 删除向量
const handleDeleteVectors = async (doc: KnowledgeDocument) => {
  await ElMessageBox.confirm(
    `确定要删除「${doc.filename}」的向量数据吗？文件本身会保留。`,
    "删除向量",
    { type: "warning" }
  );
  try {
    await deleteVectors(doc.id);
    ElMessage.success("向量已删除");
    await fetchDocuments();
  } catch {
    ElMessage.error("删除向量失败");
  }
};

// 删除文档
const handleDeleteDoc = async (doc: KnowledgeDocument) => {
  await ElMessageBox.confirm(
    `确定要彻底删除「${doc.filename}」吗？文件、向量数据将一并删除。`,
    "删除文档",
    { type: "error" }
  );
  try {
    await deleteDocument(doc.id);
    ElMessage.success("文档已删除");
    await fetchDocuments();
  } catch {
    ElMessage.error("删除文档失败");
  }
};

// 格式化
const formatSize = (bytes: number) => {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
};

const statusMap: Record<string, { label: string; type: string }> = {
  uploaded: { label: "待处理", type: "info" },
  parsing: { label: "正在解析", type: "warning" },
  parsed: { label: "待入库", type: "warning" },
  ingesting: { label: "入库中", type: "" },
  ingested: { label: "已入库", type: "success" },
  failed: { label: "处理失败", type: "danger" },
};

onMounted(fetchDocuments);
onUnmounted(() => {
  if (pollingTimer) clearInterval(pollingTimer);
});
</script>

<template>
  <div class="knowledge-manager">
    <div class="km-header">
      <h3>知识库文档管理</h3>
      <div class="km-header-actions">
        <el-button
          type="success"
          :disabled="selectedDocs.length === 0"
          @click="handleBatchProcess"
        >
          批量处理 ({{ selectedDocs.length }})
        </el-button>
        <el-upload
          :http-request="handleUpload as any"
          :show-file-list="false"
          accept=".md,.pdf,.docx,.txt"
          multiple
        >
          <el-button type="primary" :loading="uploading">上传文档</el-button>
        </el-upload>
      </div>
    </div>

    <el-table :data="documents" v-loading="loading" stripe class="km-table" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="50" />
      <el-table-column prop="filename" label="文件名" min-width="200" show-overflow-tooltip />
      <el-table-column prop="file_type" label="类型" width="80" align="center" />
      <el-table-column label="大小" width="100" align="right">
        <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="140" align="center">
        <template #default="{ row }">
          <div v-if="row.status === 'ingesting'" class="progress-cell">
            <el-progress
              :percentage="row.ingest_progress"
              :stroke-width="14"
              :text-inside="true"
              status="warning"
            />
          </div>
          <el-tag v-else :type="(statusMap[row.status]?.type as any) || 'info'" size="small">
            {{ statusMap[row.status]?.label || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="chunk_count" label="Chunks" width="80" align="center" />
      <el-table-column label="操作" width="220" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="['uploaded', 'parsed', 'failed'].includes(row.status)"
            type="primary"
            text
            size="small"
            @click="handleProcess(row)"
          >
            处理
          </el-button>
          <el-button
            v-if="row.status === 'ingested'"
            type="warning"
            text
            size="small"
            @click="handleDeleteVectors(row)"
          >
            删向量
          </el-button>
          <el-button
            type="danger"
            text
            size="small"
            @click="handleDeleteDoc(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
      <template #empty>
        <div class="km-empty">暂无文档，点击上方按钮上传</div>
      </template>
    </el-table>

    <el-pagination
      v-if="total > pageSize"
      v-model:current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next"
      class="km-pagination"
      @current-change="fetchDocuments"
    />
  </div>
</template>

<style scoped>
.knowledge-manager {
  padding: 4px;
}

.km-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.km-header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--color-text-1);
}

.km-header-actions {
  display: flex;
  gap: 12px;
}

.km-table {
  border-radius: 8px;
}

.progress-cell {
  width: 100%;
  padding: 0 4px;
}

.km-empty {
  padding: 40px 0;
  color: var(--color-text-3);
}

.km-pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
