// Archivo: frontend/src/components/MetricsPanel.tsx
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

const data = [
  { name: '5 Estrellas', stars: 5, cantidad: 45, fill: '#22c55e' },
  { name: '4 Estrellas', stars: 4, cantidad: 30, fill: '#84cc16' },
  { name: '3 Estrellas', stars: 3, cantidad: 15, fill: '#eab308' },
  { name: '2 Estrellas', stars: 2, cantidad: 10, fill: '#f97316' },
  { name: '1 Estrella',  stars: 1, cantidad: 5,  fill: '#ef4444' },
];

const totalResenas = data.reduce((acc, d) => acc + d.cantidad, 0);
const promedio = (
  data.reduce((acc, d) => acc + d.cantidad * d.stars, 0) / totalResenas
).toFixed(1);
const alertas = data
  .filter((d) => d.stars <= 2)
  .reduce((acc, d) => acc + d.cantidad, 0);

export default function MetricsPanel() {
  return (
    // Sin h-full: el padre (page.tsx) no tiene altura concreta, así que h-full resolvería a 0
    <div className="w-full flex flex-col gap-6">

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
          <p className="text-sm text-blue-600 font-semibold">Total Reseñas</p>
          <p className="text-2xl font-bold text-slate-800">{totalResenas}</p>
        </div>
        <div className="bg-green-50 p-4 rounded-lg border border-green-100">
          <p className="text-sm text-green-600 font-semibold">Promedio</p>
          <p className="text-2xl font-bold text-slate-800">{promedio} / 5.0</p>
        </div>
        <div className="bg-red-50 p-4 rounded-lg border border-red-100">
          <p className="text-sm text-red-600 font-semibold">Alertas (1-2 ★)</p>
          <p className="text-2xl font-bold text-slate-800">{alertas}</p>
        </div>
      </div>

      {/* Gráfico de Barras */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 mb-3">
          Distribución de Calificaciones
        </h3>
        {/*
          ResponsiveContainer con height en píxeles explícitos: no depende del padre.
          Antes usábamos height="100%" dentro de un div h-[280px] que también
          contenía el <h3>, por lo que el chart intentaba ocupar los 280px completos
          ignorando el espacio del título y desbordaba el recuadro.
        */}
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              horizontal={false}
              stroke="#e2e8f0"
            />
            <XAxis type="number" hide />
            <YAxis
              dataKey="name"
              type="category"
              width={90}
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              cursor={{ fill: '#f8fafc' }}
              formatter={(value) => [`${value ?? 0} reseñas`, 'Cantidad']}
            />
            <Bar dataKey="cantidad" radius={[0, 4, 4, 0]} barSize={28}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

    </div>
  );
}