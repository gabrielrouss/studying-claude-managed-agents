"""
Etapa 5: Multi-Agent Orchestrator - Content Factory
=====================================================

CONCEITOS APRENDIDOS:
- Multi-Agent: um agente coordenador delega para sub-agentes
- callable_agents: como declarar quais agentes podem ser chamados
- Threads: cada sub-agente roda em sua propria thread isolada
- Eventos multi-agent: thread_created, thread_message_sent/received, thread_idle
- Container compartilhado: todos os agentes compartilham o mesmo filesystem
- try/finally para cleanup: evitar vazamento de recursos em caso de erro

NOVIDADES EM RELACAO AS ETAPAS ANTERIORES:
- NAO simulamos mais dados - o pipeline e END-TO-END
- O Orchestrator decide quando e como delegar
- Cada sub-agente tem sua propria thread com contexto isolado
- O stream da session mostra atividade de todas as threads

NOTA: Multi-Agent e um Research Preview feature.
Pode necessitar de acesso adicional.

REQUISITOS:
- export ANTHROPIC_API_KEY="sua-chave-aqui"
- pip install anthropic>=0.92.0
- Acesso ao Research Preview de multi-agent (solicitar em claude.com/form/claude-managed-agents)
"""

from anthropic import Anthropic

# =============================================================================
# SYSTEM PROMPTS DOS SUB-AGENTES
# =============================================================================
# Os mesmos das etapas anteriores, agora centralizados aqui.

RESEARCH_SYSTEM_PROMPT = """\
Voce e um Research Analyst especializado em marketing digital.

## Seu papel
Voce pesquisa temas na web e gera relatorios estruturados.

## Como trabalhar
1. Pesquise na web por informacoes atuais sobre o tema solicitado
2. Busque dados de multiplas fontes
3. Organize em relatorio estruturado
4. Salve em /workspace/research/

## Formato do relatorio
Markdown com: resumo executivo, pontos-chave, dados/estatisticas, fontes,
insights para criacao de conteudo.

## Regras
- Cite as fontes
- Foque em dados atuais (2024-2026)
- Portugues brasileiro
- Seja objetivo e factual
"""

WRITER_SYSTEM_PROMPT = """\
Voce e um Copywriter Senior de marketing de conteudo.

## Seu papel
Voce transforma pesquisas em artigos envolventes. NAO pesquisa, apenas escreve.

## Como trabalhar
1. Leia o material em /workspace/research/
2. Escreva artigo de blog completo (800-1200 palavras)
3. Salve em /workspace/content/artigo.md

## Estilo
- Profissional mas acessivel
- Titulo impactante, subtitulos claros
- Dados da pesquisa para credibilidade
- Introducao que prende, CTA no final
- Portugues brasileiro
"""

ADAPTER_SYSTEM_PROMPT = """\
Voce e um Social Media Specialist que adapta conteudo para multiplos canais.

## Seu papel
Leia o artigo em /workspace/content/artigo.md e adapte para 4 canais.

## Canais e Regras

### LinkedIn -> /workspace/channels/linkedin.md
Tom profissional, max 1300 chars, hook na primeira linha, 3-5 hashtags.

### Instagram -> /workspace/channels/instagram.md
Tom casual/inspirador, max 2200 chars, emojis, 20-30 hashtags, sugestao de carrossel.

### Twitter/X -> /workspace/channels/twitter.md
Thread de 5-8 tweets (280 chars cada), numerados, direto e provocativo.

### Email -> /workspace/channels/email.md
Subject line (50 chars), preview text (90 chars), corpo 300-500 palavras, PS bonus.

## Regras
- Cada canal deve parecer NATIVO daquela plataforma
- Portugues brasileiro
- Nao repita texto entre canais
"""

# =============================================================================
# SYSTEM PROMPT DO ORCHESTRATOR
# =============================================================================
# Este e o agente COORDENADOR. Ele NAO faz o trabalho - ele DELEGA.
# O system prompt instrui a ORDEM da delegacao e o que esperar de cada agente.
ORCHESTRATOR_SYSTEM_PROMPT = """\
Voce e o Content Director, lider de uma equipe de agentes de marketing.

## Sua equipe
Voce coordena 3 agentes especializados:
1. **Research Agent**: pesquisa temas na web e salva em /workspace/research/
2. **Writer Agent**: le pesquisa e escreve artigos em /workspace/content/
3. **Adapter Agent**: le artigos e adapta para canais em /workspace/channels/

## Fluxo de trabalho
Ao receber um briefing do usuario, execute NESTA ORDEM:

### Fase 1: Pesquisa
- Delegue ao Research Agent com instrucoes claras sobre o que pesquisar
- Aguarde a conclusao antes de prosseguir

### Fase 2: Escrita
- Delegue ao Writer Agent pedindo para ler /workspace/research/ e escrever
- Aguarde a conclusao antes de prosseguir

### Fase 3: Adaptacao
- Delegue ao Adapter Agent pedindo para adaptar /workspace/content/artigo.md
- Aguarde a conclusao

### Fase 4: Entrega
- Liste todos os arquivos gerados em /workspace/channels/
- Apresente um resumo ao usuario do que foi produzido

## Regras
- SEMPRE delegue na ordem: Research -> Writer -> Adapter
- Forneca instrucoes CLARAS e ESPECIFICAS a cada agente
- NAO tente fazer o trabalho voce mesmo - DELEGUE
- Ao final, faca um resumo do que foi produzido
- Portugues brasileiro
"""


def main():
    client = Anthropic()

    print("=" * 60)
    print("ETAPA 5: Multi-Agent Orchestrator - Content Factory")
    print("=" * 60)

    # =========================================================================
    # Rastrear recursos criados para cleanup no finally
    # =========================================================================
    # CONCEITO: try/finally garante que recursos sao limpos mesmo em caso
    # de erro. Sem isso, agents e environments ficam orfaos na sua conta.
    research_agent = None
    writer_agent = None
    adapter_agent = None
    orchestrator = None
    environment = None

    try:
        # =====================================================================
        # PASSO 1: Criar os 3 sub-agentes
        # =====================================================================
        # Cada sub-agente e criado independentemente, com seu proprio
        # system prompt e configuracao de tools.
        # O Orchestrator os referencia por ID via callable_agents.
        print("\n[1/5] Criando sub-agentes...")

        # Research Agent - com web tools
        research_agent = client.beta.agents.create(
            name="Research Agent",
            model="claude-sonnet-4-6",
            system=RESEARCH_SYSTEM_PROMPT,
            tools=[
                {
                    "type": "agent_toolset_20260401",
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
        print(f"    Research Agent: {research_agent.id} (v{research_agent.version})")

        # Writer Agent - sem web, com file ops
        writer_agent = client.beta.agents.create(
            name="Writer Agent",
            model="claude-sonnet-4-6",
            system=WRITER_SYSTEM_PROMPT,
            tools=[
                {
                    "type": "agent_toolset_20260401",
                    "default_config": {"enabled": False},
                    "configs": [
                        {"name": "read", "enabled": True},
                        {"name": "write", "enabled": True},
                        {"name": "edit", "enabled": True},
                        {"name": "bash", "enabled": True},
                        {"name": "glob", "enabled": True},
                    ],
                },
            ],
        )
        print(f"    Writer Agent:   {writer_agent.id} (v{writer_agent.version})")

        # Adapter Agent - sem web, com file ops
        adapter_agent = client.beta.agents.create(
            name="Adapter Agent",
            model="claude-sonnet-4-6",
            system=ADAPTER_SYSTEM_PROMPT,
            tools=[
                {
                    "type": "agent_toolset_20260401",
                    "default_config": {"enabled": False},
                    "configs": [
                        {"name": "read", "enabled": True},
                        {"name": "write", "enabled": True},
                        {"name": "edit", "enabled": True},
                        {"name": "bash", "enabled": True},
                        {"name": "glob", "enabled": True},
                    ],
                },
            ],
        )
        print(f"    Adapter Agent:  {adapter_agent.id} (v{adapter_agent.version})")

        # =====================================================================
        # PASSO 2: Criar o Orchestrator com callable_agents
        # =====================================================================
        # CONCEITO NOVO: callable_agents
        #
        # O campo callable_agents lista os agentes que este agente pode invocar.
        # Cada entry precisa de:
        # - type: "agent"
        # - id: o agent ID
        # - version: a versao do agent (para garantir consistencia)
        #
        # IMPORTANTE:
        # - Apenas 1 nivel de delegacao (orquestrador -> sub-agente)
        # - Sub-agentes NAO podem chamar outros sub-agentes
        # - Todos compartilham o mesmo container/filesystem
        # - Cada sub-agente roda em sua propria THREAD com contexto isolado
        print("\n[2/5] Criando Orchestrator com callable_agents...")
        orchestrator = client.beta.agents.create(
            name="Content Director - Orchestrator",
            model="claude-sonnet-4-6",
            system=ORCHESTRATOR_SYSTEM_PROMPT,
            tools=[
                {
                    "type": "agent_toolset_20260401",
                    "default_config": {"enabled": False},
                    "configs": [
                        # O orchestrator precisa de bash/read/glob para
                        # verificar outputs e listar arquivos no final
                        {"name": "bash", "enabled": True},
                        {"name": "read", "enabled": True},
                        {"name": "glob", "enabled": True},
                    ],
                },
            ],
            # AQUI: declarar os sub-agentes que podem ser chamados
            callable_agents=[
                {
                    "type": "agent",
                    "id": research_agent.id,
                    "version": research_agent.version,
                },
                {
                    "type": "agent",
                    "id": writer_agent.id,
                    "version": writer_agent.version,
                },
                {
                    "type": "agent",
                    "id": adapter_agent.id,
                    "version": adapter_agent.version,
                },
            ],
        )
        print(f"    Orchestrator:   {orchestrator.id} (v{orchestrator.version})")
        print(
            f"    Sub-agentes:    {len(orchestrator.callable_agents)} registrados"
        )

        # =====================================================================
        # PASSO 3: Criar Environment
        # =====================================================================
        print("\n[3/5] Criando Environment...")
        environment = client.beta.environments.create(
            name="content-factory-env",
            config={
                "type": "cloud",
                "networking": {"type": "unrestricted"},
            },
        )
        print(f"    Environment: {environment.id}")

        # =====================================================================
        # PASSO 4: Criar Session com o Orchestrator
        # =====================================================================
        # A session referencia APENAS o orchestrator.
        # Os callable_agents sao resolvidos automaticamente a partir
        # da configuracao do orchestrator - nao precisam estar na session.
        print("\n[4/5] Criando Session...")
        session = client.beta.sessions.create(
            agent=orchestrator.id,
            environment_id=environment.id,
            title="Content Factory: IA no Marketing",
        )
        print(f"    Session: {session.id}")

        # =====================================================================
        # PASSO 5: Enviar briefing e observar orquestracao
        # =====================================================================
        # CONCEITO NOVO: Eventos multi-agent
        #
        # Alem dos eventos ja conhecidos, o stream agora inclui:
        # - session.thread_created: novo sub-agente iniciou (com thread_id)
        # - agent.thread_message_sent: orchestrator enviou msg para sub-agente
        # - agent.thread_message_received: sub-agente recebeu msg
        # - session.thread_idle: sub-agente terminou seu trabalho
        #
        # O stream da session (primary thread) mostra uma visao RESUMIDA
        # de todas as threads. Para ver detalhes de cada sub-agente,
        # voce usaria o stream de thread especifico.
        briefing = (
            "Quero produzir conteudo sobre 'O impacto da IA generativa no "
            "marketing de conteudo em 2025'. Execute o pipeline completo:\n"
            "1. Pesquise o tema na web\n"
            "2. Escreva um artigo de blog completo\n"
            "3. Adapte para LinkedIn, Instagram, Twitter/X e Email\n\n"
            "Ao final, me mostre um resumo do que foi produzido."
        )

        print(f"\n[5/5] Enviando briefing para o Content Director...")
        print(f"    Briefing: {briefing[:60]}...")
        print("=" * 60)
        print("STREAM DE EVENTOS (Multi-Agent)")
        print("=" * 60)

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

            # Processar stream com foco nos eventos multi-agent
            threads_seen = {}
            total_tools = 0

            for event in stream:
                match event.type:
                    # --- Eventos Multi-Agent ---

                    case "session.thread_created":
                        thread_id = getattr(event, "session_thread_id", "?")
                        agent_name = getattr(event, "agent_name", "Unknown")
                        threads_seen[thread_id] = agent_name
                        print(f"\n[THREAD CRIADA] {agent_name}")
                        print(f"   Thread ID: {thread_id}")

                    case "agent.thread_message_sent":
                        to_thread = getattr(event, "to_thread_id", "?")
                        target = threads_seen.get(to_thread, "Unknown")
                        print(f"\n[MSG ENVIADA] Director -> {target}")

                    case "agent.thread_message_received":
                        from_thread = getattr(event, "from_thread_id", "?")
                        source = threads_seen.get(from_thread, "Unknown")
                        print(f"\n[MSG RECEBIDA] De: {source}")

                    case "session.thread_idle":
                        thread_id = getattr(event, "session_thread_id", "?")
                        agent_name = threads_seen.get(thread_id, "Unknown")
                        print(f"\n[THREAD IDLE] {agent_name} terminou!")

                    # --- Eventos do Orchestrator ---

                    case "agent.message":
                        for block in event.content:
                            if hasattr(block, "text"):
                                print(f"\n[DIRECTOR] {block.text}")

                    case "agent.tool_use":
                        total_tools += 1
                        name = event.name
                        print(f"\n[TOOL] {name}")

                    case "agent.tool_result":
                        status = "OK" if not event.is_error else "ERRO"
                        print(f"   -> {status}")

                    # --- Eventos de Session ---

                    case "session.status_idle":
                        print("\n" + "=" * 60)
                        print("PIPELINE COMPLETO!")
                        print("=" * 60)
                        print(f"Threads criadas: {len(threads_seen)}")
                        for tid, name in threads_seen.items():
                            print(f"  - {name} ({tid[:20]}...)")
                        print(f"Tool calls (orchestrator): {total_tools}")
                        break

                    case "session.status_running":
                        pass

                    case "span.model_request_end":
                        if hasattr(event, "model_usage") and event.model_usage:
                            usage = event.model_usage
                            print(
                                f"[USAGE] In: {usage.input_tokens}, "
                                f"Out: {usage.output_tokens}"
                            )

        # =====================================================================
        # BONUS: Listar threads da session
        # =====================================================================
        print("\n" + "=" * 60)
        print("THREADS DA SESSION")
        print("=" * 60)
        try:
            for thread in client.beta.sessions.threads.list(session.id):
                print(f"  [{thread.agent_name}] Status: {thread.status}")
        except Exception as e:
            print(f"  Erro ao listar threads: {e}")

    finally:
        # =====================================================================
        # CLEANUP - SEMPRE executa, mesmo em caso de erro
        # =====================================================================
        # CONCEITO: try/finally garante que recursos sao limpos.
        # Sem isso, agents e environments orfaos ficam na conta.
        print("\n" + "=" * 60)
        print("CLEANUP")
        print("=" * 60)

        for agent_obj in [
            research_agent,
            writer_agent,
            adapter_agent,
            orchestrator,
        ]:
            if agent_obj:
                try:
                    client.beta.agents.archive(agent_obj.id)
                    print(f"  Agent {agent_obj.name} arquivado")
                except Exception:
                    pass

        if environment:
            try:
                client.beta.environments.delete(environment.id)
                print(f"  Environment deletado")
            except Exception:
                pass

        print("--- CLEANUP COMPLETO ---")

    print("\nEtapa 5 concluida com sucesso!")


if __name__ == "__main__":
    main()
