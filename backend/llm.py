# Archivo: backend/llm.py
import os
import json
import asyncio
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# Inicializamos la conexión con Groq usando el modelo Llama 3 Open Source
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.1-8b-instant", 
    temperature=0
)

# --- NUEVO: SISTEMA DE REFORMULACIÓN DE CONSULTAS (QUERY REWRITER) ---
contextualize_q_system_prompt = (
    "Dada la siguiente conversación y la última pregunta del usuario, "
    "que podría hacer referencia a un contexto o producto mencionado anteriormente en el historial, "
    "formula una pregunta independiente (standalone) que pueda entenderse perfectamente sin el historial. "
    "NO respondas a la pregunta, SOLO reformúlala para incluir los sustantivos explícitos (ej. nombres de productos). "
    "Si la pregunta ya es clara por sí misma, devuélvela tal cual. "
    "Tu respuesta debe contener ÚNICAMENTE la pregunta reformulada, sin saludos, explicaciones ni comillas."
)

query_rewriter_prompt = ChatPromptTemplate.from_messages([
    ("system", contextualize_q_system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}")
])

query_rewriter_chain = query_rewriter_prompt | llm | StrOutputParser()

async def rewrite_query(question: str, chat_history: list = []) -> str:
    """Reformula la pregunta basándose en el historial para mejorar la búsqueda vectorial."""
    if not chat_history:
        return question
    response = await query_rewriter_chain.ainvoke({
        "chat_history": chat_history,
        "question": question
    })
    return response.strip()

# --- MODIFICADO: PROMPT MEJORADO CON REGLA 9 (FALLBACK) Y REGLA 10 (SIN FUENTES REDUNDANTES) ---
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
5. **Manejo de fragmentos y duplicados:** Si una reseña está dividida en varias partes (ej. "parte 1/3", "parte 2/3"), trátalas como UNA SOLA reseña con UNA SOLA calificación real — nunca multipliques ni cuentes la misma calificación más de una vez por tener varios fragmentos. No digas frases como "3 valoraciones de 5/5" cuando en realidad es una única reseña fragmentada; menciona el producto una sola vez con su única calificación.
6. **Manejo riguroso de extremos y empates:** Si la pregunta pide identificar un extremo (el "mejor", "peor", "más alto", "más bajo", "top" valorado, etc.), revisa TODO el <contexto_de_base_de_datos> antes de responder y enumera TODOS los productos que compartan esa calificación extrema. Si hay un empate, menciona cada producto empatado explícitamente — nunca te detengas en el primero que encuentres ni asumas que es el único.
7. **Criterio de redacción inteligente según la intención:**
   - Si el usuario pregunta por notas o valoraciones, menciona los productos agrupando su nota o calificación real de manera fluida.
   - Si el usuario pregunta por **quejas, problemas específicos o fallos**, extrae o resume los inconvenientes mencionados en las reseñas de forma directa.
8. **Formato limpio obligatorio:** Cuando la respuesta incluya más de un elemento (varios productos, varias quejas, varios puntos), preséntalos siempre como una lista en Markdown utilizando guiones ("- "). No los redactes como una sola oración corrida separada por comas.
9. **GESTIÓN DE AUSENCIA DE PROBLEMAS (FALLBACK CONDICIONAL):** Si el usuario pregunta por defectos o problemas de un producto, y en el <contexto_de_base_de_datos> NO existe ninguna queja, calificación baja ni problema reportado para ese producto, DEBES responder de esta manera: 'No se encontraron reseñas negativas ni problemas reportados para [Nombre del Producto] en la base de datos actual.' Inmediatamente después de eso, DE FORMA PROACTIVA, puedes sugerir: 'Sin embargo, si buscas productos con áreas de mejora, el contexto señala que [Otro Producto presente en el contexto] tiene problemas con [Defecto reportado].' NUNCA inventes problemas.
10. **PROHIBIDO INCLUIR FUENTES EN EL TEXTO:** NUNCA generes una sección al final de tu respuesta llamada "Fuentes utilizadas:", ni listes los IDs con sus estrellas (ejemplo: "PROD-1001 ★ 5"). El sistema (frontend) se encarga de inyectar y listar los metadatos de las fuentes automáticamente a través del canal de streaming.
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

async def stream_insight(context: str, question: str, chat_history: list = [], sources: list = None):
    async for chunk in rag_chain.astream({
        "context": context, 
        "chat_history": chat_history,
        "question": question
    }):
        if chunk.content:
            yield chunk.content
            # await asyncio.sleep(0.02) # 👈 2. Retraso artificial de 20 milisegundos por token
            
    if sources:
        sources_json = json.dumps(sources)
        yield f"|||SOURCES|||{sources_json}"