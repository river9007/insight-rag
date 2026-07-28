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

# El nuevo ChatPromptTemplate con las instrucciones estrictas corregidas
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

rag_chain = prompt_template | llm

async def generate_insight(context: str, question: str, chat_history: list = []) -> str:
    # Llamada real al LLM para obtener la respuesta completa
    response = await rag_chain.ainvoke({
        "context": context, 
        "chat_history": chat_history,
        "question": question
    })
    return response.content

async def stream_insight(context: str, question: str, chat_history: list = []):
    # Llamada real al LLM para el efecto de escritura en vivo (streaming)
    async for chunk in rag_chain.astream({
        "context": context, 
        "chat_history": chat_history,
        "question": question
    }):
        if chunk.content:
            yield chunk.content