<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { getMe, removeToken, type AdminUser } from "@/shared/api/adminApi";

const router = useRouter();
const admin = ref<AdminUser | null>(null);
const sideCollapsed = ref(false);

onMounted(async () => {
  try {
    admin.value = await getMe();
  } catch {
    router.replace("/admin/login");
  }
});

const handleLogout = () => {
  removeToken();
  router.replace("/admin/login");
};
</script>

<template>
  <el-container class="admin-layout">
    <el-aside :width="sideCollapsed ? '64px' : '200px'" class="admin-aside">
      <div class="admin-logo" @click="router.push('/admin')">
        <img src="/logo_PXB.png" alt="logo" class="admin-logo-img" />
        <span v-show="!sideCollapsed" class="admin-logo-text">SmartCS</span>
      </div>
      <el-menu
        :default-active="$route.path"
        :collapse="sideCollapsed"
        router
        class="admin-menu"
      >
        <el-menu-item index="/admin/knowledge">
          <el-icon><el-icon-document /></el-icon>
          <template #title>知识库管理</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <el-icon
          class="collapse-btn"
          @click="sideCollapsed = !sideCollapsed"
        >
          <el-icon-fold v-if="!sideCollapsed" />
          <el-icon-expand v-else />
        </el-icon>
        <div class="header-right">
          <span class="admin-email">{{ admin?.email }}</span>
          <el-button text @click="handleLogout">退出</el-button>
        </div>
      </el-header>

      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin-layout {
  height: 100vh;
}

.admin-aside {
  background: #fff;
  border-right: 1px solid var(--color-border);
  transition: width 0.25s;
  overflow: hidden;
}

.admin-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px;
  cursor: pointer;
  height: 56px;
}

.admin-logo-img {
  width: 32px;
  height: 32px;
  object-fit: contain;
}

.admin-logo-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-1);
  white-space: nowrap;
}

.admin-menu {
  border-right: none;
}

.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid var(--color-border);
  height: 56px;
  padding: 0 20px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: var(--color-text-2);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.admin-email {
  font-size: 14px;
  color: var(--color-text-2);
}

.admin-main {
  background: var(--color-bg-page);
  min-height: 0;
}
</style>
