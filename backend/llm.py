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

<contexto>
{context}
</contexto>

<reglas_de_analisis>
1. Tu única fuente de información es el <contexto>.
2. Usa el historial de conversación solo para entender el contexto (ej. si el usuario dice "ese producto").
3. Agrupa los fragmentos de una misma reseña. NO dupliques productos en tu respuesta final.
4. Si la pregunta es sobre el mejor/peor producto, enumera TODOS los que compartan la misma calificación.
</reglas_de_analisis>
"""),
    MessagesPlaceholder(variable_name="chat_history"), 
    ("human", """{question}

<instruccion_de_formato_obligatoria>
Si la pregunta requiere listar productos (como los mejores o los peores), DEBES seguir estos pasos al pie de la letra:

PASO 1: Determina internamente cuántos productos vas a listar y si el usuario pregunta por los "mejores" o los "peores".
PASO 2: Escribe la frase introductoria EXACTA dependiendo de la cantidad y la pregunta:
   - Si es UN SOLO producto y es el MEJOR: "El producto con la mejor valoración es:"
   - Si son DOS O MÁS productos y son los MEJORES: "Los productos con las mejores valoraciones son:"
   - Si es UN SOLO producto y es el PEOR: "El producto con la peor valoración es:"
   - Si son DOS O MÁS productos y son los PEORES: "Los productos con las peores valoraciones son:"
PASO 3: Deja una línea en blanco.
PASO 4: Muestra la lista de productos usando guiones (-). Incluye el nombre, ID, la cantidad de valoraciones y la calificación exacta (ej. "con 3 valoraciones de 5/5" o "con 1 valoración de 2/5").

ESTÁ ESTRICTAMENTE PROHIBIDO resumir o mencionar los productos antes de la lista. Aplica la frase correcta del Paso 2 según corresponda.
</instruccion_de_formato_obligatoria>""")
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