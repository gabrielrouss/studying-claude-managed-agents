"""
Etapa 4: Channel Adapter Agent
================================

CONCEITOS APRENDIDOS:
- Agente de transformacao: um input -> multiplos outputs
- System prompt como "manual de regras" por canal
- Edit tool para modificacoes cirurgicas em arquivos
- Multiplos arquivos de output organizados em diretorio

NOVIDADES EM RELACAO A ETAPA 3:
- O agente transforma UM conteudo em QUATRO formatos diferentes
- System prompt mais complexo com regras especificas por canal
- Demonstra como IA adapta tom, tamanho e formato por plataforma

REQUISITOS:
- export ANTHROPIC_API_KEY="sua-chave-aqui"
- pip install anthropic>=0.52.0
"""

from anthropic import Anthropic

# System prompt do Channel Adapter.
# Este e o mais detalhado porque precisa de REGRAS ESPECIFICAS por canal.
# Cada rede social tem restricoes e melhores praticas diferentes.
ADAPTER_SYSTEM_PROMPT = """\
Voce e um Social Media Specialist que adapta conteudo para multiplos canais.

## Seu papel
Voce recebe um artigo/conteudo principal e transforma em versoes otimizadas
para cada canal de distribuicao. Voce NAO cria conteudo novo - voce ADAPTA
o conteudo existente respeitando as regras de cada plataforma.

## Como trabalhar
1. Leia o conteudo principal em /workspace/content/artigo.md
2. Adapte para CADA canal listado abaixo
3. Salve cada adaptacao em /workspace/channels/

## Canais e Regras

### LinkedIn (/workspace/channels/linkedin.md)
- **Tom**: Profissional, insightful, thought leadership
- **Tamanho**: 1300 caracteres maximo (ideal: 800-1200)
- **Formato**:
  - Primeira linha impactante (hook)
  - Paragrafos curtos (2-3 linhas)
  - Emojis profissionais com moderacao (1-3 no maximo)
  - Hashtags no final (3-5 relevantes)
  - CTA sutil no final
- **Incluir**: dados/estatisticas do artigo original

### Instagram (/workspace/channels/instagram.md)
- **Tom**: Casual, inspirador, visualmente descritivo
- **Tamanho**: 2200 caracteres maximo (ideal: 1500-2000)
- **Formato**:
  - Caption comecando com hook forte
  - Quebras de linha para facilitar leitura
  - Emojis frequentes para dividir texto
  - 20-30 hashtags relevantes (em bloco no final)
  - CTA para engajamento ("salve este post", "marque alguem")
- **Incluir**: sugestao de carrossel (5-7 slides resumindo)

### Twitter/X (/workspace/channels/twitter.md)
- **Tom**: Direto, provocativo, conversacional
- **Tamanho**: Thread de 5-8 tweets, cada um com maximo 280 caracteres
- **Formato**:
  - Tweet 1: hook forte com emoji
  - Tweets 2-6: pontos-chave, um por tweet
  - Tweet 7: conclusao com CTA
  - Ultimo tweet: link/referencia
  - Numerar tweets (1/7, 2/7, etc.)
- **Incluir**: dados impactantes, perguntas retoricas

### Email Newsletter (/workspace/channels/email.md)
- **Tom**: Pessoal, direto, como um amigo compartilhando
- **Formato**:
  - Subject line (maximo 50 caracteres, curiosidade)
  - Preview text (maximo 90 caracteres)
  - Saudacao pessoal
  - Corpo: 300-500 palavras, conversacional
  - Bullets para pontos-chave
  - CTA claro com botao
  - PS: com conteudo bonus ou pergunta
- **Incluir**: "Voce sabia que...?" com dado do artigo

## Regras Gerais
- SEMPRE leia o artigo original antes de adaptar
- Mantenha a essencia e os dados, mude o formato
- Cada canal deve parecer NATIVO daquela plataforma
- Escreva em portugues brasileiro
- Nao repita o mesmo texto em canais diferentes
"""

# Artigo simulado (que na Etapa 5 sera gerado pelo Writer Agent)
SIMULATED_ARTICLE = """\
# Como a IA Esta Revolucionando o Marketing de Conteudo em 2025

## A Nova Era do Marketing Digital

O marketing de conteudo nunca mais sera o mesmo. Em 2025, **78% das empresas**
ja utilizam inteligencia artificial em seus processos de marketing, segundo a
HubSpot. Mas a grande questao nao e se voce deve usar IA - e como usa-la
sem perder a autenticidade da sua marca.

## O Poder da Personalizacao

A personalizacao e onde a IA realmente brilha. Dados da McKinsey mostram que
**65% dos consumidores esperam conteudo personalizado**, e empresas que atendem
essa expectativa veem um **aumento de 40% no engagement**.

O email marketing e um caso exemplar: campanhas com IA tem **taxa de abertura
26% maior** que emails genericos. Alem disso, a segmentacao inteligente reduz
o **custo de aquisicao em ate 30%**.

## As Ferramentas que Estao Liderando

O ecossistema de ferramentas amadureceu significativamente:

- **Claude (Anthropic)**: lider em geracao de texto longo e analise estrategica
- **Midjourney e DALL-E**: revolucionando a criacao visual
- **Jasper AI**: especializado em copywriting de marketing
- **Canva AI**: democratizando o design com IA

## Os Riscos Que Ninguem Fala

Nem tudo sao flores. O fenomeno do "IA slop" - conteudo generico e sem alma
gerado em massa - esta saturando a internet. Questoes de direitos autorais
permanecem em area cinzenta, e a dependencia excessiva pode matar a
autenticidade que diferencia sua marca.

A regra de ouro: **IA e ferramenta, nao substituto**. O melhor conteudo
em 2025 combina eficiencia da IA com a criatividade e empatia humana.

## O Que Vem Por Ai

Para 2026, fique de olho em:
- **Agentes autonomos** que gerenciam campanhas completas
- **Video gerado por IA** como formato dominante
- **Otimizacao em tempo real** de campanhas
- **Regulamentacao** de conteudo IA na UE e Brasil

## Conclusao

A IA no marketing nao e mais vantagem competitiva - e requisito basico.
A diferenca estara em COMO voce a utiliza. Empresas que encontrarem o
equilibrio entre automacao e autenticidade serao as vencedoras.

---
*Escrito pela equipe de conteudo da MarketingAI Labs*
"""


def main():
    client = Anthropic()

    print("=" * 60)
    print("ETAPA 4: Channel Adapter Agent")
    print("=" * 60)

    # =========================================================================
    # PASSO 1: Criar Agent Adapter
    # =========================================================================
    # Tools necessarias: read (ler artigo), write (salvar adaptacoes),
    # bash (criar diretorios), glob (verificar arquivos)
    print("\n[1/4] Criando Adapter Agent...")
    agent = client.beta.agents.create(
        name="Channel Adapter - Social Media",
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
    print(f"    Agent criado! ID: {agent.id}")

    # =========================================================================
    # PASSO 2: Criar Environment
    # =========================================================================
    print("\n[2/4] Criando Environment...")
    environment = client.beta.environments.create(
        name="adapter-env",
        config={
            "type": "cloud",
            "networking": {"type": "unrestricted"},
        },
    )
    print(f"    Environment criado! ID: {environment.id}")

    # =========================================================================
    # PASSO 3: Criar Session
    # =========================================================================
    print("\n[3/4] Criando Session...")
    session = client.beta.sessions.create(
        agent=agent.id,
        environment_id=environment.id,
        title="Adapter: Conteudo Multi-Canal",
    )
    print(f"    Session criada! ID: {session.id}")

    # =========================================================================
    # PASSO 4: Popular container com artigo e pedir adaptacoes
    # =========================================================================
    # Enviamos uma unica mensagem que:
    # 1. Pede para salvar o artigo simulado
    # 2. Pede para adaptar para todos os canais
    #
    # O agente deve gerar 4 arquivos em /workspace/channels/
    print("\n[4/4] Enviando artigo e pedindo adaptacoes multi-canal...")
    print("-" * 60)

    with client.beta.sessions.events.stream(session.id) as stream:
        client.beta.sessions.events.send(
            session.id,
            events=[
                {
                    "type": "user.message",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Primeiro, crie os diretorios necessarios e salve "
                                "o seguinte artigo em /workspace/content/artigo.md:\n\n"
                                f"{SIMULATED_ARTICLE}\n\n"
                                "Depois, leia o artigo salvo e adapte para TODOS os "
                                "4 canais conforme suas regras:\n"
                                "1. LinkedIn -> /workspace/channels/linkedin.md\n"
                                "2. Instagram -> /workspace/channels/instagram.md\n"
                                "3. Twitter/X -> /workspace/channels/twitter.md\n"
                                "4. Email -> /workspace/channels/email.md\n\n"
                                "Cada canal deve ter conteudo DIFERENTE e NATIVO "
                                "daquela plataforma."
                            ),
                        },
                    ],
                },
            ],
        )

        # Processar stream rastreando qual canal esta sendo adaptado
        tool_count = 0
        channels_created = []

        for event in stream:
            match event.type:
                case "agent.message":
                    for block in event.content:
                        if hasattr(block, "text"):
                            print(f"\n[ADAPTER] {block.text}")

                case "agent.tool_use":
                    tool_count += 1
                    name = event.name

                    if hasattr(event, "input") and event.input:
                        input_dict = event.input
                        if isinstance(input_dict, dict):
                            path = input_dict.get("file_path", "")

                            # Detectar qual canal esta sendo criado
                            for channel in [
                                "linkedin",
                                "instagram",
                                "twitter",
                                "email",
                            ]:
                                if (
                                    channel in str(path)
                                    and name == "write"
                                    and channel not in channels_created
                                ):
                                    channels_created.append(channel)
                                    print(
                                        f"\n📱 [CANAL] Criando adaptacao: "
                                        f"{channel.upper()}"
                                    )

                            if name == "write" and "channels" not in str(path):
                                print(f"\n📝 [WRITE] {path}")
                            elif name == "read":
                                print(f"\n📖 [READ]  {path}")
                            elif name == "bash":
                                cmd = input_dict.get("command", "")
                                print(f"\n⚙️  [BASH]  {cmd[:80]}")
                            elif name not in ("write",):
                                print(f"\n🔧 [TOOL]  {name}")

                case "agent.tool_result":
                    status = "OK" if not event.is_error else "ERRO"
                    print(f"         -> {status}")

                case "session.status_idle":
                    print("\n" + "-" * 60)
                    print(f"[SESSION] Adapter terminou!")
                    print(f"          Tool calls: {tool_count}")
                    print(
                        f"          Canais criados: "
                        f"{', '.join(channels_created) or 'nenhum detectado'}"
                    )
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

    print("\nEtapa 4 concluida com sucesso!")


if __name__ == "__main__":
    main()
