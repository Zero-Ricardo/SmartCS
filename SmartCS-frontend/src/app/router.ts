import { createRouter, createWebHistory } from "vue-router";
import HomePage from "@/pages/HomePage.vue";
import ChatBoxPage from "@/pages/ChatBoxPage.vue";
import AdminLogin from "@/pages/admin/AdminLogin.vue";
import AdminLayout from "@/pages/admin/AdminLayout.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      component: HomePage
    },
    {
      path: "/chat-box",
      component: ChatBoxPage
    },
    {
      path: "/admin/login",
      component: AdminLogin
    },
    {
      path: "/admin",
      component: AdminLayout,
      children: [
        {
          path: "knowledge",
          component: () => import("@/pages/admin/KnowledgeManager.vue")
        },
        {
          path: "",
          redirect: "/admin/knowledge"
        }
      ]
    }
  ]
});
