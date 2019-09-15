import Vue from 'vue';
import Router from 'vue-router';
import Books from './components/Books.vue';
import Admin from './components/Admin.vue';
import Login from './components/Login.vue';

Vue.use(Router);

export default new Router({
  mode: 'history',
  base: process.env.BASE_URL,
  routes: [
    {
      path: '/',
      name: 'Books',
      component: Books,
    },
    {
      path: '/admin',
      name: 'Admin',
      component: Admin,
    },
    {
      path: '/login',
      name: 'Login',
      component: Login,
    },
  ],
});
