import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/Home',
      name: 'Home',
      component: Home,
    },
    {
      path: '/QueryUser',
      name: 'QueryUser',
      component: () => import('../views/QueryUser.vue') // 动态导入
    },
    {
      path: '/BookReturn',
      name: 'BookReturn',
      component: () => import('../views/BookReturn.vue')
    },
    {
      path: '/book/:id',
      name: 'BookDetail',
      component: () => import('../views/BookDetail.vue'),
      props: true
    },
    {
      path: '/create_book',
      name: 'creat_book',
      component: () => import('../views/photo.vue'),
      props: true
    },
    {
      path: '/BorrowBook',
      name: 'BorrowBook',
      component: () => import('../views/BorrowBook.vue')
    }
  ],
})

export default router
