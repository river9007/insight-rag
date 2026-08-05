"use client";

import { useCallback, useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from 'recharts';
import { Loader2 } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';

interface DistributionItem {
  rating: number;
  cantidad: number;
}

// 👈 Ajustado para coincidir exactamente con las llaves que devuelve FastAPI
interface TimeseriesItem {
  fecha: string;
  promedio: number;
  cantidad: number;
}

interface MetricsData {
  total_resenas: number;
  promedio: number;
  alertas: number;
  distribution: DistributionItem[];
  timeseries?: TimeseriesItem[]; // 👈 Renombrado de timeline a timeseries
  available_products: string[];
  filtered_by: string | null;
}

const RATING_COLORS: Record<number, string> = {
  5: '#22c55e',
  4: '#84cc16',
  3: '#eab308',
  2: '#f97316',
  1: '#ef4444',
};

interface MetricsPanelProps {
  refreshTrigger?: number;
}

export default function MetricsPanel({ refreshTrigger = 0 }: MetricsPanelProps) {
  const [selectedProduct, setSelectedProduct] = useState<string>('');
  const [data, setData] = useState<MetricsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      const url = new URL(`${API_URL}/metrics`);
      if (selectedProduct) {
        url.searchParams.set('product_id', selectedProduct);
      }

      const response = await fetch(url.toString(), {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error(`Error del servidor: ${response.status}`);
      }

      const json: MetricsData = await response.json();
      setData(json);
    } catch (err) {
      console.error('Error al obtener métricas:', err);
      setError('No se pudieron cargar las métricas. Intenta recargar la página.');
    } finally {
      setIsLoading(false);
    }
  }, [selectedProduct]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics, refreshTrigger]);

  if (isLoading && !data) {
    return (
      <div className="flex items-center justify-center h-40 gap-2 text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span className="text-sm">Cargando métricas...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-4">
        {error}
      </div>
    );
  }

  if (!data || data.total_resenas === 0) {
    return (
      <div className="flex flex-col gap-4">
        {data && data.available_products.length > 0 && (
          <ProductFilter
            products={data.available_products}
            selected={selectedProduct}
            onChange={setSelectedProduct}
            isLoading={isLoading}
          />
        )}
        <div className="text-center text-gray-400 text-sm py-10">
          {selectedProduct
            ? `No hay reseñas para "${selectedProduct}" todavía.`
            : 'Aún no hay reseñas ingeridas. Sube un PDF para comenzar.'}
        </div>
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Filtro por producto */}
      {data.available_products.length > 0 && (
        <ProductFilter
          products={data.available_products}
          selected={selectedProduct}
          onChange={setSelectedProduct}
          isLoading={isLoading}
        />
      )}

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
          <p className="text-sm text-blue-600 font-semibold">Total Reseñas</p>
          <p className="text-2xl font-bold text-slate-800">{data.total_resenas}</p>
        </div>
        <div className="bg-green-50 p-4 rounded-lg border border-green-100">
          <p className="text-sm text-green-600 font-semibold">Promedio</p>
          <p className="text-2xl font-bold text-slate-800">{data.promedio} / 5.0</p>
        </div>
        <div className="bg-red-50 p-4 rounded-lg border border-red-100">
          <p className="text-sm text-red-600 font-semibold">Alertas (1-2 ★)</p>
          <p className="text-2xl font-bold text-slate-800">{data.alertas}</p>
        </div>
      </div>

      {/* Gráfico de Tendencia Temporal (Eje X = Fecha, Eje Y = Calificación / Volumen) */}
      {/* 👈 Modificamos la validación para usar data.timeseries */}
      {data.timeseries && data.timeseries.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-500 mb-3">
            Evolución Temporal de Calificaciones
          </h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart
              data={data.timeseries}
              margin={{ top: 10, right: 30, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="fecha" // 👈 Alineado al JSON de FastAPI
                fontSize={12}
                tickLine={false}
                stroke="#64748b"
              />
              <YAxis
                yAxisId="left"
                domain={[1, 5]}
                fontSize={12}
                tickLine={false}
                stroke="#22c55e"
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                fontSize={12}
                tickLine={false}
                stroke="#3b82f6"
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', borderColor: '#e2e8f0' }}
                formatter={(value: any, name: any) => [
                  name === 'Promedio' ? `${value} ★` : `${value} reseñas`,
                  name
                ]}
              />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="promedio"
                name="Promedio"
                stroke="#22c55e"
                strokeWidth={2}
                dot={{ r: 4, fill: '#22c55e' }}
                activeDot={{ r: 6 }}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="cantidad" // 👈 Alineado al JSON de FastAPI
                name="Total Reseñas"
                stroke="#3b82f6"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={{ r: 4, fill: '#3b82f6' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Gráfico de Barras */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 mb-3">
          Distribución de Calificaciones
        </h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={data.distribution.map((d) => ({
              name: `${d.rating} Estrella${d.rating !== 1 ? 's' : ''}`,
              cantidad: d.cantidad,
              rating: d.rating,
            }))}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
            <XAxis type="number" hide allowDecimals={false} />
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
              {data.distribution.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={RATING_COLORS[entry.rating]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ProductFilter({
  products,
  selected,
  onChange,
  isLoading,
}: {
  products: string[];
  selected: string;
  onChange: (value: string) => void;
  isLoading: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-sm text-gray-500 font-medium">Producto:</label>
      <select
        value={selected}
        onChange={(e) => onChange(e.target.value)}
        className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">Todos los productos</option>
        {products.map((pid) => (
          <option key={pid} value={pid}>{pid}</option>
        ))}
      </select>
      {isLoading && <Loader2 className="w-4 h-4 animate-spin text-blue-500" />}
    </div>
  );
}