"use client";

import { useEffect, useRef } from 'react';
import { Search, MessageSquare, Loader2, Bot, User } from 'lucide-react';
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

  // Cambiamos la referencia: ahora apuntamos al contenedor general, no al final
  const chatContainerRef = useRef<HTMLDivElement | null>(null);

  // Nuevo efecto de scroll: Solo afecta al div interno, no a la página
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header del Chat */}
      <h2 className="text-xl font-semibold mb-4 border-b border-gray-100 pb-2 flex items-center justify-between flex-shrink-0 text-slate-800">
        <div className="flex items-center gap-2">
          <MessageSquare size={20} className="text-blue-600" />
          <span>Asistente IA</span>
        </div>
        {isLoading && (
          <span className="flex items-center gap-1.5 text-xs text-blue-600 bg-blue-50 px-2.5 py-1 rounded-full font-medium">
            <Loader2 size={12} className="animate-spin text-blue-600" />
            Analizando...
          </span>
        )}
      </h2>

      {/* Historial de conversación con la nueva Referencia (chatContainerRef) */}
      <div 
        ref={chatContainerRef}
        className="flex-1 bg-slate-50 rounded-xl p-4 mb-4 overflow-y-auto border border-gray-100 flex flex-col gap-4 min-h-0"
      >
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full text-center text-slate-400 p-6">
            <Bot className="w-10 h-10 mb-2 stroke-[1.5] text-slate-300" />
            <p className="text-sm font-medium">Sube un documento o hazme una pregunta sobre las reseñas del producto...</p>
          </div>
        )}

        {messages.map((msg, idx) => {
          const isUser = msg.role === 'user';

          // Renderizado cuando la IA está analizando la respuesta inicial
          if (!isUser && !msg.content && isLoading && idx === messages.length - 1) {
            return (
              <div key={idx} className="flex gap-3 items-start mr-4">
                <div className="w-7 h-7 rounded-lg bg-blue-600 text-white flex items-center justify-center flex-shrink-0 text-xs font-bold">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="p-3.5 rounded-2xl bg-white border border-blue-200 shadow-sm flex items-center gap-2">
                  <span className="text-xs text-slate-500 font-medium">IA Analizando</span>
                  <span className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                    <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                    <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce"></span>
                  </span>
                </div>
              </div>
            );
          }

          return (
            <div
              key={idx}
              className={`flex gap-3 items-start ${isUser ? 'flex-row-reverse ml-4' : 'mr-4'}`}
            >
              {/* Avatar Icon */}
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                  isUser ? 'bg-slate-800 text-white' : 'bg-blue-600 text-white'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Burbuja del mensaje */}
              <div
                className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                  isUser
                    ? 'bg-indigo-50 text-slate-800 border border-indigo-100 rounded-tr-none'
                    : 'bg-white text-slate-800 border border-slate-200 rounded-tl-none shadow-sm'
                }`}
              >
                <span
                  className={`text-xs font-bold uppercase mb-2 block ${
                    isUser ? 'text-indigo-600' : 'text-blue-600'
                  }`}
                >
                  {isUser ? 'Tú' : 'IA'}
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
            </div>
          );
        })}
        {/* Eliminamos el div vacío que usábamos como ancla */}
      </div>

      {/* Input de búsqueda */}
      <div className="relative mt-auto flex-shrink-0">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !isLoading && sendMessage()}
          placeholder="Ej: ¿Qué dicen de la batería?"
          className="w-full pl-4 pr-12 py-3 rounded-xl border border-gray-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all text-xs sm:text-sm shadow-sm disabled:opacity-50"
          disabled={isLoading}
        />
        <button
          onClick={() => sendMessage()}
          disabled={isLoading || !input.trim()}
          className="absolute right-2 top-2 p-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-40 transition-colors"
        >
          <Search size={18} />
        </button>
      </div>
    </div>
  );
}