import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", name: "Dashboard", component: () => import("./pages/Dashboard.vue") },
  { path: "/new", name: "NewRun", component: () => import("./pages/NewRun.vue") },
  {
    path: "/runs/:name",
    name: "RunDetail",
    component: () => import("./pages/RunDetail.vue"),
    props: true,
  },
];

export const router = createRouter({
  history: createWebHistory("/release/"),
  routes,
});

// Reuse the standard Frappe session; bounce guests to the login page.
router.beforeEach((to, from, next) => {
  const user = window.boot?.session_user;
  if (!user || user === "Guest") {
    window.location.href = "/login?redirect-to=/release";
    return;
  }
  next();
});
