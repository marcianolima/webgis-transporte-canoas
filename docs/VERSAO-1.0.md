# Caminho verificável para a versão 1.0 — 31/10/2026

A versão 0.4.0 publica **57 itinerários de 36 linhas e 1.410 paradas TACOM**, com origem, hashes e datas, além de programação real NGS e território. São referências da API; não homologam vigência, equivalência aos horários ou operação atual. Consulte [COBERTURA-PARADAS.md](COBERTURA-PARADAS.md).

| Critério | Estado atual | Dependência para encerramento |
| --- | --- | --- |
| Repositório, CI/CD e documentação | Implementados; workflow e testes presentes | Conferir o run/deploy de cada revisão |
| Frontend e mapa | PMTiles local, filtros, modo compatível e fallback GeoJSON | Testes em aparelhos e navegadores usados em campo |
| Cartografia territorial | 18 bairros e 659 setores locais | Revalidar fonte original; obter limite municipal homologado |
| Linhas e horários | 81 IDs, 4.990 saídas, cinco datas no snapshot de 30/10/2026 | Acompanhar alterações, calendários e programação oficial |
| Trajetos | 57 itinerários de 36 linhas, todos de referência; oito sob revisão de borda | Completar sentidos/variantes, vigência e vínculos; não inferir remoção de ausência em amostra |
| Paradas | 1.410 de 1.433 IDs com posição publicada; 23 fora da referência, em revisão | Revisar 23 posições; conciliar as nove linhas sem lista correspondente; obter cadastro vigente completo e homologar sequência/atendimento |
| Retomada da coleta | Cache/histórico, timeout, retry, progresso e publicação isolada testados | Disco privado persistente para conservar capturas entre runners |
| Engenharia reversa | APK e contratos mapeados; problema do serviço de coordenadas por linha isolado | Acordar contrato estável e canal seguro de produção com fornecedor |
| GPS e ETA público | Não publicados como monitoramento atual | Timestamp de medição embarcada, limites, adaptador real e infraestrutura persistente |
| Histórico e backend | Código, SQLite e modelo PostgreSQL/PostGIS preparados | Hospedagem, TLS, backups e recuperação testada em produção |
| Gestão restrita | Painel privado com chave técnica | Autenticação nominal municipal, perfis e homologação de acesso |
| Indicadores de programação | Calculados com dados reais | Conferência por data/sentido; não representam viagens realizadas |
| Auditoria operacional | Regras unitárias testadas, sem ocorrências inventadas | GPS temporal confiável, associação de viagens, critérios contratuais e revisão humana |
| Análise territorial | Área, população, paradas, buffers e extensão da amostra | Cobertura completa, equipamentos e rede de pedestres para acessibilidade |
| Relatórios | CSV/JSON/GeoJSON e impressão do navegador | Homologar dispositivos e relatórios fiscais com evidências reais |
| Acessibilidade e aceite | QA desktop e viewport móvel; sem auditoria WCAG integral | Teclado, leitor de tela, contraste, usuários de campo e aceite municipal |

Prioridades seguintes: ampliar coordenadas de paradas e variantes com capturas limitadas; conciliar códigos/sentidos/vigência com o fornecedor; confirmar timestamp e contrato GPS; implantar backend; homologar indicadores com a fiscalização. Nenhuma ausência de GPS ou de previsão comprova cancelamento, viagem não realizada ou infração.
