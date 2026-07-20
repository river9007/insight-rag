// Archivo: frontend/src/components/MetricsPanel.tsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// Datos simulados (En la Fase 5 esto vendría de FastAPI mediante un endpoint SQL de agregación)
const data = [
  { name: '5 Estrellas', cantidad: 45, fill: '#22c55e' }, // Verde
  { name: '4 Estrellas', cantidad: 30, fill: '#84cc16' }, // Verde claro
  { name: '3 Estrellas', cantidad: 15, fill: '#eab308' }, // Amarillo
  { name: '2 Estrellas', cantidad: 10, fill: '#f97316' }, // Naranja
  { name: '1 Estrella',  cantidad: 5,  fill: '#ef4444' }, // Rojo
];

export default function MetricsPanel() {
  return (
    <div className="w-full h-full flex flex-col gap-6">
      
      {/* Tarjetas de KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
          <p className="text-sm text-blue-600 font-semibold">Total Reseñas</p>
          <p className="text-2xl font-bold text-slate-800">105</p>
        </div>
        <div className="bg-green-50 p-4 rounded-lg border border-green-100">
          <p className="text-sm text-green-600 font-semibold">Promedio</p>
          <p className="text-2xl font-bold text-slate-800">4.2 / 5.0</p>
        </div>
        <div className="bg-red-50 p-4 rounded-lg border border-red-100">
          <p className="text-sm text-red-600 font-semibold">Alertas (1-2 Estrellas)</p>
          <p className="text-2xl font-bold text-slate-800">15</p>
        </div>
      </div>

      {/* Gráfico de Barras */}
      <div className="flex-1 min-h-[300px] mt-4">
        <h3 className="text-sm font-semibold text-gray-500 mb-4">Distribución de Calificaciones</h3>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
            <XAxis type="number" hide />
            <YAxis dataKey="name" type="category" width={80} fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip cursor={{ fill: '#f8fafc' }} />
            <Bar dataKey="cantidad" radius={[0, 4, 4, 0]} barSize={30} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      
    </div>
  );
}