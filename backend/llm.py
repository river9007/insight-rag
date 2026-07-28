# Archivo: backend/llm.py
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

prompt_template = ChatPromptTemplate.from_messages([
    ("system", """Eres un asistente analítico experto en reseñas de productos.

<contexto_de_base_de_datos>
{context}
</contexto_de_base_de_datos>

INSTRUCCIONES ESTRICTAS:
1. Tu principal fuente de verdad es el <contexto_de_base_de_datos>. Úsalo como prioridad absoluta para responder a TODAS las preguntas sobre productos, quejas, características o valoraciones.
2. Utiliza el historial de conversación ÚNICAMENTE para mantener el contexto de la charla (por ejemplo, si el usuario dice "ese producto", busca a qué producto se refería en el mensaje anterior).
3. Nunca inicies tus frases diciendo "Según el historial..." o "Según el contexto...". Responde de forma directa y natural.
4. Si la respuesta no está en el <contexto_de_base_de_datos>, indica claramente que no tienes esa información. No inventes datos.
"""),
    MessagesPlaceholder(variable_name="chat_history"), 
    ("human", "{question}")
])

# 👇 DEBES AGREGAR ESTAS FUNCIONES QUE TU main.py ESTÁ INTENTANDO IMPORTAR 👇

async def generate_insight(question: str, context: str, chat_history: list):
    # Aquí va tu lógica síncrona para llamar al LLM
    pass

async def stream_insight(question: str, context: str, chat_history: list):
    # Aquí va tu lógica de streaming (SSE) para llamar al LLM
    pass