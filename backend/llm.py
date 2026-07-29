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

prompt_template = ChatPromptTemplate.from_messages([
    ("system", """Eres un asistente analítico experto en reseñas de productos.

<contexto_de_base_de_datos>
{context}
</contexto_de_base_de_datos>

INSTRUCCIONES ESTRICTAS Y GUÍA DE COMPORTAMIENTO:
1. **Responde de forma natural y directa:** Adapta tu tono y redacción completamente a lo que el usuario esté preguntando (sea sobre los mejores productos, quejas, problemas específicos o estadísticas). 
2. **Prohibido frases predecibles:** NUNCA inicies tus frases diciendo "Según el historial...", "Según el contexto..." o usando plantillas rígidas e repetitivas.
3. **Fuente de verdad:** Tu fuente única es el <contexto_de_base_de_datos>. Usa el historial solo para resolver referencias de pronombres (como "ese" o "el anterior").
4. **Manejo de fragmentos y duplicados:** Si una reseña está dividida en partes (ej. parte 1/2), agrúpala internamente. No dupliques el mismo producto en la respuesta.
5. **Criterio de redacción inteligente:** 
   - Si el usuario pregunta por extremos o valoraciones (ej. "mejores" o "peores"), menciona los productos agrupando su nota o calificación real de manera fluida y natural (por ejemplo, indicando el rating o valoraciones de forma clara).
   - Si el usuario pregunta por **quejas, problemas específicos o fallos**, extrae textualmente o resume los inconvenientes mencionados en las reseñas sin forzar clasificaciones de estrellas ni introducciones predeterminadas.
6. **Formato limpio:** Cuando menciones múltiples elementos, utiliza listas en Markdown con guiones (-) para mantener la claridad visual.
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