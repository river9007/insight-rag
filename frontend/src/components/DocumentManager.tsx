'use client';

import { useState, useEffect, useCallback } from 'react';
import { Trash2, RefreshCw, FileText, AlertTriangle, Loader2 } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';

interface DocumentItem {
  review_group_id: string;
  product_id: string;
  rating: number;
  text_preview: string;
}

interface DocumentManagerProps {
  onRefreshMetrics?: () => void;
  refreshTrigger?: number;
}

export default function DocumentManager({ onRefreshMetrics, refreshTrigger }: DocumentManagerProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deletingAll, setDeletingAll] = useState<boolean>(false);
  
  // null = cerrado | 'ALL' = vaciar todo | '<id>' = borrar documento individual
  const [targetToDelete, setTargetToDelete] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        setLoading(false);
        return;
      }

      const res = await fetch(`${API_URL}/documents`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (!res.ok) throw new Error('Error al cargar la lista de documentos.');

      const data = await res.json();
      setDocuments(data.documents || []);
    } catch (err: any) {
      setError(err.message || 'No se pudieron recuperar los documentos.');
    } finally {
      setLoading(false);
    }
  }, [API_URL]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments, refreshTrigger]);

  const handleDeleteOne = async (review_group_id: string) => {
    setDeletingId(review_group_id);
    setError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const res = await fetch(`${API_URL}/documents/${review_group_id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (!res.ok) throw new Error('No se pudo eliminar el documento.');

      setDocuments((prev) => prev.filter((doc) => doc.review_group_id !== review_group_id));
      setTargetToDelete(null);
      if (onRefreshMetrics) onRefreshMetrics();
    } catch (err: any) {
      setError(err.message || 'Error al intentar eliminar el documento.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteAll = async () => {
    setDeletingAll(true);
    setError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const res = await fetch(`${API_URL}/documents/all`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (!res.ok) throw new Error('No se pudo vaciar la base de conocimientos.');

      setDocuments([]);
      setTargetToDelete(null);
      if (onRefreshMetrics) onRefreshMetrics();
    } catch (err: any) {
      setError(err.message || 'Error al intentar vaciar los datos.');
    } finally {
      setDeletingAll(false);
    }
  };

  const isDeleting = deletingAll || deletingId !== null;

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">
            Gestión de Documentos Ingeridos
          </h2>
          <span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 px-2 py-0.5 rounded-full font-medium">
            {documents.length}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchDocuments}
            disabled={loading}
            className="p-2 text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            title="Actualizar lista"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {documents.length > 0 && (
            <button
              onClick={() => setTargetToDelete('ALL')}
              className="flex items-center gap-1.5 text-xs bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/60 font-medium px-3 py-1.5 rounded-lg border border-red-200 dark:border-red-800/50 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Vaciar Todo
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 text-xs bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-lg">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-8 text-slate-400">
          <Loader2 className="w-6 h-6 animate-spin mr-2" />
          <span className="text-sm">Cargando base de conocimientos...</span>
        </div>
      ) : documents.length === 0 ? (
        <div className="text-center py-8 text-slate-500 dark:text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-lg">
          <p className="text-sm">No tienes documentos o reseñas registradas.</p>
          <p className="text-xs text-slate-400 mt-1">Sube archivos en el panel superior para comenzar.</p>
        </div>
      ) : (
        <div className="divide-y divide-slate-100 dark:divide-slate-800 max-h-80 overflow-y-auto">
          {documents.map((doc) => (
            <div key={doc.review_group_id} className="py-3 flex items-center justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-300 px-2 py-0.5 rounded border border-indigo-100 dark:border-indigo-900/50">
                    {doc.product_id}
                  </span>
                  <span className="text-xs font-medium text-amber-600 dark:text-amber-400">
                    ★ {doc.rating}/5
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 truncate">
                  {doc.text_preview}
                </p>
              </div>

              <button
                onClick={() => setTargetToDelete(doc.review_group_id)}
                disabled={deletingId === doc.review_group_id}
                className="p-1.5 text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors flex-shrink-0"
                title="Eliminar este grupo/reseña"
              >
                {deletingId === doc.review_group_id ? (
                  <Loader2 className="w-4 h-4 animate-spin text-red-600" />
                ) : (
                  <Trash2 className="w-4 h-4" />
                )}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Modal UNIFICADO de confirmación */}
      {targetToDelete !== null && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 max-w-md w-full p-6 shadow-xl">
            <div className="flex items-center gap-3 text-red-600 dark:text-red-400 mb-3">
              <AlertTriangle className="w-6 h-6 flex-shrink-0" />
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {targetToDelete === 'ALL'
                  ? '¿Vaciar base de conocimientos?'
                  : '¿Eliminar este documento?'}
              </h3>
            </div>
            
            <p className="text-xs text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
              {targetToDelete === 'ALL'
                ? 'Esta acción eliminará de forma permanente TODOS tus documentos y vectores asociados. No podrás recuperar esta información.'
                : 'Esta acción eliminará de forma permanente este documento específico y sus vectores asociados de la base de datos.'}
            </p>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setTargetToDelete(null)}
                disabled={isDeleting}
                className="px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              
              <button
                onClick={() => {
                  if (targetToDelete === 'ALL') {
                    handleDeleteAll();
                  } else {
                    handleDeleteOne(targetToDelete);
                  }
                }}
                disabled={isDeleting}
                className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Eliminando...
                  </>
                ) : (
                  targetToDelete === 'ALL' ? 'Sí, vaciar todo' : 'Sí, eliminar'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}