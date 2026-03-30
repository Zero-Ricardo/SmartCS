<script setup lang="ts">
import { computed, onMounted } from "vue";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import en from "element-plus/es/locale/lang/en";
import { useRoute } from "vue-router";
import { useI18n } from "@/shared/i18n";
import { useChatStore } from "@/entities/chat/model/useChatStore";
import ChatWidget from "@/widgets/chat/ChatWidget.vue";

const route = useRoute();
const store = useChatStore();
const { locale } = useI18n();
const elementLocale = computed(() => (locale.value === "zh-CN" ? zhCn : en));

onMounted(() => {
  const uid = route.query.user_id;
  if (typeof uid === "string" && uid.trim()) {
    store.setUserId(uid.trim());
  }
});
</script>

<template>
  <el-config-provider :locale="elementLocale">
    <ChatWidget embedded />
  </el-config-provider>
</template>
