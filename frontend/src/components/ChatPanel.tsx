"use client";

import DocumentUploader from './DocumentUploader';
import InsightChat from './InsightChat';

interface ChatPanelProps {
  onUploadSuccess: () => void;
}

export default function ChatPanel({ onUploadSuccess }: ChatPanelProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col h-[750px]">
      {/* Subida de documentos */}
      <div className="mb-4 flex-shrink-0">
        <DocumentUploader onUploadSuccess={onUploadSuccess} />
      </div>

      {/* Interfaz visual del Chat Streaming (flex-1 y flex flex-col aseguran que no colapse) */}
      <div className="flex-1 flex flex-col min-h-0">
        <InsightChat />
      </div>
    </div>
  );
}