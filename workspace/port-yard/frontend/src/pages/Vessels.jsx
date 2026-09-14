import { useEffect, useState } from 'react'
import { api } from '../api'
import { fmt, toUTCISO } from '../utils'

const STATUS = { SCHEDULED: '计划中', BERTHED: '已靠泊', DEPARTED: '已离港' }
const toLocal = (s) => (s ? s.slice(0, 16) : '')

export default function Vessels() {
  const [list, setList] = useState([])
  const [form, setForm] = useState({ vessel_name: '', voyage: '', eta: '', etd: '' })
  const [msg, setMsg] = useState('')

  const load = () => api.get('/vessels').then(setList).catch((e) => setMsg(e.message))
  useEffect(load, [])

  const submit = async (e) => {
    e.preventDefault()
    setMsg('')
    try {
      await api.post('/vessels', { ...form, eta: toUTCISO(form.eta), etd: toUTCISO(form.etd) })
      setForm({ vessel_name: '', voyage: '', eta: '', etd: '' })
      setMsg('✅ 船期已添加')
      load()
    } catch (err) { setMsg('❌ ' + err.message) }
  }

  const setStatus = async (v, status) => {
    try { await api.patch(`/vessels/${v.id}/status?status=${status}`); load() }
    catch (e) { alert(e.message) }
  }

  return (
    <div>
      <h2>船期管理</h2>
      <form className="panel form-row" onSubmit={submit}>
        <input placeholder="船名" value={form.vessel_name} required
          onChange={(e) => setForm({ ...form, vessel_name: e.target.value })} />
        <input placeholder="航次" value={form.voyage} required
          onChange={(e) => setForm({ ...form, voyage: e.target.value })} />
        <label>ETA <input type="datetime-local" value={toLocal(form.eta)} required
          onChange={(e) => setForm({ ...form, eta: e.target.value })} /></label>
        <label>ETD <input type="datetime-local" value={toLocal(form.etd)} required
          onChange={(e) => setForm({ ...form, etd: e.target.value })} /></label>
        <button type="submit">添加船期</button>
      </form>
      {msg && <p className="msg">{msg}</p>}

      <table>
        <thead>
          <tr><th>船名</th><th>航次</th><th>预计到港</th><th>预计离港</th><th>状态</th><th>操作</th></tr>
        </thead>
        <tbody>
          {list.map((v) => (
            <tr key={v.id}>
              <td>{v.vessel_name}</td>
              <td>{v.voyage}</td>
              <td>{fmt(v.eta)}</td>
              <td>{fmt(v.etd)}</td>
              <td><span className={`tag v-${v.status}`}>{STATUS[v.status]}</span></td>
              <td>
                {v.status === 'SCHEDULED' && <button className="btn-sm" onClick={() => setStatus(v, 'BERTHED')}>靠泊</button>}
                {v.status === 'BERTHED' && <button className="btn-sm" onClick={() => setStatus(v, 'DEPARTED')}>离港</button>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
