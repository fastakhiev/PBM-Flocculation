import { createRouter, createWebHistory } from 'vue-router';

import Optimization from '../components/Optimization.vue';
import Simulation from '../components/Simulation.vue';


const routes = [
  {
    path: '/',          
    name: 'Optimization', 
    component: Optimization
  },
  {
    path: '/simulation',     
    name: 'Simulation',
    component: Simulation,
    meta: { layout: 'full-width' } 

  }
];


const router = createRouter({
  history: createWebHistory(), 
  routes,
});

export default router;