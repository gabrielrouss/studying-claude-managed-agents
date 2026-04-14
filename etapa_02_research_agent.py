"""
Etapa 2: Research Agent Especializado
======================================

CONCEITOS APRENDIDOS:
- System prompts especializados: como moldar o comportamento do agente
- Tool configuration: habilitar/desabilitar tools especificas
- web_search e web_fetch: agente pesquisando na internet autonomamente
- Agent como "persona": cada agente tem um papel definido

NOVIDADES EM RELACAO A ETAPA 1:
- Na etapa 1 usamos agent_toolset_20260401 sem configuracao (todas tools ON)
- Agora vamos SELECIONAR quais tools habilitar via "configs"
- O system prompt e muito mais detalhado e direcionado
- O agente usa web_search/web_fetch para pesquisar na internet

REQUISITOS:
- export ANTHROPIC_API_KEY="sua-chave-aqui"
- pip install anthropic>=0.52.0
"""

from anthropic import Anthropic

# System prompt detalhado para o Research Agent.
# DICA: System prompts especializados sao a principal forma de controlar
# o comportamento de um agente. Quanto mais especifico, melhor o resultado.
RESEARCH_SYSTEM_PROMPT = """\
Voce e um Research Analyst especializado em marketing digital.

## Seu papel
Voce pesquisa temas relacionados a marketing, tendencias de mercado,
comportamento do consumidor e estrategias de conteudo.

## Como trabalhar
1. Ao receber um briefing, PRIMEIRO pesquise na web por informacoes atuais
2. Busque dados de MULTIPLAS fontes para ter visao completa
3. Organize os achados em um relatorio estruturado
4. Salve o relatorio em /workspace/research/

## Formato do relatorio
Salve como markdown com esta estrutura:
- Resumo executivo (3-5 linhas)
- Pontos-chave encontrados (bullets)
- Dados e estatisticas relevantes
- Fontes consultadas
- Insights para criacao de conteudo

## Regras
- Sempre cite as fontes
- Foque em dados atuais (2024-2026)
- Escreva em portugues brasileiro
- Seja objetivo e factual
"""


def main():
    client = Anthropic()

    print("=" * 60)
    print("ETAPA 2: Research Agent Especializado")
    print("=" * 60)

    # =========================================================================
    # PASSO 1: Criar Agent com tools SELECIONADAS
    # =========================================================================
    # CONCEITO NOVO: Tool configuration
    #
    # Em vez de habilitar tudo com agent_toolset_20260401, podemos:
    #
    # Estrategia A - Desabilitar tools especificas:
    #   configs: [{"name": "web_fetch", "enabled": false}]
    #
    # Estrategia B - Comecar com tudo OFF e habilitar apenas o necessario:
    #   default_config: {"enabled": false}
    #   configs: [{"name": "bash", "enabled": true}, ...]
    #
    # Para o Research Agent, queremos:
    # - web_search: ON (pesquisar na internet)
    # - web_fetch: ON (buscar conteudo de URLs)
    # - write: ON (salvar relatorios em arquivos)
    # - read: ON (ler arquivos existentes)
    # - bash: ON (criar diretorios, etc.)
    # - edit: OFF (nao precisa editar arquivos existentes)
    # - glob: OFF (nao precisa buscar por padrao de nome)
    # - grep: OFF (nao precisa buscar por conteudo)
    print("\n[1/4] Criando Research Agent com tools selecionadas...")
    agent = client.beta.agents.create(
        name="Research Agent - Marketing",
        model="claude-sonnet-4-6",
        system=RESEARCH_SYSTEM_PROMPT,
        tools=[
            {
                "type": "agent_toolset_20260401",
                # Estrategia B: tudo OFF por padrao, habilitar apenas o necessario
                "default_config": {"enabled": False},
                "configs": [
                    {"name": "web_search", "enabled": True},
                    {"name": "web_fetch", "enabled": True},
                    {"name": "write", "enabled": True},
                    {"name": "read", "enabled": True},
                    {"name": "bash", "enabled": True},
                ],
            },
        ],
    )
    print(f"    Agent criado!")
    print(f"    ID:      {agent.id}")
    print(f"    Version: {agent.version}")

    # =========================================================================
    # PASSO 2: Criar Environment
    # =========================================================================
    # Networking unrestricted e necessario para web_search/web_fetch
    # funcionarem sem restricoes. Em producao, voce usaria "limited"
    # com allowed_hosts especificos.
    print("\n[2/4] Criando Environment...")
    environment = client.beta.environments.create(
        name="research-env",
        config={
            "type": "cloud",
            "networking": {"type": "unrestricted"},
        },
    )
    print(f"    Environment criado! ID: {environment.id}")

    # =========================================================================
    # PASSO 3: Criar Session e enviar briefing de pesquisa
    # =========================================================================
    print("\n[3/4] Criando Session...")
    session = client.beta.sessions.create(
        agent=agent.id,
        environment_id=environment.id,
        title="Pesquisa: IA no Marketing de Conteudo",
    )
    print(f"    Session criada! ID: {session.id}")

    # =========================================================================
    # PASSO 4: Enviar briefing e processar stream
    # =========================================================================
    # O briefing e a "tarefa" que damos ao agente.
    # Note como e diferente do system prompt:
    # - System prompt = QUEM voce e (personalidade, regras, formato)
    # - User message = O QUE fazer (a tarefa especifica desta vez)
    briefing = (
        "Pesquise sobre o uso de Inteligencia Artificial na criacao de "
        "conteudo para marketing digital em 2025-2026. Quero entender:\n"
        "1. Quais as principais ferramentas de IA para criacao de conteudo?\n"
        "2. Como empresas estao usando IA para personalizar conteudo?\n"
        "3. Quais os riscos e limitacoes?\n"
        "4. Tendencias emergentes para os proximos anos.\n\n"
        "Salve o relatorio completo em /workspace/research/ia_marketing_2025.md"
    )

    print(f"\n[4/4] Enviando briefing de pesquisa...")
    print(f"    Briefing: {briefing[:80]}...")
    print("-" * 60)

    with client.beta.sessions.events.stream(session.id) as stream:
        client.beta.sessions.events.send(
            session.id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": briefing}],
                },
            ],
        )

        # Processar eventos - agora com foco em observar as tools de pesquisa
        tool_count = 0
        for event in stream:
            match event.type:
                case "agent.message":
                    for block in event.content:
                        if hasattr(block, "text"):
                            print(f"\n[AGENT] {block.text}")

                case "agent.tool_use":
                    tool_count += 1
                    tool_name = event.name

                    # Destaque visual para web tools
                    if tool_name in ("web_search", "web_fetch"):
                        print(f"\n🔍 [WEB] {tool_name}")
                        if hasattr(event, "input") and event.input:
                            # Para web_search, mostrar a query
                            input_dict = event.input
                            if isinstance(input_dict, dict):
                                query = input_dict.get(
                                    "query", input_dict.get("url", "")
                                )
                                print(f"         Query/URL: {query}")
                    else:
                        print(f"\n[TOOL #{tool_count}] {tool_name}")
                        if hasattr(event, "input") and event.input:
                            input_str = str(event.input)
                            if len(input_str) > 150:
                                input_str = input_str[:150] + "..."
                            print(f"         Input: {input_str}")

                case "agent.tool_result":
                    status = "OK" if not event.is_error else "ERRO"
                    print(f"         Resultado: {status}")

                case "session.status_idle":
                    print("\n" + "-" * 60)
                    print(f"[SESSION] Agente terminou! ({tool_count} tool calls)")
                    if hasattr(event, "stop_reason") and event.stop_reason:
                        print(f"          Stop reason: {event.stop_reason.type}")
                    break

                case "session.status_running":
                    pass  # Silenciar para reduzir ruido

                case "span.model_request_end":
                    if hasattr(event, "model_usage") and event.model_usage:
                        usage = event.model_usage
                        print(
                            f"[USAGE]  Input: {usage.input_tokens}, "
                            f"Output: {usage.output_tokens} tokens"
                        )

    # =========================================================================
    # CLEANUP
    # =========================================================================
    print("\n" + "=" * 60)
    print("CLEANUP")
    print("=" * 60)
    client.beta.agents.archive(agent.id)
    print(f"Agent arquivado")

    try:
        client.beta.environments.delete(environment.id)
        print(f"Environment deletado")
    except Exception as e:
        print(f"Environment: {e}")

    print("\nEtapa 2 concluida com sucesso!")


if __name__ == "__main__":
    main()
