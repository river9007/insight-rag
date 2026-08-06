// Archivo: components/DocumentUploader.tsx
'use client';

import React, { useState, useEffect } from 'react';
import { UploadCloud, AlertTriangle, CheckCircle, FileText, Download, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';

interface SkippedRow {
  fila: number;
  motivo: string;
}

interface IngestResponse {
  status: string;
  message: string;
  resenas_importadas?: number;
  resenas_detectadas?: number; // Compatibilidad en cascada
  filas_omitidas: number;
  detalle_filas_omitidas: SkippedRow[];
  chunks_creados: number;
}

interface DocumentUploaderProps {
  onUploadSuccess?: () => void;
}

export default function DocumentUploader({ onUploadSuccess }: DocumentUploaderProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [stageText, setStageText] = useState<string>('');
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState<boolean>(false);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  // Simulación dinámica del avance mientras la petición asíncrona está ejecutándose
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (loading) {
      setProgress(15);
      setStageText('Leyendo archivo...');
      
      timer = setInterval(() => {
        setProgress((prev) => {
          if (prev < 45) {
            setStageText('Procesando contenido...');
            return prev + 10;
          }
          if (prev < 75) {
            setStageText('Generando vectores de conocimiento...');
            return prev + 5;
          }
          if (prev < 90) {
            setStageText('Guardando en Supabase...');
            return prev + 2;
          }
          return prev;
        });
      }, 350);
    } else {
      setProgress(0);
      setStageText('');
    }

    return () => clearInterval(timer);
  }, [loading]);

  // Función para generar y descargar la plantilla CSV de referencia
  const downloadTemplate = () => {
    const csvContent =
      'ID de Producto,Rating,Reseña\n' +
      'PROD-1001 (Auriculares Bluetooth),5,"Excelente sonido y gran duración de batería."\n' +
      'PROD-2042 (Monitor Gamer 27),4,"Muy buena tasa de refresco, colores vivos."\n';

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'plantilla_resenas_ejemplo.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setResult(null);
      setError(null);
    }
  };

  // Handlers para la funcionalidad de Drag & Drop
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!loading) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (loading) return;

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      const validExtensions = ['.csv', '.xlsx', '.xls', '.pdf', '.txt'];
      const fileExtension = '.' + droppedFile.name.split('.').pop()?.toLowerCase();

      if (validExtensions.includes(fileExtension)) {
        setFile(droppedFile);
        setResult(null);
        setError(null);
      } else {
        setError('Formato de archivo no soportado. Usa CSV, Excel (.xlsx), PDF o TXT.');
      }
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      const response = await fetch(`${API_URL}/ingest`, {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Ocurrió un error al procesar el archivo en el servidor.');
      }

      setProgress(100);
      setStageText('¡Completado!');
      setResult(data);
      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (err: any) {
      setError(err.message || 'Error de conexión con el servidor.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold text-slate-800">Cargar Documento de Feedback</h2>
        
        <button
          onClick={downloadTemplate}
          className="flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-800 font-medium transition-colors"
          type="button"
        >
          <Download className="w-3.5 h-3.5" />
          Descargar Plantilla CSV
        </button>
      </div>

      {/* Zona de Selección y Soltado de Archivo */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-6 text-center transition-all ${
          isDragging
            ? 'border-indigo-500 bg-indigo-50/50 scale-[1.005]'
            : 'border-slate-300 bg-slate-50/50 hover:border-indigo-400'
        }`}
      >
        <input
          type="file"
          accept=".csv,.xlsx,.xls,.pdf,.txt"
          onChange={handleFileChange}
          className="hidden"
          id="file-input"
          disabled={loading}
        />
        <label htmlFor="file-input" className="cursor-pointer flex flex-col items-center">
          {loading ? (
            <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mb-2" />
          ) : (
            <UploadCloud className={`w-8 h-8 mb-2 transition-colors ${isDragging ? 'text-indigo-600' : 'text-slate-400'}`} />
          )}
          <span className="text-sm font-medium text-slate-700">
            {file ? file.name : isDragging ? '¡Suelta el archivo aquí!' : 'Haz clic para seleccionar o arrastra un archivo'}
          </span>
          <span className="text-xs text-slate-500 mt-1">
            Soporta CSV, Excel (.xlsx), PDF y TXT (Máx. 10MB)
          </span>
        </label>
      </div>

      {/* Indicador de Progreso Visual */}
      {loading && (
        <div className="mt-4 space-y-1.5">
          <div className="flex justify-between text-xs text-slate-600 font-medium">
            <span>{stageText}</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
            <div
              className="bg-indigo-600 h-full transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Accionable de Procesamiento */}
      {file && !loading && (
        <button
          onClick={handleUpload}
          disabled={loading}
          className="w-full mt-4 bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 px-4 rounded-xl transition-colors disabled:opacity-50 flex justify-center items-center gap-2 text-sm"
        >
          <FileText className="w-4 h-4" />
          Procesar Archivo
        </button>
      )}

      {/* Notificación de Error */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-red-700">{error}</p>
        </div>
      )}

      {/* Resultado de la Ingesta Backend */}
      {result && (
        <div className="mt-4 space-y-3">
          {result.filas_omitidas > 0 ? (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-amber-800">
                    Proceso completado con advertencias
                  </h4>
                  <p className="text-xs text-amber-700 mt-1">
                    Se importaron <strong>{result.resenas_importadas ?? result.resenas_detectadas ?? 0}</strong> reseña(s) ({result.chunks_creados} vectores). 
                    Se omitieron <strong>{result.filas_omitidas}</strong> fila(s) con formato no válido.
                  </p>
                  
                  {result.detalle_filas_omitidas && result.detalle_filas_omitidas.length > 0 && (
                    <>
                      <button
                        onClick={() => setShowDetails(!showDetails)}
                        className="mt-2 text-xs font-semibold text-amber-900 flex items-center gap-1 hover:underline"
                      >
                        {showDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        {showDetails ? 'Ocultar detalles' : 'Ver filas omitidas'}
                      </button>

                      {showDetails && (
                        <ul className="mt-2 space-y-1 text-xs text-amber-900 bg-amber-100/60 p-2.5 rounded-lg border border-amber-200">
                          {result.detalle_filas_omitidas.map((item, idx) => (
                            <li key={idx}>
                              • <strong>Fila {item.fila}:</strong> {item.motivo}
                            </li>
                          ))}
                        </ul>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-emerald-800">
                  ¡Ingesta completada con éxito!
                </h4>
                <p className="text-xs text-emerald-700 mt-1">
                  Se procesaron <strong>{result.resenas_importadas ?? result.resenas_detectadas ?? 0}</strong> reseña(s) correctamente y se generaron <strong>{result.chunks_creados}</strong> vectores de conocimiento.
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}