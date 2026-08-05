// Archivo: app/page.tsx
"use client";

import { useState } from 'react';
import { BarChart3 } from 'lucide-react';
import MetricsPanel from '../components/MetricsPanel';
import DocumentManager from '../components/DocumentManager';
import ChatPanel from '../components/ChatPanel';

export default function Dashboard() {
  // Contador global para actualizar componentes dependientes
  const [metricsRefreshTrigger, setMetricsRefreshTrigger] = useState(0);

  const handleRefreshAll = () => {
    setMetricsRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 p-8">

      {/* Header */}
      <header className="mb-8 flex items-center justify-between">
        <h1 className="text-3xl font-bold flex items-center gap-2 text-slate-800">
          <BarChart3 className="text-blue-600" />
          InsightRAG
        </h1>
        <span className="bg-blue-100 text-blue-800 text-sm font-semibold px-4 py-1 rounded-full border border-blue-200">
          Product Manager View
        </span>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* ── Columna Izquierda: Métricas y Gestión de Documentos (2/3 del ancho) ── */}
        <div className="lg:col-span-2 flex flex-col gap-8">
          
          {/* Panel de Métricas */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 overflow-hidden">
            <h2 className="text-xl font-semibold mb-4 border-b border-gray-100 pb-2">
              Resumen de Sentimiento
            </h2>
            <MetricsPanel refreshTrigger={metricsRefreshTrigger} />
          </div>

          {/* Gestión de Documentos Ingeridos */}
          <DocumentManager 
            onRefreshMetrics={handleRefreshAll}
            refreshTrigger={metricsRefreshTrigger}
          />
        </div>

        {/* ── Columna Derecha: Contenedor con Ingesta e InsightChat (1/3 del ancho) ── */}
        <div>
          <ChatPanel onUploadSuccess={handleRefreshAll} />
        </div>

      </main>
    </div>
  );
}