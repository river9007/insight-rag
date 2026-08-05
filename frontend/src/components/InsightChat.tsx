"use client";

import { Search, MessageSquare, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useStreamingChat } from '../hooks/useStreamingChat';

export default function InsightChat() {
  const {
    messages = [],
    input,
    setInput,
    isLoading,
    sendMessage,
  } = useStreamingChat();

  return (
    <div className="flex flex-col h-full min-h-0">
      <h2 className="text-xl font-semibold mb-4 border-b border-gray-100 pb-2 flex items-center gap-2 flex-shrink-0">
        <MessageSquare size={20} className="text-blue-600" />
        Asistente IA
      </h2>

      {/* Historial de conversación */}
      <div className="flex-1 bg-slate-50 rounded-lg p-4 mb-4 overflow-y-auto border border-gray-100 flex flex-col gap-4 min-h-0">
        {messages.length === 0 && !isLoading && (
          <p className="text-gray-400 text-sm text-center mt-10">
            Sube un documento o hazme una pregunta sobre las reseñas del producto...
          </p>
        )}

        {messages.map((msg, idx) => {
          // Ocultar mensaje streaming en blanco al inicio del render
          if (msg.role === 'assistant' && !msg.content && isLoading && idx === messages.length - 1) {
            return (
              <div key={idx} className="p-4 rounded-lg bg-white border border-blue-200 shadow-sm mr-4">
                <span className="text-xs font-bold uppercase text-blue-600 mb-2 flex items-center gap-2">
                  IA Analizando...
                  <Loader2 size={14} className="animate-spin text-blue-500" />
                </span>
              </div>
            );
          }

          return (
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

              {/* Fuentes RAG */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap gap-2">
                  <span className="text-xs font-semibold text-slate-500 w-full mb-1">
                    Fuentes utilizadas:
                  </span>
                  {msg.sources.map((src, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-1.5 text-xs bg-slate-50 border border-slate-200 text-slate-600 px-2.5 py-1 rounded-md cursor-help"
                      title={src.text_preview || src.source}
                    >
                      <span className="font-semibold text-indigo-600">
                        {src.product_id || src.name || 'Doc'}
                      </span>
                      {src.rating !== undefined && (
                        <span className="text-amber-500 font-medium">★ {src.rating}</span>
                      )}
                      {src.relevance !== undefined && (
                        <span className="text-blue-600 font-medium">
                          {typeof src.relevance === 'number'
                            ? `${(src.relevance * 100).toFixed(0)}%`
                            : src.relevance}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Input de búsqueda */}
      <div className="relative mt-auto flex-shrink-0">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ej: ¿Qué dicen de la batería?"
          className="w-full pl-4 pr-12 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all text-gray-900"
          disabled={isLoading}
        />
        <button
          onClick={() => sendMessage()}
          disabled={isLoading || !input.trim()}
          className="absolute right-2 top-2 p-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 transition-colors"
        >
          <Search size={18} />
        </button>
      </div>
    </div>
  );
}