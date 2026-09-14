import { useEffect, useState } from 'react'
import { api } from '../api'
import { fmt } from '../utils'


export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [overdue, setOverdue] = useState([])
  const [expiredAppts, setExpiredAppts] = useState([])

  const load = () => {
    api.get('/dashboard').then(setStats).catch(alert)
    api.get('/containers/overdue').then(setOverdue).catch(alert)
    api.get('/appointments?status=PENDING&expired=true').then(setExpiredAppts).catch(alert)
  }
  useEffect(load, [])

  if (!stats) return <p>加载中…</p>
  const cards = [
    { label: '在场箱量', value: stats.in_yard, cls: 'blue' },
    { label: '超期箱', value: stats.overdue, cls: stats.overdue ? 'red' : '' },
    { label: '待进场预约', value: stats.pending_appointments, cls: 'orange' },
    { label: '过期预约', value: stats.expired_appointments, cls: stats.expired_appointments ? 'red' : '' },
    { label: '在港船舶', value: stats.vessels_active, cls: 'blue' },
    { label: '堆场利用率', value: stats.yard_rate + '%', cls: stats.yard_rate > 85 ? 'red' : 'green' },
    { label: '今日进/出闸', value: `${stats.today_in} / ${stats.today_out}`, cls: '' },
  ]
  return (
    <div>
      <h2>运营看板</h2>
      <div className="cards">
        {cards.map((c) => (
          <div key={c.label} className={`card ${c.cls}`}>
            <div className="card-value">{c.value}</div>
            <div className="card-label">{c.label}</div>
          </div>
        ))}
      </div>

      <h3>⏰ 过期预约（已过预约时段未进场，需改期或取消）</h3>
      {expiredAppts.length === 0 ? <p className="muted">暂无过期预约</p> : (
        <table>
          <thead>
            <tr><th>箱号</th><th>计划时间</th><th>到场时段</th><th>车牌</th></tr>
          </thead>
          <tbody>
            {expiredAppts.map((a) => (
              <tr key={a.id} className="row-red">
                <td className="mono">{a.container_no}</td>
                <td>{fmt(a.planned_time)}</td>
                <td>{fmt(a.window_start)} ~ {fmt(a.window_end)}</td>
                <td>{a.truck_no}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>⚠️ 超期箱提醒（在场超过免堆存期）</h3>
      {overdue.length === 0 ? <p className="muted">暂无超期箱</p> : (
        <table>
          <thead>
            <tr><th>箱号</th><th>尺寸/箱型</th><th>堆位</th><th>货主</th><th>进场时间</th><th>在场天数</th><th>免堆期</th></tr>
          </thead>
          <tbody>
            {overdue.map((c) => (
              <tr key={c.id} className="row-red">
                <td className="mono">{c.container_no}</td>
                <td>{c.size}'{c.ctype}</td>
                <td>{c.position_code || '-'}</td>
                <td>{c.consignee}</td>
                <td>{fmt(c.in_time)}</td>
                <td>{c.days_in_yard} 天</td>
                <td>{c.free_days} 天</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
