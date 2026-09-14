import { useEffect, useState } from 'react'
import { api } from '../api'
import { fmt } from '../utils'

const STATUS = { BOOKED: '已预约', IN_YARD: '在场', OUT: '已出场' }

export default function Containers() {
  const [list, setList] = useState([])
  const [vessels, setVessels] = useState([])
  const [filter, setFilter] = useState({ status: '', q: '' })
  const [form, setForm] = useState({
    container_no: '', size: '40', ctype: 'GP', vessel_id: '',
    weight_t: '', consignee: '', free_days: 7,
  })
  const [msg, setMsg] = useState('')
  const [editing, setEditing] = useState(null)

  const load = () => {
    const p = new URLSearchParams()
    if (filter.status) p.set('status', filter.status)
    if (filter.q) p.set('q', filter.q)
    api.get('/containers?' + p).then(setList).catch((e) => setMsg(e.message))
  }
  useEffect(load, [filter])
  useEffect(() => { api.get('/vessels').then(setVessels) }, [])

  const submit = async (e) => {
    e.preventDefault()
    setMsg('')
    try {
      await api.post('/containers', {
        ...form,
        vessel_id: form.vessel_id ? Number(form.vessel_id) : null,
        weight_t: Number(form.weight_t) || 0,
        free_days: Number(form.free_days),
      })
      setForm({ ...form, container_no: '', weight_t: '', consignee: '' })
      setMsg('✅ 创建成功')
      load()
    } catch (err) { setMsg('❌ ' + err.message) }
  }

  const toggleHold = async (c) => {
    try {
      await api.patch(`/containers/${c.id}/hold?hold=${!c.has_hold}`)
      load()
    } catch (e) { alert(e.message) }
  }

  const startEdit = (c) => {
    setMsg('')
    setEditing({
      id: c.id, container_no: c.container_no, size: c.size, ctype: c.ctype,
      vessel_id: c.vessel_id || '', consignee: c.consignee, free_days: c.free_days,
    })
  }

  const saveEdit = async (e) => {
    e.preventDefault()
    setMsg('')
    try {
      await api.patch(`/containers/${editing.id}`, {
        size: editing.size,
        ctype: editing.ctype,
        vessel_id: editing.vessel_id ? Number(editing.vessel_id) : null,
        consignee: editing.consignee,
        free_days: Number(editing.free_days),
      })
      setEditing(null)
      setMsg('✅ 已保存，超期判定已按新免堆天数重算')
      load()
    } catch (err) { setMsg('❌ ' + err.message) }
  }

  return (
    <div>
      <h2>集装箱管理</h2>
      <form className="panel form-row" onSubmit={submit}>
        <input placeholder="箱号 (如 MSKU1234567)" value={form.container_no}
          onChange={(e) => setForm({ ...form, container_no: e.target.value.toUpperCase() })}
          maxLength={11} required />
        <select value={form.size} onChange={(e) => setForm({ ...form, size: e.target.value })}>
          <option value="20">20尺</option><option value="40">40尺</option><option value="45">45尺</option>
        </select>
        <select value={form.ctype} onChange={(e) => setForm({ ...form, ctype: e.target.value })}>
          <option value="GP">普通箱</option><option value="HC">高箱</option><option value="RF">冷藏箱</option>
        </select>
        <select value={form.vessel_id} onChange={(e) => setForm({ ...form, vessel_id: e.target.value })}>
          <option value="">关联船期(可选)</option>
          {vessels.map((v) => <option key={v.id} value={v.id}>{v.vessel_name} / {v.voyage}</option>)}
        </select>
        <input placeholder="重量(吨)" type="number" step="0.1" value={form.weight_t}
          onChange={(e) => setForm({ ...form, weight_t: e.target.value })} />
        <input placeholder="货主" value={form.consignee}
          onChange={(e) => setForm({ ...form, consignee: e.target.value })} />
        <input placeholder="免堆天数" type="number" value={form.free_days}
          onChange={(e) => setForm({ ...form, free_days: e.target.value })} style={{ width: 90 }} />
        <button type="submit">登记箱</button>
      </form>
      {msg && <p className="msg">{msg}</p>}

      {editing && (
        <form className="panel form-row" onSubmit={saveEdit}>
          <span className="mono" style={{ alignSelf: 'center' }}>{editing.container_no}</span>
          <select value={editing.size} onChange={(e) => setEditing({ ...editing, size: e.target.value })}>
            <option value="20">20尺</option><option value="40">40尺</option><option value="45">45尺</option>
          </select>
          <select value={editing.ctype} onChange={(e) => setEditing({ ...editing, ctype: e.target.value })}>
            <option value="GP">普通箱</option><option value="HC">高箱</option><option value="RF">冷藏箱</option>
          </select>
          <select value={editing.vessel_id} onChange={(e) => setEditing({ ...editing, vessel_id: e.target.value })}>
            <option value="">关联船期(可选)</option>
            {vessels.map((v) => <option key={v.id} value={v.id}>{v.vessel_name} / {v.voyage}</option>)}
          </select>
          <input placeholder="货主" value={editing.consignee}
            onChange={(e) => setEditing({ ...editing, consignee: e.target.value })} />
          <input placeholder="免堆天数" type="number" min="0" value={editing.free_days}
            onChange={(e) => setEditing({ ...editing, free_days: e.target.value })} style={{ width: 90 }} required />
          <button type="submit">保存</button>
          <button type="button" className="btn-sm" onClick={() => setEditing(null)}>取消</button>
        </form>
      )}
      {editing && <p className="muted">箱号与进出场时间不可修改；保存后超期标记、看板超期箱数与超期清单按新免堆天数重算。</p>}

      <div className="toolbar">
        <select value={filter.status} onChange={(e) => setFilter({ ...filter, status: e.target.value })}>
          <option value="">全部状态</option>
          <option value="BOOKED">已预约</option>
          <option value="IN_YARD">在场</option>
          <option value="OUT">已出场</option>
        </select>
        <input placeholder="搜索箱号…" value={filter.q}
          onChange={(e) => setFilter({ ...filter, q: e.target.value })} />
      </div>

      <table>
        <thead>
          <tr><th>箱号</th><th>尺寸/箱型</th><th>状态</th><th>船名/航次</th><th>堆位</th><th>货主</th><th>进场时间</th><th>在场天数</th><th>扣箱</th><th>操作</th></tr>
        </thead>
        <tbody>
          {list.map((c) => (
            <tr key={c.id} className={c.overdue ? 'row-red' : ''}>
              <td className="mono">{c.container_no}</td>
              <td>{c.size}'{c.ctype}</td>
              <td><span className={`tag s-${c.status}`}>{STATUS[c.status]}</span>
                {c.overdue && <span className="tag s-over">超期</span>}</td>
              <td>{c.vessel_name || '-'}</td>
              <td>{c.position_code || '-'}</td>
              <td>{c.consignee}</td>
              <td>{fmt(c.in_time)}</td>
              <td>{c.days_in_yard != null ? c.days_in_yard + ' 天' : '-'}</td>
              <td>{c.has_hold ? '🔒' : '-'}</td>
              <td>
                <button className="btn-sm" onClick={() => startEdit(c)}>编辑</button>
                <button className="btn-sm" onClick={() => toggleHold(c)}>
                  {c.has_hold ? '解除扣箱' : '扣箱'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
