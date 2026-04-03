<script setup lang="ts">
import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { login, register, setToken } from "@/shared/api/adminApi";
import { ElMessage } from "element-plus";

const router = useRouter();
const isLogin = ref(true);
const loading = ref(false);

const loginForm = reactive({ username: "", password: "" });
const registerForm = reactive({ username: "", password: "", confirm_password: "" });

const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning("请输入用户名和密码");
    return;
  }
  loading.value = true;
  try {
    const res = await login(loginForm);
    setToken(res.access_token);
    ElMessage.success("登录成功");
    router.replace("/admin/knowledge");
  } catch (e: any) {
    ElMessage.error(e.message || "登录失败");
  } finally {
    loading.value = false;
  }
};

const handleRegister = async () => {
  if (!registerForm.username || !registerForm.password) {
    ElMessage.warning("请输入用户名和密码");
    return;
  }
  if (registerForm.password !== registerForm.confirm_password) {
    ElMessage.warning("两次密码不一致");
    return;
  }
  loading.value = true;
  try {
    await register(registerForm);
    ElMessage.success("注册成功，请登录");
    isLogin.value = true;
    loginForm.username = registerForm.username;
    loginForm.password = "";
  } catch (e: any) {
    ElMessage.error(e.message || "注册失败");
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <img src="/logo_PXB.png" alt="logo" class="login-logo" />
        <h2>SmartCS 管理后台</h2>
      </div>

      <el-tabs v-model="isLogin" class="login-tabs">
        <el-tab-pane label="登录" :name="true">
          <el-form @submit.prevent="handleLogin">
            <el-form-item>
              <el-input
                v-model="loginForm.username"
                placeholder="用户名"
                size="large"
                prefix-icon="User"
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="密码"
                size="large"
                prefix-icon="Lock"
                show-password
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              class="login-btn"
              @click="handleLogin"
            >
              登录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" :name="false">
          <el-form @submit.prevent="handleRegister">
            <el-form-item>
              <el-input
                v-model="registerForm.username"
                placeholder="用户名"
                size="large"
                prefix-icon="User"
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="密码"
                size="large"
                prefix-icon="Lock"
                show-password
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="registerForm.confirm_password"
                type="password"
                placeholder="确认密码"
                size="large"
                prefix-icon="Lock"
                show-password
              />
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              class="login-btn"
              @click="handleRegister"
            >
              注册
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
}

.login-card {
  width: 400px;
  background: #fff;
  border-radius: 16px;
  padding: 40px 32px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
}

.login-header {
  text-align: center;
  margin-bottom: 24px;
}

.login-logo {
  width: 48px;
  height: 48px;
  margin-bottom: 12px;
}

.login-header h2 {
  margin: 0;
  font-size: 20px;
  color: var(--color-text-1);
}

.login-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.login-btn {
  width: 100%;
  margin-top: 8px;
}
</style>
