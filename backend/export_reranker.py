import os
from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import AutoTokenizer

# Definir la raíz del proyecto (un nivel arriba de backend/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# Se guarda en la raíz del proyecto: <proyecto>/onnx_reranker_fp32
OUTPUT_DIR = os.path.join(BASE_DIR, "onnx_reranker_fp32")

def export_fp32():
    print(f"📦 Exportando '{MODEL_NAME}' a ONNX FP32 optimizado...")
    
    # Exportar a ONNX FP32 nativo
    model = ORTModelForSequenceClassification.from_pretrained(
        MODEL_NAME, 
        export=True
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    # Guardar en disco
    tokenizer.save_pretrained(OUTPUT_DIR)
    model.save_pretrained(OUTPUT_DIR)

    print(f"✅ ¡Completado! Modelo ONNX FP32 guardado en: '{OUTPUT_DIR}'")

if __name__ == "__main__":
    export_fp32()