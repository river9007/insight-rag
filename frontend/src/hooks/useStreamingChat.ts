import { useState, useRef, useEffect, useCallback } from 'react';
import { supabase } from '../lib/supabaseClient';

export interface Source {
  id?: string;
  product_id?: string;
  name?: string;
  source?: string;
  rating?: number;
  relevance?: string | number;
  text_preview?: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
}

interface UseStreamingChatOptions {
  renderSpeedMs?: number; // Frecuencia de refresco en ms (por defecto 15ms)
  charsPerTick?: number;  // Caracteres revelados por cada tick (por defecto 2)
}

export function useStreamingChat(options: UseStreamingChatOptions = {}) {
  const { renderSpeedMs = 15, charsPerTick = 2 } = options;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Búferes mutables para desacoplar la red de la UI
  const incomingBufferRef = useRef<string>('');
  const isStreamFinishedRef = useRef<boolean>(false);
  const pendingSourcesRef = useRef<Source[] | null>(null);

  // Bucle de renderizado continuo (Typewriter Engine)
  useEffect(() => {
    if (!isLoading) return;

    const timer = setInterval(() => {
      // 1. Drenar texto del búfer a la UI de forma fluida
      if (incomingBufferRef.current.length > 0) {
        const takeLength = Math.min(charsPerTick, incomingBufferRef.current.length);
        const chunkToDisplay = incomingBufferRef.current.slice(0, takeLength);
        incomingBufferRef.current = incomingBufferRef.current.slice(takeLength);

        setMessages((prev) => {
          if (prev.length === 0) return prev;
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          const lastMsg = updated[lastIdx];

          if (lastMsg && lastMsg.role === 'assistant') {
            updated[lastIdx] = {
              ...lastMsg,
              content: lastMsg.content + chunkToDisplay,
            };
          }
          return updated;
        });
      } 
      // 2. Finalizar cuando la red cerró y el búfer de texto quedó completamente vacío
      else if (isStreamFinishedRef.current) {
        if (pendingSourcesRef.current) {
          const sourcesToInject = pendingSourcesRef.current;
          pendingSourcesRef.current = null;

          setMessages((prev) => {
            if (prev.length === 0) return prev;
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            const lastMsg = updated[lastIdx];

            if (lastMsg && lastMsg.role === 'assistant') {
              updated[lastIdx] = {
                ...lastMsg,
                sources: sourcesToInject,
              };
            }
            return updated;
          });
        }

        setIsLoading(false);
      }
    }, renderSpeedMs);

    return () => clearInterval(timer);
  }, [isLoading, renderSpeedMs, charsPerTick]);

  const sendMessage = useCallback(
    async (userPrompt?: string) => {
      const promptToSend = userPrompt ?? input;
      if (!promptToSend.trim() || isLoading) return;

      // Obtención segura del Token JWT de Supabase
      try {
        const sessionData = await supabase.auth.getSession();
        let token = sessionData.data.session?.access_token;

        if (!token && typeof window !== 'undefined') {
          const supabaseStorageKey = Object.keys(localStorage).find((key) => 
            key.startsWith('sb-') && key.endsWith('-auth-token')
          );
          if (supabaseStorageKey) {
            const storedAuth = JSON.parse(localStorage.getItem(supabaseStorageKey) || '{}');
            token = storedAuth?.access_token;
          }
        }

        if (!token) {
          throw new Error('No hay una sesión activa. Por favor, inicia sesión de nuevo.');
        }

        const userMessage: Message = { role: 'user', content: promptToSend };
        const assistantMessage: Message = { role: 'assistant', content: '', sources: [] };

        const historyPayload = messages.map((m) => ({
          role: m.role,
          content: m.content,
        }));

        setMessages((prev) => [...prev, userMessage, assistantMessage]);
        setIsLoading(true);
        setInput('');

        // Reset de referencias de streaming
        incomingBufferRef.current = '';
        isStreamFinishedRef.current = false;
        pendingSourcesRef.current = null;

        const response = await fetch('http://localhost:8000/analyze/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            query: promptToSend,
            history: historyPayload,
            limit: 10,
            product_id: null,
          }),
        });

        if (!response.ok || !response.body) {
          throw new Error(`Error al conectar con el servidor (HTTP ${response.status})`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        
        let fullPayload = '';
        let processedTextLength = 0;
        const DELIMITER = '|||SOURCES|||';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          fullPayload += decoder.decode(value, { stream: true });
          const delimiterIndex = fullPayload.indexOf(DELIMITER);

          if (delimiterIndex !== -1) {
            // El delimitador ya llegó completo: extraemos texto estricto antes del delimitador
            const textPart = fullPayload.slice(0, delimiterIndex);
            const newTextChunk = textPart.slice(processedTextLength);

            if (newTextChunk.length > 0) {
              incomingBufferRef.current += newTextChunk;
              processedTextLength += newTextChunk.length;
            }

            // Intentar parsear las fuentes del payload restante
            const sourcesJsonStr = fullPayload.slice(delimiterIndex + DELIMITER.length);
            if (sourcesJsonStr.trim()) {
              try {
                pendingSourcesRef.current = JSON.parse(sourcesJsonStr);
              } catch {
                // El JSON de fuentes sigue completándose en chunks posteriores
              }
            }
          } else {
            // Seguridad Anti-Fuga: retenemos los últimos (DELIMITER.length - 1) caracteres 
            // en caso de que el delimitador venga partido entre dos paquetes TCP sucesivos.
            const safeLength = Math.max(0, fullPayload.length - (DELIMITER.length - 1));
            const safeTextChunk = fullPayload.slice(processedTextLength, safeLength);

            if (safeTextChunk.length > 0) {
              incomingBufferRef.current += safeTextChunk;
              processedTextLength += safeTextChunk.length;
            }
          }
        }

        // Parseo final de respaldo de las fuentes tras la finalización completa del Stream de red
        const finalDelimiterIdx = fullPayload.indexOf(DELIMITER);
        if (finalDelimiterIdx !== -1 && !pendingSourcesRef.current) {
          const sourcesJsonStr = fullPayload.slice(finalDelimiterIdx + DELIMITER.length);
          if (sourcesJsonStr.trim()) {
            try {
              pendingSourcesRef.current = JSON.parse(sourcesJsonStr);
            } catch (err) {
              console.error('Error al parsear JSON final de fuentes:', err);
            }
          }
        }
      } catch (error: any) {
        console.error('Streaming error:', error);
        setMessages((prev) => {
          if (prev.length === 0) return prev;
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          const lastMsg = updated[lastIdx];
          if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
            updated[lastIdx] = {
              ...lastMsg,
              content: error.message || 'Ocurrió un error al procesar tu consulta. Inténtalo de nuevo.',
            };
          }
          return updated;
        });
      } finally {
        isStreamFinishedRef.current = true;
      }
    },
    [input, isLoading, messages]
  );

  return {
    messages,
    input,
    setInput,
    isLoading,
    sendMessage,
    // Aliases de compatibilidad integrados para evitar roturas de tipos
    chatHistory: messages,
    query: input,
    setQuery: setInput,
    handleSearch: () => sendMessage(),
  };
}