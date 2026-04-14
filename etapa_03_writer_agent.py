"""
Etapa 3: Content Writer Agent
==============================

CONCEITOS APRENDIDOS:
- Environment com pacotes pre-instalados (pip, npm, apt, etc.)
- Agente que le arquivos existentes no container (file operations)
- Sessao com conteudo pre-populado (simular output de etapa anterior)
- Separacao de responsabilidades entre agentes

NOVIDADES EM RELACAO A ETAPA 2:
- Environment agora instala pacotes Python automaticamente
- O agente NAO tem acesso a web (trabalha apenas com dados locais)
- Demonstra como um agente consome o output de outro agente
- Simula o fluxo: Research -> Writer (que sera automatizado na Etapa 5)

REQUISITOS:
- export ANTHROPIC_API_KEY="sua-chave-aqui"
- pip install anthropic>=0.52.0
"""

from anthropic import Anthropic

# System prompt do Content Writer.
# Note que ele NAO pesquisa - ele escreve com base em pesquisa JA feita.
# Isso demonstra separacao de responsabilidades entre agentes.
WRITER_SYSTEM_PROMPT = """\
Voce e um Copywriter Senior especializado em marketing de conteudo.

## Seu papel
Voce transforma pesquisas e dados em conteudo envolvente e profissional.
Voce NAO pesquisa - voce ESCREVE com base em material ja pesquisado.

## Como trabalhar
1. Leia o material de pesquisa disponivel em /workspace/research/
2. Analise os pontos-chave e dados mais relevantes
3. Escreva um artigo/blog post completo e envolvente
4. Salve o conteudo final em /workspace/content/

## Estilo de escrita
- Tom: profissional mas acessivel
- Formato: artigo de blog com titulo, subtitulos, bullets quando necessario
- Tamanho: 800-1200 palavras
- Inclua: introducao que prende, desenvolvimento com dados, conclusao com CTA
- Use dados e estatisticas da pesquisa para dar credibilidade

## Formato do arquivo de saida
Salve como markdown em /workspace/content/artigo.md com:
- Titulo principal (H1)
- Subtitulos (H2/H3) para cada secao
- Bullets para listas
- **Negrito** para destaques
- Uma secao final "Sobre" com 1-2 linhas sobre a empresa/autor ficticio

## Regras
- SEMPRE leia /workspace/research/ antes de escrever
- Nunca invente dados - use apenas o que esta na pesquisa
- Escreva em portugues brasileiro
- Foco em valor para o leitor, nao em venda direta
"""

# Dados simulados de pesquisa (que na Etapa 5 serao gerados pelo Research Agent)
SIMULATED_RESEARCH = """\
# Pesquisa: IA na Criacao de Conteudo para Marketing Digital (2025-2026)

## Resumo Executivo
A inteligencia artificial transformou a criacao de conteudo em marketing digital.
Em 2025, 78% das empresas ja utilizam alguma forma de IA em seus processos de
marketing, segundo a HubSpot State of Marketing Report.

## Pontos-Chave

### Ferramentas Principais
- **Claude (Anthropic)**: lider em geracao de texto longo e analise
- **ChatGPT (OpenAI)**: popular para brainstorming e drafts rapidos
- **Midjourney/DALL-E**: geracao de imagens para redes sociais
- **Jasper AI**: focado em copywriting de marketing
- **Canva AI**: design grafico com assistencia de IA

### Personalizacao com IA
- 65% dos consumidores esperam conteudo personalizado (McKinsey, 2025)
- Empresas que usam IA para personalizar conteudo veem aumento de 40% no engagement
- Email marketing com IA tem taxa de abertura 26% maior que emails genericos
- Segmentacao por IA reduz custo de aquisicao em ate 30%

### Riscos e Limitacoes
- Conteudo generico quando mal utilizado ("IA slop")
- Questoes de direitos autorais em conteudo gerado
- Dependencia excessiva pode reduzir autenticidade da marca
- Necessidade de revisao humana para manter qualidade
- Alucinacoes e dados inventados sao risco em conteudo factual

### Tendencias 2025-2026
- Agentes autonomos de IA para campanhas completas
- Video gerado por IA em alta (Sora, Runway)
- IA para otimizacao em tempo real de campanhas
- Conteudo interativo gerado por IA
- Regulamentacao de conteudo gerado por IA na UE e Brasil

## Fontes
- HubSpot State of Marketing 2025
- McKinsey Digital Marketing Report 2025
- Gartner Magic Quadrant for AI in Marketing 2025
- Content Marketing Institute Annual Survey 2025
"""


def main():
    client = Anthropic()

    print("=" * 60)
    print("ETAPA 3: Content Writer Agent")
    print("=" * 60)

    # =========================================================================
    # PASSO 1: Criar Agent Writer (sem acesso a web)
    # =========================================================================
    # CONCEITO: Agente SEM web tools
    # O Writer so trabalha com dados locais. Isso demonstra o principio
    # de MENOR PRIVILEGIO - cada agente so tem acesso ao que precisa.
    print("\n[1/4] Criando Writer Agent (sem web tools)...")
    agent = client.beta.agents.create(
        name="Content Writer - Marketing",
        model="claude-sonnet-4-6",
        system=WRITER_SYSTEM_PROMPT,
        tools=[
            {
                "type": "agent_toolset_20260401",
                "default_config": {"enabled": False},
                "configs": [
                    # Apenas file operations e bash - SEM web
                    {"name": "read", "enabled": True},
                    {"name": "write", "enabled": True},
                    {"name": "edit", "enabled": True},
                    {"name": "bash", "enabled": True},
                    {"name": "glob", "enabled": True},
                ],
            },
        ],
    )
    print(f"    Agent criado! ID: {agent.id}")

    # =========================================================================
    # PASSO 2: Criar Environment COM pacotes pre-instalados
    # =========================================================================
    # CONCEITO NOVO: Packages
    #
    # O campo "packages" pre-instala pacotes no container ANTES do agente
    # iniciar. Isso e mais eficiente do que o agente instalar via bash.
    #
    # Package managers suportados:
    # - pip: Python (ex: "pandas", "pandas==2.2.0")
    # - npm: Node.js (ex: "express", "express@4.18.0")
    # - apt: Sistema (ex: "ffmpeg", "imagemagick")
    # - cargo: Rust
    # - gem: Ruby
    # - go: Go modules
    #
    # Pacotes sao cacheados entre sessions que compartilham o mesmo environment.
    print("\n[2/4] Criando Environment com pacotes Python...")
    environment = client.beta.environments.create(
        name="writer-env",
        config={
            "type": "cloud",
            "packages": {
                "pip": ["markdown", "rich"],
            },
            # Sem web, o writer nao precisa de networking
            # Mas usamos unrestricted para manter simples neste exemplo
            "networking": {"type": "unrestricted"},
        },
    )
    print(f"    Environment criado! ID: {environment.id}")
    print(f"    Pacotes pip: markdown, rich")

    # =========================================================================
    # PASSO 3: Criar Session
    # =========================================================================
    print("\n[3/4] Criando Session...")
    session = client.beta.sessions.create(
        agent=agent.id,
        environment_id=environment.id,
        title="Writer: Artigo sobre IA no Marketing",
    )
    print(f"    Session criada! ID: {session.id}")

    # =========================================================================
    # PASSO 4: Popular container e pedir para escrever
    # =========================================================================
    # CONCEITO: Simular output de outro agente
    #
    # Na Etapa 5 (Orchestrator), o Research Agent populara /workspace/research/
    # automaticamente. Por agora, SIMULAMOS isso enviando duas mensagens:
    #
    # Mensagem 1: "Crie o diretorio e salve a pesquisa"
    # Mensagem 2: "Agora escreva o artigo baseado nessa pesquisa"
    #
    # Isso demonstra que sessions sao STATEFUL - o filesystem persiste
    # entre mensagens na mesma session.
    print("\n[4/4] Populando container com pesquisa e pedindo artigo...")
    print("-" * 60)

    with client.beta.sessions.events.stream(session.id) as stream:
        # Mensagem 1: popular o filesystem com a pesquisa simulada
        client.beta.sessions.events.send(
            session.id,
            events=[
                {
                    "type": "user.message",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Primeiro, crie o diretorio /workspace/research/ "
                                "e salve o seguinte conteudo de pesquisa no arquivo "
                                "/workspace/research/ia_marketing_2025.md:\n\n"
                                f"{SIMULATED_RESEARCH}\n\n"
                                "Depois de salvar a pesquisa, leia o arquivo para "
                                "confirmar que esta correto. Entao crie o diretorio "
                                "/workspace/content/ e escreva um artigo de blog "
                                "completo baseado nessa pesquisa. Salve em "
                                "/workspace/content/artigo.md"
                            ),
                        },
                    ],
                },
            ],
        )

        # Processar stream com indicadores visuais por tipo de operacao
        tool_count = 0
        for event in stream:
            match event.type:
                case "agent.message":
                    for block in event.content:
                        if hasattr(block, "text"):
                            print(f"\n[WRITER] {block.text}")

                case "agent.tool_use":
                    tool_count += 1
                    name = event.name

                    # Categorizar a operacao visualmente
                    if name in ("write", "edit"):
                        icon = "📝"
                        label = "ESCREVENDO"
                    elif name == "read":
                        icon = "📖"
                        label = "LENDO"
                    elif name == "bash":
                        icon = "⚙️"
                        label = "EXECUTANDO"
                    elif name == "glob":
                        icon = "🔍"
                        label = "BUSCANDO"
                    else:
                        icon = "🔧"
                        label = "TOOL"

                    print(f"\n{icon} [{label}] {name}")
                    if hasattr(event, "input") and event.input:
                        input_dict = event.input
                        if isinstance(input_dict, dict):
                            # Mostrar path do arquivo quando aplicavel
                            path = input_dict.get(
                                "file_path", input_dict.get("command", "")
                            )
                            if path:
                                display = str(path)
                                if len(display) > 100:
                                    display = display[:100] + "..."
                                print(f"         {display}")

                case "agent.tool_result":
                    status = "OK" if not event.is_error else "ERRO"
                    print(f"         -> {status}")

                case "session.status_idle":
                    print("\n" + "-" * 60)
                    print(f"[SESSION] Writer terminou! ({tool_count} tool calls)")
                    break

                case "span.model_request_end":
                    if hasattr(event, "model_usage") and event.model_usage:
                        usage = event.model_usage
                        print(
                            f"[USAGE]  In: {usage.input_tokens}, "
                            f"Out: {usage.output_tokens} tokens"
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

    print("\nEtapa 3 concluida com sucesso!")


if __name__ == "__main__":
    main()
