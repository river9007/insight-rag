// Archivo: components/MetricsPanel.tsx
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
  Legend,
  PieChart,
  Pie,
} from 'recharts';
import { Loader2, Tag, ThumbsUp, MessageSquare, AlertTriangle } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';

interface DistributionItem {
  rating: number;
  cantidad: number;
}

interface TimeseriesItem {
  fecha: string;
  promedio: number;
  cantidad: number;
}

interface SentimentDistribution {
  POSITIVE: number;
  NEUTRAL: number;
  NEGATIVE: number;
}

interface CategoryItem {
  category: string;
  count: number;
  avg_rating: number;
}

interface AspectTagItem {
  tag: string;
  count: number;
}

interface MetricsData {
  total_resenas: number;
  promedio: number;
  alertas: number;
  distribution: DistributionItem[];
  timeseries?: TimeseriesItem[];
  available_products: string[];
  filtered_by: string | null;
  sentiment_distribution?: SentimentDistribution;
  top_categories?: CategoryItem[];
  top_aspect_tags?: AspectTagItem[];
}

const RATING_COLORS: Record<number, string> = {
  5: '#22c55e',
  4: '#84cc16',
  3: '#eab308',
  2: '#f97316',
  1: '#ef4444',
};

const SENTIMENT_COLORS = {
  POSITIVE: '#22c55e',
  NEUTRAL: '#94a3b8',
  NEGATIVE: '#ef4444',
};

interface MetricsPanelProps {
  refreshTrigger?: number;
}

export default function MetricsPanel({ refreshTrigger = 0 }: MetricsPanelProps) {
  const [selectedProduct, setSelectedProduct] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [data, setData] = useState<MetricsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

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
      if (startDate) {
        url.searchParams.set('start_date', startDate);
      }
      if (endDate) {
        url.searchParams.set('end_date', endDate);
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
  }, [selectedProduct, startDate, endDate]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics, refreshTrigger]);

  if (!isMounted) {
    return (
      <div className="flex items-center justify-center h-40 gap-2 text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span className="text-sm font-medium">Iniciando panel...</span>
      </div>
    );
  }

  if (isLoading && !data) {
    return (
      <div className="flex items-center justify-center h-40 gap-2 text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span className="text-sm font-medium">Cargando métricas...</span>
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
        <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-3 border border-gray-200 rounded-lg shadow-sm">
          {(data?.available_products?.length ?? 0) > 0 && (
            <ProductFilter
              products={data?.available_products || []}
              selected={selectedProduct}
              onChange={setSelectedProduct}
              isLoading={isLoading}
            />
          )}

          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500 font-medium">Desde:</span>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="text-sm border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-500 font-medium">Hasta:</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="text-sm border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {(startDate || endDate) && (
              <button
                onClick={() => {
                  setStartDate('');
                  setEndDate('');
                }}
                className="text-xs text-blue-600 hover:underline ml-1 font-medium"
              >
                Limpiar fechas
              </button>
            )}
          </div>
        </div>
        <div className="text-center text-gray-400 text-sm py-10">
          {selectedProduct || startDate || endDate
            ? 'No hay reseñas con los filtros seleccionados.'
            : 'Aún no hay reseñas ingeridas. Sube un PDF para comenzar.'}
        </div>
      </div>
    );
  }

  const sentimentData = data.sentiment_distribution
    ? [
        { name: 'Positivo', value: data.sentiment_distribution.POSITIVE || 0, fill: SENTIMENT_COLORS.POSITIVE },
        { name: 'Neutro', value: data.sentiment_distribution.NEUTRAL || 0, fill: SENTIMENT_COLORS.NEUTRAL },
        { name: 'Negativo', value: data.sentiment_distribution.NEGATIVE || 0, fill: SENTIMENT_COLORS.NEGATIVE },
      ].filter((item) => item.value > 0)
    : [];

  const barChartData = (data.distribution || []).map((d) => ({
    name: `${d.rating} ★`,
    cantidad: d.cantidad,
    rating: d.rating,
    fill: RATING_COLORS[d.rating] || '#3b82f6',
  }));

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Barra de Filtros (Producto + Fechas) */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-3 border border-gray-200 rounded-lg shadow-sm">
        {(data?.available_products?.length ?? 0) > 0 && (
          <ProductFilter
            products={data?.available_products || []}
            selected={selectedProduct}
            onChange={setSelectedProduct}
            isLoading={isLoading}
          />
        )}

        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500 font-medium">Desde:</span>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="text-sm border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-500 font-medium">Hasta:</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="text-sm border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {(startDate || endDate) && (
            <button
              onClick={() => {
                setStartDate('');
                setEndDate('');
              }}
              className="text-xs text-blue-600 hover:underline ml-1 font-medium"
            >
              Limpiar fechas
            </button>
          )}
        </div>
      </div>

      {/* KPIs Principales */}
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

      {/* Fila Dual: Sentimiento y Distribución por Estrellas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Gráfico de Sentimiento VoC */}
        <div className="border border-gray-100 rounded-lg p-4 bg-slate-50/50">
          <h3 className="text-sm font-semibold text-gray-600 mb-2 flex items-center gap-1.5">
            <ThumbsUp className="w-4 h-4 text-blue-500" />
            Sentimiento General (VoC)
          </h3>
          {sentimentData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={sentimentData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={75}
                  paddingAngle={4}
                  dataKey="value"
                />
                <Tooltip formatter={(val) => [`${val} opiniones`, 'Cantidad']} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-xs text-gray-400 py-10 text-center">Sin datos de sentimiento</p>
          )}
        </div>

        {/* Distribución por Estrellas */}
        <div className="border border-gray-100 rounded-lg p-4 bg-slate-50/50">
          <h3 className="text-sm font-semibold text-gray-600 mb-2">
            Distribución de Calificaciones
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={barChartData}
              layout="vertical"
              margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
              <XAxis type="number" hide allowDecimals={false} />
              <YAxis dataKey="name" type="category" width={45} fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip cursor={{ fill: '#f8fafc' }} formatter={(val) => [`${val ?? 0} reseñas`, 'Cantidad']} />
              <Bar dataKey="cantidad" radius={[0, 4, 4, 0]} barSize={22} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tendencia Temporal */}
      {data.timeseries && data.timeseries.length > 0 && (
        <div className="border border-gray-100 rounded-lg p-4 bg-slate-50/50">
          <h3 className="text-sm font-semibold text-gray-600 mb-3">
            Evolución Temporal
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data.timeseries} margin={{ top: 10, right: 20, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="fecha" fontSize={11} tickLine={false} stroke="#64748b" />
              <YAxis yAxisId="left" domain={[1, 5]} fontSize={11} tickLine={false} stroke="#22c55e" />
              <YAxis yAxisId="right" orientation="right" fontSize={11} tickLine={false} stroke="#3b82f6" allowDecimals={false} />
              <Tooltip contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px' }} />
              <Legend wrapperStyle={{ fontSize: '11px' }} />
              <Line yAxisId="left" type="monotone" dataKey="promedio" name="Promedio" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
              <Line yAxisId="right" type="monotone" dataKey="cantidad" name="Reseñas" stroke="#3b82f6" strokeWidth={2} strokeDasharray="4 4" dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Fila Dual: Categorías Destacadas y Nube de Aspect Tags */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Categorías VoC */}
        <div className="border border-gray-100 rounded-lg p-4 bg-slate-50/50">
          <h3 className="text-sm font-semibold text-gray-600 mb-3 flex items-center gap-1.5">
            <MessageSquare className="w-4 h-4 text-purple-500" />
            Top Categorías Mencionadas
          </h3>
          {data.top_categories && data.top_categories.length > 0 ? (
            <div className="flex flex-col gap-2">
              {data.top_categories.map((cat, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs bg-white p-2.5 rounded border border-gray-100">
                  <span className="font-medium text-slate-700 capitalize">{cat.category}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-400">{cat.count} menciones</span>
                    <span className="font-semibold text-emerald-600">{cat.avg_rating} ★</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-400 py-6 text-center">Sin datos de categorías</p>
          )}
        </div>

        {/* Aspect Tags */}
        <div className="border border-gray-100 rounded-lg p-4 bg-slate-50/50">
          <h3 className="text-sm font-semibold text-gray-600 mb-3 flex items-center gap-1.5">
            <Tag className="w-4 h-4 text-amber-500" />
            Aspectos Clave (Aspect Tags)
          </h3>
          {data.top_aspect_tags && data.top_aspect_tags.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {data.top_aspect_tags.map((item, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200"
                >
                  {item.tag}
                  <span className="bg-amber-200 text-amber-900 rounded-full text-[10px] px-1.5 py-0.2">
                    {item.count}
                  </span>
                </span>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-400 py-6 text-center">Sin aspectos detectados</p>
          )}
        </div>
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