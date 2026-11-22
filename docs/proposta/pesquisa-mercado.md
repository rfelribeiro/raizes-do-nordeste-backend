# Pesquisa de mercado: construir × comprar × integrar

> Insumo da apresentação final (seção 4, 6 e 7 do [roteiro](README.md)). Data de consulta de todos os valores: **22 nov. 2026**. Rede Raízes do Nordeste é fictícia; os números abaixo são de produtos reais, para dimensionar a decisão.

## 1. Método e limites

- Buscas na web (modo padrão) sobre produtos e preços **públicos**, em português e inglês, e leitura dos resultados de páginas oficiais sempre que a busca as devolveu. Nenhum dado pessoal ou do repositório foi enviado.
- Cada valor tem um tipo: **público** (publicado pelo fornecedor), **público, de terceiro** (publicado por revenda, concorrente ou blog; menos confiável), **sob consulta** (o fornecedor não publica) ou **estimativa** (cálculo da IA com premissa explícita).
- **Limitação honesta:** os valores foram lidos em resumos de busca de páginas que mudam com frequência; várias fontes divergem entre si (apontado nas tabelas). Antes de qualquer contratação, os preços devem ser confirmados com o fornecedor. Onde não houve preço público, está escrito "sob consulta", sem número inventado.
- Dólar usado nas conversões: **R$ 5,50 por US$ 1,00**, premissa da IA, a validar pelo autor sem fonte (varia).
- Para cada capacidade, a recomendação segue a tese: **comprar o que é commodity, integrar o que é crítico e construir só o que diferencia (os dados como ativo)**.

Critérios transversais avaliados: LGPD e hospedagem no Brasil (em geral os fornecedores nacionais não publicam a região de hospedagem; marcado "confirmar"), existência de API/exportação (para os dados chegarem ao DW e ao outbox do projeto), custo por unidade franqueada, suporte no Brasil e risco de aprisionamento (*lock-in*).

## 2. Capacidades

### 2.1 PDV, frente de caixa e gestão de pedidos (multiunidade)

| Opção | Tipo | Preço/custo | Fonte e data | API/exportação | Observações |
|---|---|---|---|---|---|
| Loyverse POS | Gratuita (complementos pagos) | US$ 0 no plano base; complementos pagos [sob consulta no Brasil] | [F5] 22/11/2026 (público) | API e exportação existem no produto (não verificadas aqui) | Voltado a lanchonete/QSR; análises indicam falta de mesas, comandas e estoque de ingredientes; emissão fiscal brasileira não confirmada |
| Saipos | Prateleira (BR) | a partir de R$ 240,79/mês por loja, sem taxa de instalação e sem cobrança por usuário; suporte 24h incluso | [F1] 22/11/2026 (público; URL contém "teste2025", pode estar defasada) | Integra com iFood e outros; API aberta para clientes não confirmada | Suporte no Brasil; tabela completa de planos não publicada |
| Colibri (RS Solutions) | Prateleira (BR), foco em redes | **sob consulta** | [F6] 22/11/2026 (notícia: ~15 mil restaurantes, mais de 100 revendedores) | Não confirmada | Atende de pequenos a redes e franquias, segundo o fabricante; preço só por revendedor |
| Sob medida | Sob medida | Estimativa: 3 desenvolvedores por 6 a 12 meses, de R$ 0,42 mi a R$ 0,84 mi (ver seção 4) | Estimativa da IA com salários de [F20] e encargos de [F21], 22/11/2026 | Total (é o código da rede) | Inclui fiscal (NFC-e), impressão, offline e hardware: escopo muito maior que o MVP deste trabalho |

**Recomendação: comprar.** PDV e frente de caixa são commodity e exigem NFC-e, impressoras e operação offline que a rede não precisa dominar (RNF-09, disponibilidade no pico). Exigir na contratação API/exportação de pedidos para alimentar o DW.

### 2.2 Cardápio digital, pedido online, retirada e totem

| Opção | Tipo | Preço/custo | Fonte e data | API/exportação | Observações |
|---|---|---|---|---|---|
| Módulo de pedido online do PDV (ex.: Saipos) | Prateleira | incluído no plano do PDV (a confirmar) | [F1] 22/11/2026 | via PDV | Evita um segundo fornecedor |
| Goomer | Prateleira (BR) | Básico R$ 59,94/mês (anual) ou R$ 99,90 (mensal); Automatizar R$ 110,94 (anual) ou R$ 184,90; Integrar R$ 224,93 (anual) ou R$ 299,90. Totem: **sob consulta** | [F3] 22/11/2026 (público de terceiro: página de concorrente; um guia cita R$ 49,95 a R$ 224,93) | Plano "Integrar" prevê integração com PDV | Também vende totem de autoatendimento; faturamento declarado de R$ 4 bi de GMV em 2025 |
| Anota AI (hoje do iFood) | Prateleira (BR) | valores divergentes: Start ~R$ 249,99/mês; plano anual ~R$ 178,99 (2023) | [F4], [F24] 22/11/2026 (público de terceiro, inconsistente) | Não confirmada | Cardápio e atendimento por WhatsApp; reclamações de cobrança no Reclame Aqui; propriedade do iFood é risco de conflito de interesse |
| Open source | Open source | Nenhuma opção madura identificada para cardápio/totem em português | pesquisa de 22/11/2026 | – | Gap de mercado; custo seria de construir |
| Sob medida | Sob medida | App, web e totem próprios: estimativa de R$ 0,4 mi a R$ 0,8 mi para a primeira versão (mesma base de [F20], [F21]) | Estimativa da IA | Total | Front-end está fora do escopo deste trabalho (Won't) |

**Recomendação: comprar.** Pedido online, retirada e totem (canais APP, WEB, PICKUP e TOTEM, RF-07) são commodity; a rede deve exigir que o `canalPedido` chegue à API ou ao DW.

### 2.3 Delivery e marketplaces

| Opção | Tipo | Preço/custo | Fonte e data | API/exportação | Observações |
|---|---|---|---|---|---|
| iFood, plano Básico (entrega própria) | Marketplace | ~12% de comissão + ~3,2% a 3,5% de pagamento online; mensalidade ~R$ 100 a R$ 130 acima de R$ 1.800 de venda (fontes divergem) | [F2], [F23] 22/11/2026 (público de terceiro) | API para parceiros (integrada por PDVs) | Taxas mudam por contrato e por cidade; houve acusações de lojistas sobre taxas altas |
| iFood, plano Entrega | Marketplace | ~23% (um artigo antigo cita 27%) | [F2], [F23] 22/11/2026 (público de terceiro) | idem | O iFood entrega com entregadores parceiros |
| Canal próprio (pedido online da seção 2.2) | Prateleira | sem comissão de marketplace; custo é a mensalidade do módulo e a taxa de pagamento | [F3] | via fornecedor | Reduz dependência, mas não traz a demanda do marketplace |
| Sob medida | Sob medida | Não se constrói marketplace; construir só o conector | – | – | Logística e entrega estão fora do escopo (Won't) |

**Recomendação: comprar** (e integrar os pedidos ao PDV), porque a comissão de 12% a 23% compra audiência que a rede não consegue construir sozinha; o dado do pedido deve voltar para a rede (RF-22, outbox).

### 2.4 Pagamentos (gateway, adquirência e Pix)

| Opção | Tipo | Preço/custo | Fonte e data | API/exportação | Observações |
|---|---|---|---|---|---|
| Mercado Pago (Point/Pix/QR) | Prateleira | Pix 0,49% (PJ, Point Pro 3); débito 1,41% a 1,99%; crédito à vista 3,31% a 4,98%, conforme faturamento; páginas divergem sobre Pix (0% a 0,99%) | [F9] 22/11/2026 (público; um artigo informa valores de jul. 2026) | API e webhooks | Taxa cai com o volume |
| Asaas | Prateleira (BR) | Pix R$ 0,99 nos 3 primeiros meses e R$ 1,99 depois, por transação; boleto R$ 0,99 (promocional) ou R$ 1,99; crédito à vista R$ 0,49 + 2,99% (layout confuso) | [F10] 22/11/2026 (público) | API robusta, sandbox | Tarifa fixa por Pix favorece ticket alto; cuidado com ticket médio baixo de lanchonete |
| Pagar.me (Stone) | Prateleira (BR) | Pix ~1,19% (0,78% negociado); crédito à vista 2,39% a 4,39%; boleto R$ 3,49; proposta personalizada | [F11] 22/11/2026 (público de terceiro) | API (gateway + PSP) | Taxas finais por proposta |
| Gateway open source | Open source | Não existe equivalente: a adquirência é regulada | – | – | Só se pode abstrair o gateway (padrão já usado no mock deste trabalho) |
| Sob medida | Sob medida | Inviável (regulação do Banco Central, PCI DSS) | – | – | Construir só a camada de integração |

**Recomendação: integrar.** Pagamento é crítico e regulado: contrata-se o gateway e constrói-se apenas a integração com timeout e idempotência (RF-11, RNF-10), mantendo a troca de fornecedor simples. Comissão de pagamento é custo variável, igual em qualquer cenário, e por isso não entra no TCO.

### 2.5 Estoque, ERP e ficha técnica

| Opção | Tipo | Preço/custo | Fonte e data | API/exportação | Observações |
|---|---|---|---|---|---|
| Odoo Community / ERPNext | Open source | Licença gratuita; ERPNext hospedado no Frappe Cloud a partir de ~US$ 5/mês por site (por consumo); suporte não incluso | [F7], [F8] 22/11/2026 (público) | API aberta | Localização fiscal brasileira (NF-e) e ficha técnica exigem parceiro e implantação (não confirmados aqui) |
| Odoo Online (Standard/Custom) | Prateleira | US$ 31,10 (Standard) e US$ 46,70 (Custom) por usuário/mês no anual; Custom traz API externa e multiempresa; um agregador cita US$ 76,20 (não confirmado) | [F7] 22/11/2026 (público) | API só no Custom | Dados hospedados fora do Brasil (confirmar) |
| Estoque do próprio PDV (ex.: Saipos) | Prateleira | incluído na mensalidade do PDV (a confirmar o módulo de ficha técnica) | [F1] | via PDV | Menor integração |
| Sob medida | Sob medida | O MVP deste trabalho cobre reserva e baixa; um ERP completo é multiplicado por fiscal, compras e CMV: estimativa de R$ 0,4 mi a R$ 0,8 mi | Estimativa da IA | Total | Não recomendado |

**Recomendação: comprar.** Ficha técnica, compras e CMV por unidade são commodity; a API da rede só precisa reservar e baixar estoque no pedido (RF-16) e publicar o movimento para o DW (matriz de barramento).

### 2.6 Fidelidade, CRM e campanhas

| Opção | Tipo | Preço/custo | Fonte e data | API/exportação | Observações |
|---|---|---|---|---|---|
| Fidelidade do Goomer (plano Automatizar) | Prateleira | R$ 110,94/mês (anual) ou R$ 184,90, com chatbot e fidelidade | [F3] 22/11/2026 (público de terceiro) | Não confirmada | Atrelado ao fornecedor do cardápio |
| Fidelimax | Prateleira (BR) | **sob consulta** | [F19] 22/11/2026 | integrações com e-commerce | Aplicativo do consumidor gratuito |
| Planilha/CRM open source | Open source | gratuito | – | total | Exige operação e atenção à LGPD |
| Sob medida | Sob medida | Pontos, resgate e consentimento por finalidade já modelados neste trabalho (RF-14, RF-17, RF-18, não implementados); custo adicional de ~2 a 3 meses de 2 desenvolvedores (estimativa, R$ 95 mil a R$ 140 mil) | Estimativa da IA ([F20], [F21]) | Total | Faz sentido só quando as regras forem diferenciais |

**Recomendação: comprar** no início (5 unidades) e **construir depois** se as regras de pontos forem o diferencial, porque o programa exige consentimento por finalidade e revogação (RF-14, LGPD), e a rede deve poder levar o histórico embora (exigir exportação).

### 2.7 BI e painéis

| Opção | Tipo | Preço/custo | Fonte e data | API/exportação | Observações |
|---|---|---|---|---|---|
| Looker Studio | Gratuita | grátis; Pro cobrado por usuário (US$ 9 em fonte de jun. 2025) | [F14] 22/11/2026 (Pro: terceiro, possivelmente desatualizado) | conecta a BigQuery, Sheets, etc. | Nuvem Google |
| Metabase | Open source + nuvem | Open source gratuito (auto-hospedado); nuvem Starter US$ 100/mês + US$ 6 por usuário (5 inclusos); Pro US$ 575/mês + US$ 12 por usuário (10 inclusos) | [F13] 22/11/2026 (público; sites de terceiros ainda mostram preços anteriores) | SQL direto no DW | Auto-hospedar custa operação |
| Apache Superset | Open source | gratuito; custo é hospedagem e operação | [F25] (site do projeto; sem preço) | SQL direto | Mais técnico |
| Power BI Pro | Prateleira | R$ 80,20 por usuário/mês, cobrança anual, sem impostos | [F12] 22/11/2026 (público) | conecta a DuckDB/Postgres/Parquet por conectores | Valor em outras fontes: R$ 93,50 (GoDaddy) |
| Sob medida | Sob medida | Não se justifica construir ferramenta de BI | – | – | Construir apenas o modelo de dados (DW Kimball) |

**Recomendação: comprar** a ferramenta de painel e **construir o modelo de dados** (seção 2.9), porque o diferencial é o dado conformado (`dim_canal`, fatos de pedido), não o gráfico.

### 2.8 Automação e IA aplicada

| Opção | Tipo | Preço/custo | Fonte e data | API/exportação | Observações |
|---|---|---|---|---|---|
| WhatsApp Business Platform (Meta) | Prateleira (cobrança por mensagem) | modelo por mensagem entregue (marketing, utilidade, autenticação; serviço gratuito). Estimativas de terceiros para o Brasil: marketing ~R$ 0,38 a R$ 0,39; utilidade ~R$ 0,04 a R$ 0,08. Tabela oficial em BRL não obtida | [F15] 22/11/2026 (oficial para o modelo; valores em BRL de terceiros) | API oficial | Exige consentimento (LGPD) e provedor oficial |
| Blip (Take) | Prateleira (BR) | **sob consulta** (um concorrente estima a partir de R$ 2.600/mês; não verificado) | [F16] 22/11/2026 | API | Relatos de reajuste na migração de contrato |
| Chatbot nativo do cardápio (Goomer/Anota AI) | Prateleira | embutido nos planos da seção 2.2 | [F3], [F4] | limitada | Menor esforço |
| Previsão de demanda | Open source / sob medida | bibliotecas open source (ex.: Prophet) sem custo de licença; custo é de pessoa | – | usa o DW | Só faz sentido com histórico de vendas próprio (algumas centenas de dias por unidade) |

**Recomendação: integrar** (atendimento por WhatsApp oficial com cardápio da unidade) e **construir** somente a previsão de demanda sobre o DW, porque a previsão depende do histórico próprio da rede e o atendimento é commodity (RG p. 6: pico sem falhas). Cuidados: LGPD, consentimento de MARKETING (RF-14) e revisão humana das respostas.

### 2.9 Dados: armazenamento analítico

| Opção | Tipo | Preço/custo | Fonte e data | API/exportação | Observações |
|---|---|---|---|---|---|
| DuckDB + Parquet (o DW deste trabalho) | Open source | licença gratuita; custo é armazenamento e operação | [F26] (site do projeto, sem preço) | formatos abertos (Parquet): portabilidade total | Sem servidor multiusuário; evolui para Lakehouse |
| PostgreSQL gerenciado (ex.: RDS) | Open source gerenciado | db.t4g.medium em São Paulo: ~US$ 0,137/h em instância única (~US$ 100/mês) e ~US$ 0,275/h em Multi-AZ (~US$ 200/mês), mais armazenamento e backup | [F22] 22/11/2026 (terceiro; não confirmado na página da AWS) | SQL padrão | Região São Paulo ajuda na LGPD |
| BigQuery | DW gerenciado | consulta sob demanda US$ 6,25 por TiB (1 TiB gratuito por mês); armazenamento por GB: não confirmado na região São Paulo | [F17] 22/11/2026 (público) | exportação para Parquet | Região southamerica-east1 existe; baixo volume cabe quase todo na cota gratuita |
| MotherDuck | DuckDB gerenciado | Lite US$ 0/mês (10 horas de CU e 10 GB); Business US$ 250/mês mais uso; fontes de 2025 citam US$ 25 e US$ 100 (superadas) | [F18] 22/11/2026 (público) | DuckDB/Parquet | Mantém o formato; hospedagem fora do Brasil (confirmar) |
| Sob medida | Sob medida | O que já existe neste trabalho: outbox + DW dimensional | – | total | Este é o diferencial |

**Recomendação: construir** o modelo e o pipeline (outbox transacional + DW Kimball em formato aberto), com armazenamento em serviço gerenciado conforme crescer, porque é o ativo que diferencia a rede e que não se perde na troca de fornecedores (RF-22, visão analítica).

## 3. Quadro-resumo da decisão

| Capacidade | Decisão | Justificativa (uma frase) |
|---|---|---|
| PDV e gestão de pedidos | Comprar | Commodity com exigências fiscais e de operação offline; RNF-09 (pico). |
| Cardápio digital, pedido online e totem | Comprar | Canais APP, WEB, PICKUP e TOTEM (RF-07) já existem prontos; exigir `canalPedido` nos dados. |
| Delivery e marketplaces | Comprar | A comissão paga audiência que a rede não constrói; pedido volta pelo outbox (RF-22). |
| Pagamentos | Integrar | Crítico e regulado: contrata-se o gateway e constrói-se só a integração (RF-11, RNF-10). |
| Estoque, ERP e ficha técnica | Comprar | Ficha técnica e CMV são commodity; a API só reserva e baixa (RF-16). |
| Fidelidade e CRM | Comprar (revisar) | Consentimento por finalidade (RF-14, LGPD) e exportação do histórico, até a regra de pontos virar diferencial. |
| BI e painéis | Comprar | O diferencial é o modelo de dados, não a ferramenta de gráfico. |
| Automação e IA | Integrar | WhatsApp oficial sobre o cardápio; previsão de demanda só sobre dados próprios. |
| Dados e DW | Construir | Ativo da rede, em formatos abertos, alimentado pelo outbox (RF-22). |

## 4. TCO em 3 anos

### 4.1 Premissas (todas explícitas)

1. **Horizonte:** 3 anos, em reais constantes, sem inflação, sem desconto financeiro; cada cenário (5, 20 e 50 unidades) é estático nos 3 anos.
2. **Fora do TCO (iguais nos dois cenários):** hardware (totem, tablet, impressora, maquininha), taxas de pagamento e comissões de marketplace (variáveis com a receita), mensagens de WhatsApp, NFC-e e tributos.
3. **Salários (mensal, Robert Half, São Paulo, 22/11/2026):** back-end pleno mediana R$ 12.000 (25º a 75º: R$ 9.200 a R$ 15.450) [F20]; back-end sênior mediana R$ 16.000 (R$ 12.250 a R$ 20.600) [F20]. Para a equipe de construção usa-se **R$ 13.000** de salário médio (mistura pleno e sênior; premissa da IA, a validar pelo autor).
4. **Encargos:** multiplicador **1,8** sobre o salário (CLT, provisões de 13º/férias/FGTS e encargos; fontes citam 1,7 a 2,5, conforme regime) [F21]. Custo por desenvolvedor: R$ 13.000 × 1,8 = R$ 23.400/mês (R$ 280.800/ano).
5. **Prateleira, por unidade:** PDV e gestão Saipos R$ 240,79/mês [F1] + cardápio/pedido online/fidelidade/chatbot Goomer "Integrar" R$ 224,93/mês no plano anual [F3] = **R$ 465,72/mês por unidade** (R$ 5.588,64/ano). Supõe-se que os planos se somem, que um cobre ficha técnica e estoque, e que não há desconto por volume (premissas que o fornecedor deve confirmar).
6. **Prateleira, matriz:** ERP (Odoo Standard, US$ 31,10 × R$ 5,50 = R$ 171,05) + BI (Power BI Pro R$ 80,20) = R$ 251,25 por usuário/mês; 3, 5 e 8 usuários para 5, 20 e 50 unidades (premissa da IA, a validar pelo autor).
7. **Camada de dados (prateleira):** R$ 500/mês (estimativa da IA para DW gerenciado e ingestão; base: BigQuery US$ 6,25/TiB com 1 TiB gratuito [F17] e Postgres gerenciado ~US$ 100/mês [F22]).
8. **Integração e dados na prateleira:** 0,25, 0,5 e 1,0 pessoa em tempo integral (pleno, R$ 12.000 × 1,8 = R$ 21.600/mês) para 5, 20 e 50 unidades: sem isso o ecossistema não conversa nem alimenta o DW (premissa da IA, a validar pelo autor).
9. **Implantação (só ano 1):** R$ 1.500 por unidade (treinamento e configuração; estimativa, o fornecedor anuncia implantação gratuita como promoção [F1]).
10. **Construção própria:** 3, 4 e 6 desenvolvedores para 5, 20 e 50 unidades (premissa da IA, a validar pelo autor: equipe mínima para PDV, canais, estoque, fidelidade, dados, operação e plantão; cresce com as unidades). Infraestrutura em nuvem: R$ 2.200, R$ 4.500 e R$ 9.000 por mês (estimativa: banco gerenciado em Multi-AZ ~US$ 200 [F22], contêineres, balanceador, logs, backup e ambiente de teste, escalando com a carga). Segurança e conformidade: R$ 60 mil por ano (teste de invasão, DPO terceirizado e auditoria; R$ 90 mil com 50 unidades; estimativa da IA, sem fonte pública). A manutenção está dentro da equipe, que é paga integralmente a partir do ano 1 mesmo que o produto só fique pronto no meio dele.
11. A construção **não** inclui hardware, NFC-e, taxas de pagamento nem o custo de oportunidade de atrasar a expansão.

### 4.2 Cálculo

Prateleira, por ano (recorrente) = (R$ 465,72 × unidades + R$ 251,25 × usuários da matriz + R$ 500) × 12 + integração (FTE × R$ 21.600 × 12). Ano 1 soma a implantação.

| Cenário | Licenças por unidade | ERP + BI da matriz | Camada de dados | Integração | Recorrente/ano | Implantação (ano 1) |
|---|---|---|---|---|---|---|
| 5 unidades | R$ 27.943 | R$ 9.045 | R$ 6.000 | R$ 64.800 | R$ 107.788 | R$ 7.500 |
| 20 unidades | R$ 111.773 | R$ 15.075 | R$ 6.000 | R$ 129.600 | R$ 262.448 | R$ 30.000 |
| 50 unidades | R$ 279.432 | R$ 24.120 | R$ 6.000 | R$ 259.200 | R$ 568.752 | R$ 75.000 |

Construção própria, por ano = desenvolvedores × R$ 13.000 × 1,8 × 12 + infraestrutura × 12 + segurança.

| Cenário | Equipe | Infraestrutura/ano | Segurança e conformidade/ano | Total/ano |
|---|---|---|---|---|
| 5 unidades | R$ 842.400 (3 devs) | R$ 26.400 | R$ 60.000 | R$ 928.800 |
| 20 unidades | R$ 1.123.200 (4 devs) | R$ 54.000 | R$ 60.000 | R$ 1.237.200 |
| 50 unidades | R$ 1.684.800 (6 devs) | R$ 108.000 | R$ 90.000 | R$ 1.882.800 |

### 4.3 Resultado (R$, 3 anos)

| Unidades | Prateleira ano 1 | Ano 2 | Ano 3 | **Total prateleira** | **Total construção** | Construção ÷ prateleira |
|---|---|---|---|---|---|---|
| 5 | 115.288 | 107.788 | 107.788 | **330.865** | **2.786.400** | 8,4 × |
| 20 | 292.448 | 262.448 | 262.448 | **817.343** | **3.711.600** | 4,5 × |
| 50 | 643.752 | 568.752 | 568.752 | **1.781.256** | **5.648.400** | 3,2 × |

Leitura honesta: mesmo com 50 unidades, construir tudo custa cerca de 3 vezes o ecossistema de prateleira. O custo por unidade da prateleira fica em torno de R$ 11 mil/ano (R$ 568.752 ÷ 50); a equipe de construção a 50 unidades custa R$ 1,88 mi/ano; supondo custo linear de prateleira e sem desconto por volume, o ponto de equilíbrio fica em **150 a 170 unidades** (cálculo grosseiro, ver sinais abaixo). Isso não considera ganhos de diferenciação que só a construção entregaria. A conta é sensível às premissas 5, 8 e 10; recomenda-se que a rede refaça com cotações reais (Colibri, Goomer, Blip e outros estão "sob consulta").

## 5. Roadmap por fase de crescimento

| Fase | Adotar (comprar/integrar) | Construir / evoluir |
|---|---|---|
| **5 unidades** | PDV com pedido online/totem (um fornecedor), gateway de pagamento, ERP leve ou estoque do PDV, Looker Studio ou Power BI, planilha de CRM com consentimento | Nada além do esquema de dados: exigir exportação de pedidos e canal; guardar eventos (outbox) e montar o DW pequeno em DuckDB/Parquet |
| **20 unidades** | ERP multiunidade, programa de fidelidade com consentimento, WhatsApp oficial com chatbot, BI com modelo de dados central; equipe de dados de 0,5 pessoa | Pipeline de dados e modelo dimensional (matriz de barramento), previsão de demanda piloto |
| **50+ unidades** | Negociar contratos por volume, DW gerenciado (BigQuery ou Postgres na região de São Paulo), segundo gateway | Previsão de demanda e compras, motor de regras de campanhas e fidelidade, camada de integração própria entre fornecedores; avaliar plataforma própria de pedidos somente se os sinais abaixo ocorrerem |

### Sinais de que vale construir algo próprio

1. O fornecedor não oferece API ou exportação suficiente para alimentar o DW, ou cobra à parte por isso (risco de lock-in).
2. A regra de negócio é o diferencial (por exemplo, fidelidade ligada ao período junino e a produtos sazonais) e não cabe no produto de prateleira.
3. Custo por unidade da prateleira cresce com a rede acima do custo marginal de manter uma equipe própria (ponto em torno de 150 a 170 unidades, pela conta acima).
4. Exigência de LGPD ou de hospedagem no Brasil que o fornecedor não atende.
5. Limites de desempenho no pico que o fornecedor não consegue cumprir (RNF-08, RNF-09).
6. Disposição e capacidade de contratar e reter uma equipe de engenharia (o risco principal de construir: salário médio, rotatividade e conhecimento concentrado).

## 6. Fontes

Todas com "Acesso em: 22 nov. 2026".

- [F1] SAIPOS. **Planos e preços**. Disponível em: https://saipos.com/teste2025/planos-e-precos ; e **Delivery**: https://saipos.com/delivery. Acesso em: 22 nov. 2026.
- [F2] SAIPOS. **Planos iFood**. Disponível em: https://saipos.com/integracoes/ifood/planos-ifood. Acesso em: 22 nov. 2026.
- [F3] SAIPOS. **Goomer: guia completo** (comparativo de planos). Disponível em: https://saipos.com/cardapio-digital/goomer. Acesso em: 22 nov. 2026.
- [F4] SAIPOS. **Cardápio digital Anota Ai**. Disponível em: https://saipos.com/cardapio-digital/anota-ai. Acesso em: 22 nov. 2026.
- [F5] LOYVERSE. **Pricing**. Disponível em: https://loyverse.com/en-us/pricing. Acesso em: 22 nov. 2026.
- [F6] BLOOMBERG LINEA. **RS Solutions compra Colibri**. Disponível em: https://www.bloomberglinea.com.br/tech/rs-solutions-compra-colibri-software-usado-por-15-mil-restaurantes-dizem-fontes/. Acesso em: 22 nov. 2026.
- [F7] ODOO. **Pricing plan**. Disponível em: https://odoo.com/pricing-plan. Acesso em: 22 nov. 2026.
- [F8] FRAPPE. **Frappe Cloud pricing**. Disponível em: https://frappe.io/cloud/pricing. Acesso em: 22 nov. 2026.
- [F9] MERCADO PAGO. **Quanto custa receber pagamentos via Pix e código QR**. Disponível em: https://www.mercadopago.com.br/blog/quanto-custa-receber-pagamentos-via-pix-e-codigo-qr ; **Taxas da Point Pro 3**: https://www.mercadopago.com.br/blog/taxas-point-pro-3-reducao-progressiva-volume. Acesso em: 22 nov. 2026.
- [F10] ASAAS. **Preços e taxas**. Disponível em: https://www.asaas.com/precos-e-taxas. Acesso em: 22 nov. 2026.
- [F11] IDINHEIRO. **Melhores gateways de pagamento** (inclui Pagar.me). Disponível em: https://www.idinheiro.com.br/negocios/melhores-gateways-de-pagamento/. Acesso em: 22 nov. 2026.
- [F12] MICROSOFT. **Power BI: preços**. Disponível em: https://www.microsoft.com/pt-br/power-platform/products/power-bi/pricing. Acesso em: 22 nov. 2026.
- [F13] METABASE. **Pricing / upgrade**. Disponível em: https://www.metabase.com/upgrade/ ; https://www.metabase.com/pricing. Acesso em: 22 nov. 2026.
- [F14] GOOGLE CLOUD. **Looker Studio Pro subscription overview**. Disponível em: https://cloud.google.com/looker/docs/studio/looker-studio-pro-subscription-overview?hl=pt-br ; WISE. **Looker Studio Pro: preços**: https://wise.com/br/blog/lookerstudio-planos. Acesso em: 22 nov. 2026.
- [F15] META. **Pricing on the WhatsApp Business Platform**. Disponível em: https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing ; HYPERLEAP. **WhatsApp pricing calculator (Brazil, 2026)**: https://hyperleap.ai/whatsapp-pricing-calculator-brazil. Acesso em: 22 nov. 2026.
- [F16] TALQUI. **Alternativas à Take Blip** (preço estimado por concorrente). Disponível em: https://talqui.chat/en/alternativas/take-blip. Acesso em: 22 nov. 2026.
- [F17] GOOGLE CLOUD. **BigQuery pricing**. Disponível em: https://cloud.google.com/bigquery/pricing. Acesso em: 22 nov. 2026.
- [F18] MOTHERDUCK. **Pricing model**. Disponível em: https://motherduck.com/docs/about-motherduck/billing/pricing/. Acesso em: 22 nov. 2026.
- [F19] NUVEMSHOP. **Fidelimax (loja de aplicativos)**. Disponível em: https://www.nuvemshop.com.br/loja-aplicativos-nuvem/fidelimax. Acesso em: 22 nov. 2026.
- [F20] ROBERT HALF. **Desenvolvedor(a) Back-End pleno e sênior, São Paulo** (faixas salariais). Disponível em: https://www.roberthalf.com/br/pt/vagas-detalhes/desenvolvedora-back-end-pleno/sao-paulo ; https://www.roberthalf.com/br/pt/vagas-detalhes/desenvolvedora-back-end-senior/sao-paulo. Acesso em: 22 nov. 2026.
- [F21] VALORFINAL. **Custo do funcionário CLT: encargos e provisões (2026)**. Disponível em: https://valorfinal.com.br/guia/custo-funcionario. Acesso em: 22 nov. 2026.
- [F22] AMAZON WEB SERVICES. **Amazon RDS for PostgreSQL pricing**. Disponível em: https://aws.amazon.com/rds/postgresql/pricing/ ; SPARE CORES. **db.t4g.medium**: https://sparecores.com/database/aws/db.t4g.medium. Acesso em: 22 nov. 2026.
- [F23] SERASA. **Como abrir loja no iFood** (comissões e taxas). Disponível em: https://www.serasa.com.br/blog/abrir-loja-no-ifood/. Acesso em: 22 nov. 2026.
- [F24] STARTUPS. **iFood compra a Anota AI**. Disponível em: https://startups.com.br/negocios/exclusivo-ifood-compra-a-anota-ai-para-oferecer-atendimento-pelo-whatsapp/. Acesso em: 22 nov. 2026.
- [F25] APACHE SOFTWARE FOUNDATION. **Apache Superset**. Disponível em: https://superset.apache.org. Acesso em: 22 nov. 2026 (referência ao projeto; não consultado preço).
- [F26] DUCKDB. **DuckDB**. Disponível em: https://duckdb.org. Acesso em: 22 nov. 2026 (referência ao projeto; não consultado preço).

## 7. Lacunas ("sob consulta" ou não confirmado)

Preço do Colibri; preço de totem de autoatendimento (Goomer e outros); preço do Fidelimax; preço do Blip (só estimativa de concorrente); tabela oficial em reais do WhatsApp para o Brasil; armazenamento por GB do BigQuery em São Paulo; região de hospedagem de dados e política de exportação dos fornecedores nacionais; módulos de ficha técnica e estoque incluídos no plano do PDV; localização fiscal do ERP open source; desconto por volume para redes; salários e infraestrutura são estimativas.
