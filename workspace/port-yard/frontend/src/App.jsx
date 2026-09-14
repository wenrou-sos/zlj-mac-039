import { NavLink, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Containers from './pages/Containers'
import Vessels from './pages/Vessels'
import Yard from './pages/Yard'
import Gate from './pages/Gate'
import Appointments from './pages/Appointments'

const nav = [
  { to: '/', label: '运营看板', end: true },
  { to: '/containers', label: '集装箱管理' },
  { to: '/vessels', label: '船期管理' },
  { to: '/yard', label: '堆位图' },
  { to: '/gate', label: '闸口作业' },
  { to: '/appointments', label: '进场预约' },
]

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="logo">⚓ 堆场管理系统</div>
        <nav>
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}
              className={({ isActive }) => (isActive ? 'active' : '')}>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/containers" element={<Containers />} />
          <Route path="/vessels" element={<Vessels />} />
          <Route path="/yard" element={<Yard />} />
          <Route path="/gate" element={<Gate />} />
          <Route path="/appointments" element={<Appointments />} />
        </Routes>
      </main>
    </div>
  )
}
