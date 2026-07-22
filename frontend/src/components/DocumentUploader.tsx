import { useState } from 'react';
import { UploadCloud, Loader2, CheckCircle } from 'lucide-react';

export default function DocumentUploader() {
  const [isUploading, setIsUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validamos que sea PDF en el frontend para mejor UX
    if (file.type !== 'application/pdf') {
      setStatusMessage('Por favor, selecciona un archivo PDF válido.');
      return;
    }

    setIsUploading(true);
    setStatusMessage('Procesando y vectorizando...');

    // Preparamos el archivo para enviarlo
    const formData = new FormData();
    formData.append('file', file);

    try {
      // Uso de variable de entorno con fallback a localhost
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/ingest`, {
        method: 'POST',
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
      // Limpiamos el input para permitir subir el mismo archivo de nuevo si es necesario
      event.target.value = ''; 
    }
  };

  return (
    <div className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors">
      <label className="flex flex-col items-center cursor-pointer w-full text-center">
        {isUploading ? (
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin mb-2" />
        ) : (
          <UploadCloud className="w-10 h-10 text-gray-500 mb-2" />
        )}
        
        <span className="text-sm font-medium text-gray-700">
          {isUploading ? 'Vectorizando documento...' : 'Haz clic para subir feedback (PDF)'}
        </span>
        
        <input 
          type="file" 
          accept=".pdf" 
          className="hidden" 
          onChange={handleFileUpload}
          disabled={isUploading}
        />
      </label>

      {statusMessage && (
        <div className="mt-4 flex items-center text-sm text-gray-700 font-medium">
          {statusMessage.includes('Éxito') && <CheckCircle className="w-4 h-4 text-green-500 mr-2" />}
          {statusMessage}
        </div>
      )}
    </div>
  );
}