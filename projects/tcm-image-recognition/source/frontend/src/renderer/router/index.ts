import { createRouter, createWebHistory, type Router,createWebHashHistory } from "vue-router";

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "index",
      component: () => import("@/renderer/views/Index.vue"),
      meta: { requiresAuth: true },
      children: [
        {
          path: "history",
          name: "history",
          component: () => import("@/renderer/views/History.vue"),
        },
        {
          //用户管理界面
          path: 'usermanagement',
          name: 'UserManagement',
          component: () => import('@/renderer/views/UserManagement.vue'),
          meta: { requiresAuth: true, requiresAdmin: true }, // 增加管理员权限要求
          beforeEnter: (to, from, next) => {
            const userData = localStorage.getItem('user');
            if (userData) {
              const user = JSON.parse(userData);
              const isAdmin = user.roles?.some((role: any) => role.roleKey === 'admin');
              if (isAdmin) {
                next(); // 是管理员，放行
              } else {
                alert('无权访问：此页面仅限管理员查看。');
                next(false); // 不是管理员，阻止导航
              }
            } else {
              // 如果没有用户信息，全局守卫会处理跳转到登录页
              next({ name: 'login' });
            }
          }
        },
        {
          //配置个人信息界面
          path: 'userinfo',
          name: 'UserInfo',
          component: () => import('@/renderer/views/UserInfo.vue'),
          meta: { requiresAuth: true }  // 需要登录验证
        }
      ],
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/renderer/views/LoginPlatform.vue"),
    },
    {
      path: "/register",
      name: "register",
      component: () => import("@/renderer/views/Register.vue"),
    }
  ],
});

// 全局前置守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token');

  // 情况1: 访问的是登录页
  if (to.name === 'login') {
    if (token) {
      // 如果已登录，还想去登录页，则重定向到首页
      next({ name: 'index' });
    } else {
      // 如果未登录，正常访问登录页
      next();
    }
  } 
  // 情况2: 访问的是需要授权的页面
  else if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!token) {
      // 如果未登录，重定向到登录页
      next({ name: 'login' });
    } else {
      // 如果已登录，正常访问
      next();
    }
  } 
  // 情况3: 访问其他所有页面 (例如注册页)
  else {
    next();
  }
});

//获取路由信息
export const getRouter = (): Router => {
	return router
}

export default router;