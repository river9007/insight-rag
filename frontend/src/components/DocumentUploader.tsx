import { useState } from 'react';
import { UploadCloud, Loader2, CheckCircle } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';

export default function DocumentUploader() {
  const [isUploading, setIsUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.type !== 'application/pdf') {
      setStatusMessage('Por favor, selecciona un archivo PDF válido.');
      return;
    }

    setIsUploading(true);
    setStatusMessage('Procesando y vectorizando...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      const response = await fetch(`${API_URL}/ingest`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        setStatusMessage(`¡Éxito! Archivo procesado en ${data.chunks_creados} fragmentos.`);
      } else {
        setStatusMessage(`Error: ${data.detail || 'Fallo en la ingesta'}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      setStatusMessage('Error de conexión con el servidor.');
    } finally {
      setIsUploading(false);
      event.target.value = ''; 
    }
  };

  return (
    <div className="w-full">
      <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer bg-white hover:bg-gray-50 transition-all relative overflow-hidden">
        {isUploading ? (
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-2" />
        ) : (
          <UploadCloud className="w-8 h-8 text-gray-400 mb-2" />
        )}
        <span className="text-sm font-medium text-gray-600">
          {isUploading ? 'Vectorizando documento...' : 'Haz clic para subir feedback (PDF)'}
        </span>
        <input 
          type="file" 
          className="hidden" 
          accept=".pdf" 
          onChange={handleFileUpload} 
          disabled={isUploading} 
        />
      </label>

      {statusMessage && (
        <div className={`mt-3 flex items-center gap-2 text-sm p-3 rounded-lg ${statusMessage.includes('Éxito') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {statusMessage.includes('Éxito') && <CheckCircle className="w-4 h-4" />}
          {statusMessage}
        </div>
      )}
    </div>
  );
}