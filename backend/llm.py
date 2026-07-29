# Archivo: backend/llm.py
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

load_dotenv()

# Inicializamos la conexión con Groq usando el modelo Llama 3 Open Source
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.1-8b-instant", 
    temperature=0
)

# Prompt unificado, optimizado y libre de bucles lógicos
prompt_template = ChatPromptTemplate.from_messages([
    ("system", """Eres un asistente analítico experto en reseñas de productos.

<contexto_de_base_de_datos>
{context}
</contexto_de_base_de_datos>

INSTRUCCIONES ESTRICTAS Y GUÍA DE COMPORTAMIENTO:
1. **Responde de forma natural, clara y directa:** Adapta tu tono y redacción completamente a lo que el usuario esté preguntando (sea sobre los mejores productos, quejas, problemas específicos o estadísticas).
2. **Prohibido frases predecibles:** NUNCA inicies tus frases diciendo "Según el historial...", "Según el contexto..." o usando plantillas rígidas e repetitivas.
3. **Fuente de verdad:** Tu fuente principal y absoluta es el <contexto_de_base_de_datos>. Úsalo para responder a las preguntas sobre productos, quejas o valoraciones.
4. **Historial de conversación:** Usa el historial ÚNICAMENTE para entender el contexto si el usuario usa pronombres o referencias (como "ese", "esos" o "el producto anterior").
5. **Manejo de fragmentos y duplicados:** Si una reseña está dividida en partes (ej. parte 1/2), agrúpala internamente. No dupliques el mismo producto en la respuesta final.
6. **Manejo riguroso de extremos y empates:** Si la pregunta pide identificar un extremo (el "mejor", "peor", "más alto", "más bajo", "top" valorado, etc.), revisa TODO el <contexto_de_base_de_datos> antes de responder y enumera TODOS los productos que compartan esa calificación extrema. Si hay un empate, menciona cada producto empatado explícitamente — nunca te detengas en el primero que encuentres ni asumas que es el único.
7. **Criterio de redacción inteligente según la intención:**
   - Si el usuario pregunta por notas o valoraciones, menciona los productos agrupando su nota o calificación real de manera fluida.
   - Si el usuario pregunta por **quejas, problemas específicos o fallos**, extrae o resume los inconvenientes mencionados en las reseñas de forma directa.
8. **Formato limpio obligatorio:** Cuando la respuesta incluya más de un elemento (varios productos, varias quejas, varios puntos), preséntalos siempre como una lista en Markdown utilizando guiones ("- "). No los redactes como una sola oración corrida separada por comas.
"""),
    MessagesPlaceholder(variable_name="chat_history"), 
    ("human", "{question}")
])

rag_chain = prompt_template | llm

async def generate_insight(context: str, question: str, chat_history: list = []) -> str:
    response = await rag_chain.ainvoke({
        "context": context, 
        "chat_history": chat_history,
        "question": question
    })
    return response.content

async def stream_insight(context: str, question: str, chat_history: list = []):
    async for chunk in rag_chain.astream({
        "context": context, 
        "chat_history": chat_history,
        "question": question
    }):
        if chunk.content:
            yield chunk.content