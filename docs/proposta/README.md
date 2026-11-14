# Proposta à Raízes do Nordeste: apresentação final

> Visão do autor (D-037). Este arquivo guarda o roteiro da apresentação até a fase final do trabalho. A apresentação será um HTML feito com apoio da IA (Claude Code), e o uso será declarado em `docs/uso-de-ia/`.

## Tese

A Raízes do Nordeste deve ser uma **franquia de restaurantes tecnológica, e não uma empresa de tecnologia**. O autor atua como **interlocutor**: traduz o problema do negócio em opções, com custos, riscos e trade-offs, para que a rede decida o que é adequado ao seu momento de crescimento.

## Premissa de honestidade

Construir uma solução sob medida **não é economicamente viável na maior parte dos casos** para uma empresa em fase de crescimento. A API desenvolvida neste trabalho demonstra domínio técnico e serve de referência para avaliar fornecedores e integrações. Ela **não** é, por padrão, a recomendação de compra. A apresentação deve mostrar como o mercado costuma decidir: **comprar o que é commodity, integrar o que é crítico e construir só o que diferencia.**

## Estrutura prevista

1. **O problema do negócio:** expansão, multicanal, unidades diferentes, LGPD, pico (resumo do estudo de caso).
2. **O que foi construído:** arquitetura em camadas, fluxo pedido → pagamento → status, segurança/LGPD, testes. Demonstração ao vivo e links públicos.
3. **A visão analítica:** dados como ativo da empresa (DW → Lakehouse), mesmo usando ferramentas de prateleira.
4. **Construir × comprar × integrar:** matriz de decisão por capacidade (PDV/pedidos, cardápio digital e totem, delivery, pagamentos, estoque/ERP, fidelidade/CRM, BI, automação, IA). Para cada uma: opção gratuita/open source, opção paga de prateleira e opção sob medida, com custo estimado, prazo, risco, aprisionamento ao fornecedor (*lock-in*) e quando faz sentido cada uma.
5. **IA e automação aplicadas:** casos concretos e de baixo risco (atendimento, previsão de demanda e de compras, análise de vendas, campanhas) com o cuidado de LGPD.
6. **Custo total de propriedade (TCO):** comparação em 3 anos entre ecossistema de prateleira e construção própria (equipe, infraestrutura, manutenção, segurança, conformidade).
7. **Roadmap por fase de crescimento:** o que adotar com 5, 20 e 50+ unidades e os sinais de que vale a pena construir algo próprio.
8. **Recomendação e próximos passos**, deixando a decisão com o cliente.

## Regras para a pesquisa de ferramentas (fase final)

- Preços e planos mudam: pesquisar **perto da entrega**, citando fonte e data de consulta de cada valor.
- Nenhuma ferramenta é recomendada sem justificativa ligada a um requisito do estudo de caso.
- Avaliar sempre: LGPD/hospedagem de dados, API/integração (para não perder os próprios dados), custo por unidade franqueada e suporte no Brasil.
