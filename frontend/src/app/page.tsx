// Archivo: frontend/src/app/page.tsx
"use client";

import { useState } from 'react';
import { Search, BarChart3, MessageSquare, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import MetricsPanel from '../components/MetricsPanel';
import DocumentUploader from '../components/DocumentUploader';
import { supabase } from '../lib/supabaseClient';

export default function Dashboard() {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([]);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    setAnswer('');

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // Auth Supabase — conservado del dashboard actual
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      const response = await fetch(`${API_URL}/analyze/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          query,
          history: chatHistory,
          limit: 5,
        }),
      });

      if (!response.body) throw new Error('No hay body en la respuesta');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;
      let fullResponse = '';

      while (!done) {
        const { done: readerDone, value } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          fullResponse += chunk;
          setAnswer((prev) => prev + chunk);
        }
      }

      setChatHistory((prev) => [
        ...prev,
        { role: 'user', content: query },
        { role: 'assistant', content: fullResponse },
      ]);

      setAnswer('');
      setQuery('');
    } catch (error) {
      console.error('Error en la conexión:', error);
      setAnswer('❌ Ocurrió un error al conectar con el backend.');
    } finally {
      setIsLoading(false);
    }
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

        {/* ── Panel de Métricas (2/3 del ancho) ── */}
        {/* overflow-hidden: barrera de seguridad por si algún SVG de Recharts desborda */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-6 overflow-hidden">
          <h2 className="text-xl font-semibold mb-4 border-b border-gray-100 pb-2">
            Resumen de Sentimiento
          </h2>
          {/* Sin wrapper flex-1: MetricsPanel se dimensiona solo con contenido natural */}
          <MetricsPanel />
        </div>

        {/* ── Chat RAG + Ingesta (1/3 del ancho) ── */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col h-[700px]">
          <h2 className="text-xl font-semibold mb-4 border-b border-gray-100 pb-2 flex items-center gap-2">
            <MessageSquare size={20} className="text-blue-600" />
            Asistente IA
          </h2>

          {/* Subida de documentos */}
          <div className="mb-4">
            <DocumentUploader />
          </div>

          {/* Historial de conversación */}
          <div className="flex-1 bg-slate-50 rounded-lg p-4 mb-4 overflow-y-auto border border-gray-100 flex flex-col gap-4">
            {chatHistory.length === 0 && !answer && !isLoading && (
              <p className="text-gray-400 text-sm text-center mt-10">
                Sube un documento PDF o hazme una pregunta sobre las reseñas del producto...
              </p>
            )}

            {chatHistory.map((msg, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-indigo-50 border border-indigo-100 ml-4'
                    : 'bg-white border border-slate-200 shadow-sm mr-4'
                }`}
              >
                <span
                  className={`text-xs font-bold uppercase mb-2 block ${
                    msg.role === 'user' ? 'text-indigo-600' : 'text-blue-600'
                  }`}
                >
                  {msg.role === 'user' ? 'Tú' : 'IA'}
                </span>
                <div className="prose prose-sm prose-slate max-w-none">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              </div>
            ))}

            {/* Burbuja de streaming en tiempo real */}
            {(answer || isLoading) && (
              <div className="p-4 rounded-lg bg-white border border-blue-200 shadow-sm mr-4">
                <span className="text-xs font-bold uppercase text-blue-600 mb-2 flex items-center gap-2">
                  IA Analizando...
                  {isLoading && !answer && (
                    <Loader2 size={14} className="animate-spin text-blue-500" />
                  )}
                </span>
                <div className="prose prose-sm prose-slate max-w-none">
                  <ReactMarkdown>{answer}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="relative mt-auto">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Ej: ¿Qué dicen de la batería?"
              className="w-full pl-4 pr-12 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all text-gray-900"
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