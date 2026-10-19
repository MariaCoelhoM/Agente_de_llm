from langgraph.checkpoint.memory import InMemorySaver

from src.grafo import obter_grafo
from src.llm import LLMSimulado

grafo = obter_grafo(LLMSimulado([]), InMemorySaver()).get_graph()
print("NÓS")
for nome in grafo.nodes:
    print(f"  {nome}")
print("ARESTAS")
for e in grafo.edges:
    print(f"  {e.source} -> {e.target}" + ("   [condicional]" if e.conditional else ""))