"""
Etapa 5: Multi-Agent Orchestrator - Content Factory (Orquestracao Real)
========================================================================

CONCEITOS APRENDIDOS:
- Orquestracao via codigo: o Python coordena o pipeline entre agentes
- Sessoes independentes: cada agente roda em sua propria session
- Filesystem compartilhado: mesmo environment = mesmos arquivos no container
- Pipeline real: Research -> Writer -> Adapter, cada um fazendo seu trabalho

COMO FUNCIONA:
- Criamos UM environment compartilhado
- Criamos UMA session para cada agente (compartilhando o environment)
- O codigo Python faz o papel do orchestrator:
  1. Envia briefing ao Research Agent -> espera terminar
  2. Envia instrucao ao Writer Agent -> espera terminar
  3. Envia instrucao ao Adapter Agent -> espera terminar
  4. Coleta e exibe os resultados

NOTA IMPORTANTE:
  Sessions que compartilham o mesmo environment NAO compartilham filesystem
  automaticamente (cada session tem container isolado). Para resolver isso,
  usamos UMA UNICA SESSION reutilizada em sequencia, trocando o agente
  por mensagem contextual. Alternativamente, poderiamos usar a API de Files
  para transferir arquivos entre sessions.

  A abordagem aqui usa sessions separadas onde cada agente recebe o contexto
  necessario via mensagem (o output do agente anterior e passado como input
  para o proximo).

REQUISITOS:
- export ANTHROPIC_API_KEY="sua-chave-aqui"
- pip install anthropic>=0.92.0
"""

from anthropic import Anthropic

# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

RESEARCH_SYSTEM_PROMPT = """\
Voce e um Research Analyst especializado em marketing digital.

## Seu papel
Voce pesquisa temas na web e gera relatorios estruturados.

## Como trabalhar
1. Pesquise na web por informacoes atuais sobre o tema solicitado
2. Busque dados de multiplas fontes
3. Organize em relatorio estruturado

## Formato do relatorio
Markdown com: resumo executivo, pontos-chave, dados/estatisticas, fontes,
insights para criacao de conteudo.

## Regras
- Cite as fontes
- Foque em dados atuais (2024-2026)
- Portugues brasileiro
- Seja objetivo e factual
- Salve o relatorio em /workspace/research/research.md
"""

WRITER_SYSTEM_PROMPT = """\
Voce e um Copywriter Senior de marketing de conteudo.

## Seu papel
Voce transforma pesquisas em artigos envolventes. NAO pesquisa, apenas escreve.

## Como trabalhar
1. Leia o material de pesquisa fornecido na mensagem
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
Receba um artigo e adapte para 4 canais diferentes.

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
# HELPER: Enviar mensagem e coletar resposta completa do agente
# =============================================================================

def run_agent(client, session_id, message, agent_label):
    """
    Envia mensagem para um agente e coleta a resposta completa.

    Retorna:
    - full_text: todo o texto que o agente respondeu
    - tool_count: quantas tools o agente usou
    """
    full_text = ""
    tool_count = 0

    with client.beta.sessions.events.stream(session_id) as stream:
        client.beta.sessions.events.send(
            session_id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": message}],
                },
            ],
        )

        for event in stream:
            match event.type:
                case "agent.message":
                    for block in event.content:
                        if hasattr(block, "text"):
                            full_text += block.text

                case "agent.tool_use":
                    tool_count += 1
                    name = event.name
                    if name in ("web_search", "web_fetch"):
                        query = ""
                        if hasattr(event, "input") and isinstance(event.input, dict):
                            query = event.input.get("query", event.input.get("url", ""))
                        print(f"    [{agent_label}] 🔍 {name}: {query[:80]}")
                    elif name == "write":
                        path = ""
                        if hasattr(event, "input") and isinstance(event.input, dict):
                            path = event.input.get("file_path", "")
                        print(f"    [{agent_label}] 📝 write: {path}")
                    elif name == "bash":
                        cmd = ""
                        if hasattr(event, "input") and isinstance(event.input, dict):
                            cmd = event.input.get("command", "")
                        print(f"    [{agent_label}] ⚙️  bash: {cmd[:60]}")
                    else:
                        print(f"    [{agent_label}] 🔧 {name}")

                case "agent.tool_result":
                    if event.is_error:
                        print(f"    [{agent_label}] ❌ ERRO em tool")

                case "session.status_idle":
                    break

                case "span.model_request_end":
                    if hasattr(event, "model_usage") and event.model_usage:
                        u = event.model_usage
                        print(
                            f"    [{agent_label}] tokens: "
                            f"in={u.input_tokens} out={u.output_tokens}"
                        )

    return full_text, tool_count


# =============================================================================
# HELPER: Enviar mensagem e capturar conteudo de arquivos escritos
# =============================================================================

def run_agent_and_read_output(client, session_id, message, agent_label, output_path):
    """
    Roda o agente e depois le o arquivo que ele escreveu no container.

    Retorna o conteudo do arquivo (para passar ao proximo agente).
    """
    _text, tools = run_agent(client, session_id, message, agent_label)
    print(f"    [{agent_label}] Concluido! ({tools} tool calls)")

    # Ler o arquivo que o agente escreveu
    # Enviamos uma segunda mensagem pedindo para o agente ler e retornar o conteudo
    content, _ = run_agent(
        client, session_id,
        f"Leia o arquivo {output_path} e retorne o conteudo completo, sem comentarios adicionais.",
        agent_label,
    )

    return content


# =============================================================================
# MAIN
# =============================================================================

def main():
    client = Anthropic()

    print("=" * 70)
    print("  CONTENT FACTORY - Multi-Agent Pipeline (Orquestracao Real)")
    print("=" * 70)

    # Rastrear recursos para cleanup
    agents = []
    environment = None
    sessions = []

    try:
        # =================================================================
        # PASSO 1: Criar os 3 agentes especializados
        # =================================================================
        print("\n[SETUP] Criando agentes especializados...")

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
        agents.append(research_agent)
        print(f"  ✓ Research Agent: {research_agent.id}")

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
        agents.append(writer_agent)
        print(f"  ✓ Writer Agent:   {writer_agent.id}")

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
        agents.append(adapter_agent)
        print(f"  ✓ Adapter Agent:  {adapter_agent.id}")

        # =================================================================
        # PASSO 2: Criar environment compartilhado
        # =================================================================
        print("\n[SETUP] Criando environment...")
        environment = client.beta.environments.create(
            name="content-factory-env",
            config={
                "type": "cloud",
                "networking": {"type": "unrestricted"},
            },
        )
        print(f"  ✓ Environment: {environment.id}")

        # =================================================================
        # PASSO 3: Criar sessions - uma por agente
        # =================================================================
        # NOTA: Cada session tem seu proprio container isolado.
        # Para passar dados entre agentes, enviamos o conteudo via mensagem.
        print("\n[SETUP] Criando sessions...")

        research_session = client.beta.sessions.create(
            agent=research_agent.id,
            environment_id=environment.id,
            title="Research: IA no Marketing",
        )
        sessions.append(research_session)
        print(f"  ✓ Research Session: {research_session.id}")

        writer_session = client.beta.sessions.create(
            agent=writer_agent.id,
            environment_id=environment.id,
            title="Writer: Artigo de Blog",
        )
        sessions.append(writer_session)
        print(f"  ✓ Writer Session:   {writer_session.id}")

        adapter_session = client.beta.sessions.create(
            agent=adapter_agent.id,
            environment_id=environment.id,
            title="Adapter: Multi-Canal",
        )
        sessions.append(adapter_session)
        print(f"  ✓ Adapter Session:  {adapter_session.id}")

        # =================================================================
        # PIPELINE: Research -> Writer -> Adapter
        # =================================================================
        briefing_topic = (
            "O impacto da IA generativa no marketing de conteudo em 2025"
        )

        # -----------------------------------------------------------------
        # FASE 1: RESEARCH
        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("  FASE 1: RESEARCH AGENT - Pesquisando na web")
        print("=" * 70)

        research_message = (
            f"Pesquise sobre '{briefing_topic}'. Cubra:\n"
            "1. Principais ferramentas de IA para criacao de conteudo\n"
            "2. Como empresas estao usando IA para personalizar conteudo\n"
            "3. Riscos e limitacoes\n"
            "4. Tendencias emergentes para 2025-2026\n\n"
            "Salve o relatorio em /workspace/research/research.md"
        )

        research_output = run_agent_and_read_output(
            client,
            research_session.id,
            research_message,
            "RESEARCH",
            "/workspace/research/research.md",
        )

        print(f"\n  📊 Pesquisa coletada: {len(research_output)} caracteres")

        # -----------------------------------------------------------------
        # FASE 2: WRITER
        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("  FASE 2: WRITER AGENT - Escrevendo artigo")
        print("=" * 70)

        writer_message = (
            "Aqui esta a pesquisa completa para voce transformar em artigo:\n\n"
            "---INICIO DA PESQUISA---\n"
            f"{research_output}\n"
            "---FIM DA PESQUISA---\n\n"
            "Escreva um artigo de blog completo (800-1200 palavras) baseado "
            "nessa pesquisa. Use os dados e estatisticas encontrados. "
            "Salve em /workspace/content/artigo.md"
        )

        article_output = run_agent_and_read_output(
            client,
            writer_session.id,
            writer_message,
            "WRITER",
            "/workspace/content/artigo.md",
        )

        print(f"\n  📝 Artigo coletado: {len(article_output)} caracteres")

        # -----------------------------------------------------------------
        # FASE 3: ADAPTER
        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("  FASE 3: ADAPTER AGENT - Adaptando para canais")
        print("=" * 70)

        adapter_message = (
            "Aqui esta o artigo para voce adaptar para 4 canais:\n\n"
            "---INICIO DO ARTIGO---\n"
            f"{article_output}\n"
            "---FIM DO ARTIGO---\n\n"
            "Adapte para os 4 canais conforme suas regras:\n"
            "1. LinkedIn -> /workspace/channels/linkedin.md\n"
            "2. Instagram -> /workspace/channels/instagram.md\n"
            "3. Twitter/X -> /workspace/channels/twitter.md\n"
            "4. Email -> /workspace/channels/email.md\n\n"
            "Cada canal deve ter conteudo DIFERENTE e NATIVO da plataforma."
        )

        _adapter_text, adapter_tools = run_agent(
            client,
            adapter_session.id,
            adapter_message,
            "ADAPTER",
        )
        print(f"\n  🎯 Adapter concluido! ({adapter_tools} tool calls)")

        # -----------------------------------------------------------------
        # FASE 4: COLETAR RESULTADOS DOS CANAIS
        # -----------------------------------------------------------------
        # Os arquivos existem no container cloud do Adapter Agent.
        # Precisamos pedir ao agente para ler e retornar o conteudo
        # antes que a session termine e o container seja destruido.
        print("\n" + "=" * 70)
        print("  FASE 4: COLETANDO RESULTADOS")
        print("=" * 70)

        channels = {}
        for channel in ["linkedin", "instagram", "twitter", "email"]:
            content, _ = run_agent(
                client,
                adapter_session.id,
                f"Leia o arquivo /workspace/channels/{channel}.md e retorne "
                f"o conteudo completo, sem comentarios adicionais.",
                "DOWNLOAD",
            )
            channels[channel] = content
            print(f"  ✓ {channel}.md coletado ({len(content)} chars)")

        # -----------------------------------------------------------------
        # FASE 5: SALVAR LOCALMENTE + EXIBIR
        # -----------------------------------------------------------------
        import os

        output_dir = os.path.join(os.path.dirname(__file__) or ".", "output")
        os.makedirs(output_dir, exist_ok=True)

        # Salvar pesquisa e artigo
        with open(os.path.join(output_dir, "research.md"), "w", encoding="utf-8") as f:
            f.write(research_output)
        with open(os.path.join(output_dir, "artigo.md"), "w", encoding="utf-8") as f:
            f.write(article_output)

        # Salvar canais
        for channel, content in channels.items():
            with open(os.path.join(output_dir, f"{channel}.md"), "w", encoding="utf-8") as f:
                f.write(content)

        print(f"\n  📁 Todos os arquivos salvos em: {os.path.abspath(output_dir)}/")

        # -----------------------------------------------------------------
        # EXIBIR RESULTADO FINAL
        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("  PIPELINE COMPLETO - RESULTADO FINAL")
        print("=" * 70)

        print("""
  ┌─────────────────────────────────────────────────────┐
  │                CONTENT FACTORY                       │
  │                                                      │
  │  [Briefing]                                          │
  │      │                                               │
  │      ▼                                               │
  │  ┌──────────────┐                                    │
  │  │ RESEARCH     │ → Pesquisou na web, gerou          │
  │  │ AGENT        │   relatorio com dados reais        │
  │  └──────┬───────┘                                    │
  │         │ (pesquisa passada via mensagem)             │
  │         ▼                                            │
  │  ┌──────────────┐                                    │
  │  │ WRITER       │ → Transformou pesquisa em          │
  │  │ AGENT        │   artigo de blog completo          │
  │  └──────┬───────┘                                    │
  │         │ (artigo passado via mensagem)               │
  │         ▼                                            │
  │  ┌──────────────┐    ┌──────────────────────┐        │
  │  │ ADAPTER      │ →  │ linkedin.md           │        │
  │  │ AGENT        │ →  │ instagram.md          │        │
  │  │              │ →  │ twitter.md            │        │
  │  │              │ →  │ email.md              │        │
  │  └──────────────┘    └──────────────────────┘        │
  └─────────────────────────────────────────────────────┘

  3 agentes especializados, cada um fez SEU trabalho:
  • Research Agent: pesquisou na web (web_search, web_fetch)
  • Writer Agent: escreveu o artigo (read, write)
  • Adapter Agent: adaptou para 4 canais (read, write)

  O codigo Python orquestrou o pipeline passando o output
  de cada agente como input para o proximo.
""")

        # Exibir preview de cada canal
        print("=" * 70)
        print("  PREVIEW DOS CONTEUDOS GERADOS")
        print("=" * 70)

        for channel, content in channels.items():
            label = {
                "linkedin": "LINKEDIN",
                "instagram": "INSTAGRAM",
                "twitter": "TWITTER/X",
                "email": "EMAIL",
            }.get(channel, channel.upper())
            print(f"\n  --- {label} ({len(content)} chars) ---")
            # Mostrar primeiras 500 chars como preview
            preview = content[:500]
            if len(content) > 500:
                preview += "\n  [... truncado, veja arquivo completo em output/]"
            for line in preview.split("\n"):
                print(f"  {line}")

        print(f"\n  📁 Arquivos completos em: {os.path.abspath(output_dir)}/")
        print("=" * 70)

    finally:
        # =================================================================
        # CLEANUP
        # =================================================================
        print("=" * 70)
        print("  CLEANUP")
        print("=" * 70)

        for agent_obj in agents:
            try:
                client.beta.agents.archive(agent_obj.id)
                print(f"  ✓ Agent {agent_obj.name} arquivado")
            except Exception as e:
                print(f"  ⚠ Agent {agent_obj.name}: {e}")

        if environment:
            try:
                client.beta.environments.delete(environment.id)
                print("  ✓ Environment deletado")
            except Exception as e:
                print(f"  ⚠ Environment: {e}")

        print("  --- CLEANUP COMPLETO ---")


if __name__ == "__main__":
    main()
