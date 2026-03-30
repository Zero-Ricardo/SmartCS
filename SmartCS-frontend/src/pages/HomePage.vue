<script setup lang="ts">
import ChatWidget from "@/widgets/chat/ChatWidget.vue";
</script>

<template>
  <main class="home-page">
    <section class="hero">
      <h1>培训宝智能客服</h1>
      <p>围绕企业学习全流程，提供培训管理、在线学习、考试测评与运营支持的智能咨询服务。</p>
      <el-button type="primary" size="large">立即咨询方案</el-button>
    </section>
    <section class="grid">
      <article class="panel">
        <h2>培训管理数字化</h2>
        <p>覆盖报名、签到、评估与数据归档，帮助培训管理流程标准化、可追踪。</p>
      </article>
      <article class="panel">
        <h2>学习与考试一体化</h2>
        <p>支持在线学习、考试测评与学习路径设计，提升培训触达效率与落地效果。</p>
      </article>
      <article class="panel">
        <h2>运营与服务支持</h2>
        <p>通过智能客服快速获取实施建议、答疑支持与业务场景配置思路。</p>
      </article>
    </section>
    <ChatWidget />
  </main>
</template>
