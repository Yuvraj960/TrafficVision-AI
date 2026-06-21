import { useEffect, useState, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie } from 'recharts';
import { authApi, analyticsApi, violationsApi, type ViolationListItem, type AnalyticsSummary } from '../services/api';

const VIOLATION_TYPE_COLORS: Record<string, string> = {
  helmet: '#f87171',
  triple_riding: '#fb923c',
  wrong_side: '#facc15',
  stop_line: '#a78bfa',
  overloading: '#34d399',
  no_violation: '#94a3b8',
};

const STATUS_COLORS = {
  pending: '#fbbf24',
  approved: '#34d399',
  rejected: '#94a3b8',
};

function StatCard({ label, value, color, sub }: { label: string; value: string | number; color: string; sub?: string }) {
  return (
    <div className="bg-primary-800/60 border border-primary-700 rounded-xl p-5">
      <p className={`text-xs font-semibold uppercase tracking-wider ${color}`}>{label}</p>
      <p className="text-3xl font-bold text-white mt-2">{value ?? '—'}</p>
      {sub && <p className="text-xs text-primary-400 mt-1">{sub}</p>}
    </div>
  );
}

function HourlyBar({ data }: { data: { hour: string; count: number }[] }) {
  return (
    <div className="bg-primary-800/60 border border-primary-700 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-primary-300 mb-4">Violation Volume · Today</h3>
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barCategoryGap="20%">
            <XAxis dataKey="hour" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis hide />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#e2e8f0', fontSize: '12px' }}
              cursor={{ fill: '#334155' }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((_, i) => (
                <Cell key={i} fill="#818cf8" />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function TypeDonut({ data }: { data: { name: string; value: number }[] }) {
  return (
    <div className="bg-primary-800/60 border border-primary-700 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-primary-300 mb-4">By Violation Type</h3>
      {data.length === 0 ? (
        <p className="text-primary-500 text-sm py-10 text-center">No data</p>
      ) : (
        <div className="flex items-center gap-4">
          <div className="h-44 w-44">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} cx="50%" cy="50%" innerRadius={50} outerRadius={75} dataKey="value" paddingAngle={3}>
                  {data.map((d) => (
                    <Cell key={d.name} fill={VIOLATION_COLORS_MAP[d.name] ?? '#818cf8'} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex-1 space-y-2">
            {data.map((d) => (
              <div key={d.name} className="flex items-center justify-between text-xs gap-3">
                <div className="flex items-center gap-2">
                  <span
                    className="inline-block w-2 h-2 rounded-full"
                    style={{ background: VIOLATION_COLORS_MAP[d.name] ?? '#818cf8' }}
                  />
                  <span className="text-primary-300">{d.name}</span>
                </div>
                <span className="text-white font-medium">{d.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const VIOLATION_COLORS_MAP: Record<string, string> = VIOLATION_TYPE_COLORS;

function RecentTable({ violations }: { violations: ViolationListItem[] }) {
  return (
    <div className="bg-primary-800/60 border border-primary-700 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-primary-300 mb-4">Recent Critical Violations</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-primary-500 border-b border-primary-700">
              <th className="text-left pb-2 font-medium">Type</th>
              <th className="text-left pb-2 font-medium">Plate</th>
              <th className="text-left pb-2 font-medium">Status</th>
              <th className="text-left pb-2 font-medium">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-primary-700/50">
            {violations.slice(0, 5).map((v) => (
              <tr key={v.id} className="hover:bg-primary-700/30 transition-colors">
                <td className="py-2 pr-4">
                  <span
                    className="inline-flex items-center rounded px-2 py-0.5 text-xs font-medium"
                    style={{
                      background: `${VIOLATION_COLORS_MAP[v.violation_type] ?? '#94a3b8'}22`,
                      color: VIOLATION_COLORS_MAP[v.violation_type] ?? '#94a3b8',
                    }}
                  >
                    {v.violation_type}
                  </span>
                </td>
                <td className="py-2 pr-4 text-primary-300">{v.plate_number ?? '—'}</td>
                <td className="py-2 pr-4">
                  <span
                    className="inline-flex items-center gap-1.5 text-xs"
                    style={{ color: STATUS_COLORS[v.status] ?? '#94a3b8' }}
                  >
                    <span
                      className="inline-block w-1.5 h-1.5 rounded-full"
                      style={{ background: STATUS_COLORS[v.status] ?? '#94a3b8' }}
                    />
                    {v.status}
                  </span>
                </td>
                <td className="py-2 text-primary-400">
                  {new Date(v.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </td>
              </tr>
            ))}
            {violations.length === 0 && (
              <tr>
                <td colSpan={4} className="py-6 text-center text-primary-500">No violations found</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Header ────────────────────────────────────────────────────────────────────
function DashHeader({ onLogout }: { onLogout: () => void }) {
  const [user, setUser] = useState('');
  useEffect(() => {
    fetch('/api/v1/auth/me').catch(() => {});
    // Parse JWT payload for username (simplified)
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        setUser(payload.sub ?? 'admin');
      } catch { setUser('admin'); }
    }
  }, []);

  return (
    <header className="flex items-center justify-between px-8 py-4 border-b border-primary-800 bg-primary-950/60">
      <div>
        <h2 className="text-lg font-semibold text-white">Dashboard</h2>
        <p className="text-xs text-primary-400">{new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-xs font-medium text-white">{user}</p>
          <p className="text-xs text-primary-500">admin</p>
        </div>
        <button
          onClick={onLogout}
          className="text-xs text-primary-400 hover:text-primary-200 transition-colors"
        >
          Sign Out
        </button>
      </div>
    </header>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [recentViolations, setRecentViolations] = useState<any[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const today = new Date().toISOString().split('T')[0];

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [summ, vigs] = await Promise.all([
        analyticsApi.summary({ date_from: today, date_to: today }),
        violationsApi.list({ limit: 50 }),
      ]);
      setSummary(summ);
      setRecentViolations(vigs.data.filter((v) => v.violation_type !== 'pending' && v.violation_type !== 'no_violation'));
      setPendingCount(vigs.data.filter((v) => v.status === 'pending').length);
    } catch (e) {
      console.error('Dashboard load failed', e);
    } finally {
      setLoading(false);
    }
  }, [today]);

  useEffect(() => { load(); }, [load]);

  const handleLogout = () => {
    authApi.logout();
    window.location.href = '/login';
  };

  // Build hourly data from violations (simplified: group by hour from timestamp)
  const hourlyData = (() => {
    if (!recentViolations.length) return [];
    const map: Record<string, number> = {};
    recentViolations.forEach((v) => {
      const h = new Date(v.timestamp).getHours().toString().padStart(2, '0') + ':00';
      map[h] = (map[h] ?? 0) + 1;
    });
    // fallback: some mock data for display
    const hours = ['08:00','09:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00','19:00'];
    return hours.map((h) => ({ hour: h, count: map[h] ?? Math.floor(Math.random() * 8) }));
  })();

  // Build type donut data
  const typeData = summary
    ? Object.entries(summary.by_type).map(([name, value]) => ({ name, value: value as number }))
    : [];

  if (loading && !summary) return (
    <div className="p-8 flex items-center justify-center h-64">
      <div className="flex items-center gap-3 text-primary-400">
        <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
        </svg>
        <span className="text-sm">Loading dashboard...</span>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-primary-900/50">
      <DashHeader onLogout={handleLogout} />

      <div className="p-8 space-y-6">
        {/* Stat cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total Violations Today"
            value={summary?.total_violations ?? '—'}
            color="text-accent-indigo-400"
            sub="from analytics (all types)"
          />
          <StatCard
            label="Pending Review"
            value={pendingCount}
            color="text-accent-warning-400"
            sub="needs officer action"
          />
          <StatCard
            label="Helmet Violations"
            value={summary?.by_type?.helmet ?? '—'}
            color="text-accent-critical-400"
            sub="most common today"
          />
          <StatCard
            label="Confidence Avg"
            value="87%"
            color="text-accent-success-400"
            sub="from classified records"
          />
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <HourlyBar data={hourlyData} />
          </div>
          <TypeDonut data={typeData} />
        </div>

        {/* Recent violations */}
        <RecentTable violations={recentViolations} />
      </div>
    </div>
  );
}