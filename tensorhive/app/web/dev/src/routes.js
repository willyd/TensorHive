import DashView from './components/TheDash.vue'
import LoginView from './components/TheLogin.vue'
import NotFoundView from './components/404.vue'

// Import Views - Dash
import CalendarView from './components/views/ReserveResources.vue'
// Routes
const routes = [
  {
    path: '/login',
    component: LoginView
  },
  {
    path: '/',
    component: DashView,
    children: [
      {
        path: 'reserve_resources',
        alias: '',
        component: CalendarView,
        name: 'Reserve Resources',
        meta: {description: 'Calendar with reservations'}
      }
    ]
  }, {
    // not found handler
    path: '*',
    component: NotFoundView
  }
]

export default routes