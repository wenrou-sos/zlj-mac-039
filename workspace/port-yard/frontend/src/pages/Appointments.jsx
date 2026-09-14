import { useEffect, useState } from 'react'
import { api } from '../api'
import { fmt, fmtShort, toUTCISO, toLocalInput } from '../utils'

const STATUS = { PENDING: '待进场', COMPLETED: '已完成', CANCELLED: '已取消' }
const TABS = [
  { key: '', label: '全部' },
  { key: 'active', label: '待进场' },
  { key: 'expired', label: '已过期' },
  { key: 'COMPLETED', label: '已完成' },
  { key: 'CANCELLED', label: '已取消' },
]

export default function Appointments() {
  const [list, setList] = useState([])
  const [vessels, setVessels] = useState([])
  const [tab, setTab] = useState('')
  const [form, setForm] = useState({
    container_no: '', vessel_id: '', planned_time: '', tolerance_hours: 2, truck_no: '',
    size: '40', ctype: 'GP', consignee: '', free_days: 7,
  })
  const [archiveHint, setArchiveHint] = useState('')
  const [resched, setResched] = useState(null) // {id, planned_time, tolerance_hours}
  const [msg, setMsg] = useState('')

  const load = () => {
    let path = '/appointments'
    if (tab === 'expired') path += '?status=PENDING&expired=true'
    else if (tab === 'active') path += '?status=PENDING&expired=false'
    else if (tab) path += `?status=${tab}`
    api.get(path).then(setList).catch((e) => setMsg(e.message))
  }
  useEffect(load, [tab])
  useEffect(() => { api.get('/vessels').then(setVessels) }, [])

  // 箱号输满后查箱档案: 已建档则回填供核对修正, 未建档提示将按所填信息自动建档
  useEffect(() => {
    const no = form.container_no
    if (no.length !== 11) { setArchiveHint(''); return }
    let stale = false
    api.get('/containers?q=' + no).then((list) => {
      if (stale) return
      const c = list.find((x) => x.container_no === no)
      if (c) {
        setForm((f) => (f.container_no === no ? {
          ...f, size: c.size || '40', ctype: c.ctype || 'GP',
          consignee: c.consignee, free_days: c.free_days,
          vessel_id: f.vessel_id || (c.vessel_id || ''),
        } : f))
        setArchiveHint(c.status === 'IN_YARD'
          ? '⚠️ 该箱已在场内，无需预约进场'
          : '📋 该箱已建档，档案信息已回填，可核对修正后提交')
      } else {
        setArchiveHint('🆕 该箱未建档，提交预约时将按所填尺寸/箱型/货主/免堆期自动建档')
      }
    }).catch(() => {})
    return () => { stale = true }
  }, [form.container_no])

  const submit = async (e) => {
    e.preventDefault()
    setMsg('')
    try {
      await api.post('/appointments', {
        ...form,
        planned_time: toUTCISO(form.planned_time),
        vessel_id: form.vessel_id ? Number(form.vessel_id) : null,
        tolerance_hours: Number(form.tolerance_hours),
        free_days: Number(form.free_days),
      })
      setForm({
        container_no: '', vessel_id: '', planned_time: '', tolerance_hours: 2, truck_no: '',
        size: '40', ctype: 'GP', consignee: '', free_days: 7,
      })
      setArchiveHint('')
      setMsg('✅ 预约已创建（箱档案信息已同步）')
      load()
    } catch (err) { setMsg('❌ ' + err.message) }
  }

  const cancel = async (a) => {
    try { await api.patch(`/appointments/${a.id}/cancel`); load() }
    catch (e) { alert(e.message) }
  }

  const doReschedule = async () => {
    try {
      await api.patch(`/appointments/${resched.id}/reschedule`, {
        planned_time: toUTCISO(resched.planned_time),
        tolerance_hours: Number(resched.tolerance_hours),
      })
      setResched(null)
      setMsg('✅ 改期成功，原时段已释放')
      load()
    } catch (e) { alert(e.message) }
  }

  return (
    <div>
      <h2>进场预约</h2>
      <form className="panel form-row" onSubmit={submit}>
        <input placeholder="箱号 (如 MSKU1234567)" value={form.container_no} required maxLength={11}
          onChange={(e) => setForm({ ...form, container_no: e.target.value.toUpperCase() })} />
        <select value={form.vessel_id} onChange={(e) => setForm({ ...form, vessel_id: e.target.value })}>
          <option value="">关联船期(可选)</option>
          {vessels.map((v) => <option key={v.id} value={v.id}>{v.vessel_name} / {v.voyage}</option>)}
        </select>
        <label>计划进场 <input type="datetime-local" value={form.planned_time} required
          onChange={(e) => setForm({ ...form, planned_time: e.target.value })} /></label>
        <label>容差(小时) <input type="number" min="1" max="24" value={form.tolerance_hours} required
          onChange={(e) => setForm({ ...form, tolerance_hours: e.target.value })} style={{ width: 70 }} /></label>
        <input placeholder="车牌号" value={form.truck_no}
          onChange={(e) => setForm({ ...form, truck_no: e.target.value })} />
        <select value={form.size} title="尺寸" onChange={(e) => setForm({ ...form, size: e.target.value })}>
          <option value="20">20尺</option><option value="40">40尺</option><option value="45">45尺</option>
        </select>
        <select value={form.ctype} title="箱型" onChange={(e) => setForm({ ...form, ctype: e.target.value })}>
          <option value="GP">普通箱</option><option value="HC">高箱</option><option value="RF">冷藏箱</option>
        </select>
        <input placeholder="货主" value={form.consignee}
          onChange={(e) => setForm({ ...form, consignee: e.target.value })} />
        <input placeholder="免堆天数" type="number" min="0" value={form.free_days} required
          onChange={(e) => setForm({ ...form, free_days: e.target.value })} style={{ width: 90 }} />
        <button type="submit">创建预约</button>
      </form>
      {archiveHint && <p className="msg">{archiveHint}</p>}
      {msg && <p className="msg">{msg}</p>}

      <div className="toolbar">
        {TABS.map((t) => (
          <button key={t.key} className={`block-btn ${tab === t.key ? 'active' : ''}`}
            onClick={() => setTab(t.key)}>{t.label}</button>
        ))}
      </div>

      <table>
        <thead>
          <tr><th>箱号</th><th>计划时间</th><th>到场时段</th><th>车牌</th><th>状态</th><th>操作</th></tr>
        </thead>
        <tbody>
          {list.map((a) => (
            <tr key={a.id} className={a.is_expired ? 'row-red' : ''}>
              <td className="mono">{a.container_no}</td>
              <td>{fmt(a.planned_time)}</td>
              <td>{fmtShort(a.window_start)} ~ {fmtShort(a.window_end)}</td>
              <td>{a.truck_no}</td>
              <td>
                <span className={`tag a-${a.status}`}>{STATUS[a.status]}</span>
                {a.is_expired && <span className="tag s-over">已过期</span>}
              </td>
              <td>
                {a.status === 'PENDING' && (
                  resched?.id === a.id ? (
                    <span className="form-row">
                      <input type="datetime-local" value={resched.planned_time}
                        onChange={(e) => setResched({ ...resched, planned_time: e.target.value })} />
                      <input type="number" min="1" max="24" value={resched.tolerance_hours} title="容差(小时)"
                        onChange={(e) => setResched({ ...resched, tolerance_hours: e.target.value })} style={{ width: 60 }} />
                      <button className="btn-sm" onClick={doReschedule}>确认</button>
                      <button className="btn-sm" onClick={() => setResched(null)}>取消</button>
                    </span>
                  ) : (
                    <>
                      <button className="btn-sm" onClick={() => setResched({
                        id: a.id, planned_time: toLocalInput(a.planned_time),
                        tolerance_hours: a.tolerance_hours,
                      })}>改期</button>{' '}
                      <button className="btn-sm" onClick={() => cancel(a)}>取消预约</button>
                    </>
                  )
                )}
              </td>
            </tr>
          ))}
          {list.length === 0 && <tr><td colSpan={6} className="muted">暂无记录</td></tr>}
        </tbody>
      </table>
    </div>
  )
}
