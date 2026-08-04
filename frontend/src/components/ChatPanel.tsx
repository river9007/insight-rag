"use client";

import { useState } from 'react';
import { Search, MessageSquare, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import DocumentUploader from './DocumentUploader';
import { supabase } from '../lib/supabaseClient';

interface ChatPanelProps {
  onUploadSuccess: () => void;
}

interface SourceItem {
  product_id: string;
  rating: number;
  text_preview: string;
  review_group_id?: string;
}

interface ChatMessage {
  role: string;
  content: string;
  sources?: SourceItem[];
}

export default function ChatPanel({ onUploadSuccess }: ChatPanelProps) {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [currentSources, setCurrentSources] = useState<SourceItem[] | null>(null);

  // Función helper para deduplicar fuentes en el cliente como red de seguridad
  const deduplicateSources = (sources: SourceItem[]): SourceItem[] => {
    if (!sources || !Array.isArray(sources)) return [];
    const seen = new Set<string>();
    return sources.filter((src) => {
      // Usamos review_group_id si existe, o una combinación de product_id + rating + texto
      const key = src.review_group_id || `${src.product_id}-${src.rating}-${src.text_preview?.slice(0, 30)}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  };

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    setAnswer('');
    setCurrentSources(null);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
          history: chatHistory.map(msg => ({ role: msg.role, content: msg.content })),
        }),
      });

      if (!response.body) throw new Error('No hay body en la respuesta');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;
      let rawAccumulated = '';
      let textContent = '';
      let extractedSources: SourceItem[] | null = null;

      while (!done) {
        const { done: readerDone, value } = await reader.read();
        done = readerDone;
        if (value) {
          rawAccumulated += decoder.decode(value, { stream: true });

          // Verificamos si el payload ya incluye el delimitador de fuentes
          if (rawAccumulated.includes('|||SOURCES|||')) {
            const parts = rawAccumulated.split('|||SOURCES|||');
            textContent = parts[0];
            const sourcesJsonString = parts[1];

            setAnswer(textContent);

            if (sourcesJsonString && sourcesJsonString.trim()) {
              try {
                const parsed = JSON.parse(sourcesJsonString);
                extractedSources = deduplicateSources(parsed);
                setCurrentSources(extractedSources);
              } catch (e) {
                console.error("Error parseando fuentes JSON:", e);
              }
            }
          } else {
            textContent = rawAccumulated;
            setAnswer(textContent);
          }
        }
      }

      // Guardamos el mensaje final en el historial con sus fuentes deduplicadas
      setChatHistory((prev) => [
        ...prev,
        { role: 'user', content: query },
        { role: 'assistant', content: textContent, sources: extractedSources || [] },
      ]);

      setAnswer('');
      setQuery('');
      setCurrentSources(null);
    } catch (error) {
      console.error('Error en la conexión:', error);
      setAnswer('❌ Ocurrió un error al conectar con el backend.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col h-[750px]">
      <h2 className="text-xl font-semibold mb-4 border-b border-gray-100 pb-2 flex items-center gap-2">
        <MessageSquare size={20} className="text-blue-600" />
        Asistente IA
      </h2>

      {/* Subida de documentos */}
      <div className="mb-4">
        <DocumentUploader onUploadSuccess={onUploadSuccess} />
      </div>

      {/* Historial de conversación */}
      <div className="flex-1 bg-slate-50 rounded-lg p-4 mb-4 overflow-y-auto border border-gray-100 flex flex-col gap-4">
        {chatHistory.length === 0 && !answer && !isLoading && (
          <p className="text-gray-400 text-sm text-center mt-10">
            Sube un documento o hazme una pregunta sobre las reseñas del producto...
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
            
            {/* Renderizado de fuentes del historial */}
            {msg.sources && msg.sources.length > 0 && (
              <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap gap-2">
                <span className="text-xs font-semibold text-slate-500 w-full mb-1">Fuentes utilizadas:</span>
                {msg.sources.map((src, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-xs bg-slate-50 border border-slate-200 text-slate-600 px-2.5 py-1 rounded-md cursor-help" title={src.text_preview}>
                    <span className="font-semibold text-indigo-600">{src.product_id}</span>
                    <span className="text-amber-500 font-medium">★ {src.rating}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {/* Mensaje actual en proceso (Streaming) */}
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
            
            {/* Renderizado de fuentes durante el streaming */}
            {currentSources && currentSources.length > 0 && (
              <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap gap-2">
                <span className="text-xs font-semibold text-slate-500 w-full mb-1">Fuentes utilizadas:</span>
                {currentSources.map((src, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-xs bg-slate-50 border border-slate-200 text-slate-600 px-2.5 py-1 rounded-md cursor-help" title={src.text_preview}>
                    <span className="font-semibold text-indigo-600">{src.product_id}</span>
                    <span className="text-amber-500 font-medium">★ {src.rating}</span>
                  </div>
                ))}
              </div>
            )}
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
  );
}