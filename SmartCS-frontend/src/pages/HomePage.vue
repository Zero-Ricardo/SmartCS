<script setup lang="ts">
import ChatWidget from "@/widgets/chat/ChatWidget.vue";
</script>

<template>
  <main class="home-page">
    <section class="hero">
      <h1>淘课网企业培训服务</h1>
      <p>公开课、内训课、讲师匹配与方案咨询，一站式为企业提供培训支持。</p>
      <el-button type="primary" size="large">查看课程</el-button>
    </section>
    <section class="grid">
      <article class="panel">
        <h2>热门专题</h2>
        <p>管理提升、销售增长、数字化转型与组织人才发展。</p>
      </article>
      <article class="panel">
        <h2>企业内训</h2>
        <p>支持按行业、岗位和预算快速生成内训建议与报价参考。</p>
      </article>
      <article class="panel">
        <h2>讲师合作</h2>
        <p>匹配认证讲师，查看履历、擅长主题与历史评价。</p>
      </article>
    </section>
    <ChatWidget />
  </main>
</template>
