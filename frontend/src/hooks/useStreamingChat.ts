"use client";

import { useState } from 'react';
import { supabase } from '../lib/supabaseClient'; // 👈 Importamos la instancia oficial de Supabase

export interface Source {
  product_id?: string;
  rating?: number;
  text_preview?: string;
  name?: string;
  source?: string;
  relevance?: string | number;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
}

export function useStreamingChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (userPrompt?: string) => {
    const promptToSend = userPrompt ?? input;
    if (!promptToSend.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', content: promptToSend };

    // Construir el historial para enviarlo al backend antes de mutar el estado local
    const historyPayload = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    // 1. Añadir el mensaje del usuario y una burbuja vacía para el asistente
    setMessages((prev) => [
      ...prev,
      userMessage,
      { role: 'assistant', content: '', sources: [] },
    ]);
    setIsLoading(true);
    setInput('');

    try {
      // 🛡️ Tech Lead Insight: En lugar de buscar claves a ciegas en localStorage,
      // consultamos directamente a la sesión activa de Supabase SDK o al almacenamiento local estructurado.
      const sessionData = await supabase.auth.getSession();
      let token = sessionData.data.session?.access_token;

      // Fallback por si la sesión síncrona tarda o requiere lectura directa del storage de Supabase
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
        console.warn('No se encontró un token de sesión activo en Supabase.');
        throw new Error('No hay una sesión activa. Por favor, inicia sesión de nuevo.');
      }

      // Única llamada fetch correcta al backend con el token JWT real
      const response = await fetch('http://localhost:8000/analyze/stream', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          query: promptToSend,
          history: historyPayload,
          limit: 10,
          product_id: null
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error('Error al conectar con el servidor');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let fullText = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        fullText += chunk;

        if (fullText.includes('|||SOURCES|||')) {
          const [textContent, sourcesJSON] = fullText.split('|||SOURCES|||');
          let parsedSources: Source[] = [];

          try {
            parsedSources = JSON.parse(sourcesJSON.trim());
          } catch (e) {
            console.error('Error al parsear JSON de fuentes:', e);
          }

          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: 'assistant',
              content: textContent.trim(),
              sources: parsedSources,
            };
            return updated;
          });
        } else {
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: 'assistant',
              content: fullText,
              sources: updated[updated.length - 1]?.sources || [],
            };
            return updated;
          });
        }
      }
    } catch (error: any) {
      console.error('Streaming error:', error);
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: 'assistant',
          content: error.message || 'Ocurrió un error al procesar tu consulta. Inténtalo de nuevo.',
        };
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  return {
    messages,
    input,
    setInput,
    isLoading,
    sendMessage,
    // Aliases de compatibilidad para evitar roturas
    chatHistory: messages,
    query: input,
    setQuery: setInput,
    handleSearch: () => sendMessage(),
  };
}