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

# El nuevo ChatPromptTemplate con instrucciones claras y sin bucles lógicos
prompt_template = ChatPromptTemplate.from_messages([
    ("system", """Eres un asistente analítico experto en reseñas de productos.

<contexto_de_base_de_datos>
{context}
</contexto_de_base_de_datos>

INSTRUCCIONES ESTRICTAS:
1. Responde SIEMPRE de forma directa, clara y natural.
2. NUNCA inicies tus frases diciendo "Según el historial..." o "Según el contexto de la base de datos...". Simplemente da la respuesta.
3. Tu fuente principal y absoluta de información es el <contexto_de_base_de_datos>. Úsalo para responder a las preguntas sobre productos, quejas o valoraciones.
4. Usa el historial de la conversación ÚNICAMENTE para entender el contexto si el usuario usa palabras como "ese", "esos" o "el producto anterior".
"""),
    MessagesPlaceholder(variable_name="chat_history"), 
    ("human", "{question}")
])

rag_chain = prompt_template | llm

async def generate_insight(context: str, question: str, chat_history: list = []) -> str:
    # Ahora pasamos también el chat_history
    response = await rag_chain.ainvoke({
        "context": context, 
        "chat_history": chat_history,
        "question": question
    })
    return response.content

async def stream_insight(context: str, question: str, chat_history: list = []):
    # astream() funciona igual, pero recibe el chat_history
    async for chunk in rag_chain.astream({
        "context": context, 
        "chat_history": chat_history,
        "question": question
    }):
        if chunk.content:
            yield chunk.content