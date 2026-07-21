// Archivo: frontend/src/app/page.tsx
"use client";

import { useState } from 'react';
import { Search, BarChart3, MessageSquare, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import MetricsPanel from '../components/MetricsPanel';

export default function Dashboard() {
  // Estados para manejar el chat
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Función que se conecta a FastAPI y procesa el streaming
  const handleSearch = async () => {
    if (!query.trim()) return;
    
    setIsLoading(true);
    setAnswer(""); // Limpiamos la respuesta anterior

    try {
      const response = await fetch('https://insight-rag-backend.onrender.com/analyze/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, limit: 5 }),
      });

      if (!response.body) throw new Error("No hay body en la respuesta");

      // API nativa del navegador para leer streams (Server-Sent Events)
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        // Decodificamos el pedazo de texto (chunk) y lo añadimos al estado
        const chunk = decoder.decode(value, { stream: true });
        setAnswer((prev) => prev + chunk);
      }
    } catch (error) {
      console.error("Error en la conexión:", error);
      setAnswer("❌ Ocurrió un error al conectar con el backend.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 p-8">
      
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
        
        {/* Panel de Métricas */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col">
          <h2 className="text-xl font-semibold mb-4 border-b border-gray-100 pb-2">Resumen de Sentimiento</h2>
          <div className="flex-1 min-h-[400px]">
            <MetricsPanel />
          </div>
        </div>

        {/* Panel del Chat RAG */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col h-[500px]">
          <h2 className="text-xl font-semibold mb-4 border-b border-gray-100 pb-2 flex items-center gap-2">
            <MessageSquare size={20} className="text-blue-600" />
            Asistente IA
          </h2>
          
          <div className="flex-1 bg-slate-50 rounded-lg p-4 mb-4 overflow-y-auto border border-gray-100">
            {/* Si no hay respuesta ni está cargando, mostramos texto de ayuda */}
            {!answer && !isLoading && (
              <p className="text-gray-400 text-sm text-center mt-10">
                Hazme una pregunta sobre las reseñas del producto PROD-001...
              </p>
            )}
            
            {/* Aquí renderizamos el Markdown en HTML usando la librería */}
            <div className="prose prose-sm prose-blue">
              <ReactMarkdown>{answer}</ReactMarkdown>
            </div>
            
            {/* Spinner si está procesando el primer token */}
            {isLoading && !answer && (
              <div className="flex justify-center mt-4">
                <Loader2 className="animate-spin text-blue-500" />
              </div>
            )}
          </div>

          <div className="relative mt-auto">
            <input 
              type="text" 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Ej: ¿Qué dicen de la batería?" 
              className="w-full pl-4 pr-12 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
              disabled={isLoading}
            />
            <button 
              onClick={handleSearch}
              disabled={isLoading || !query.trim()}
              className="absolute right-2 top-2 p-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 transition-colors"
            >
              <Search size={18} />
            </button>
          </div>
        </div>
        
      </main>
    </div>
  );
}