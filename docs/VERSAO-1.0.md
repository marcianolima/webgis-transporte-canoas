# Caminho verificável para a versão 1.0

A versão publicada nesta revisão é **0.2.0**, com programação e território reais, mapa PMTiles e importador de percursos. A existência de telas, algoritmos e infraestrutura no código não encerra a homologação de integrações ou operação municipal.

| Critério | Estado em 0.2.0 | Evidência / condição para encerramento |
| --- | --- | --- |
| Repositório e documentação | Implementados | Código, instruções, contratos, modelo, testes e metodologia versionados |
| Frontend público | Pipeline de Pages existente; verificar o run desta revisão | Build, deploy e carregamento público precisam concluir com sucesso a cada release |
| Desktop/mobile | Verificados no navegador de QA | Viewport móvel interno 390×844; falta validar aparelhos e navegadores usados em campo |
| Mapa funcional | PMTiles local + modo compatível + fallback GeoJSON | 18 bairros, 659 setores; sem dependência de chave ou servidor de desenvolvimento |
| Cartografia oficial | Base de bairros integrada de projeto anterior | Revalidar publicação original; obter limite municipal oficial, hoje união derivada de bairros |
| Linhas/horários | 81 IDs e 4.990 saídas em cinco datas no snapshot de 30/10/2026 | Coleta NGS real; assegurar autorização/estabilidade operacional e conferir alterações |
| Trajetos | Desenho, filtros e importador implementados; 0 linhas com geometria real | Obter GeoJSON/GTFS municipal com códigos, sentidos, variantes, origem e vigência; homologar |
| Paradas | Pendente | Cadastro geográfico, sequência, atendimento e sentidos homologados |
| GoBus/TACOM | Engenharia reversa **estática do APK 1.29.1.2 concluída**; acesso operacional não homologado | Host e caminhos/estruturas identificados; confirmar retorno municipal de `cidadesApp`, sigla de cidade, condições de consulta, payload e timestamp de GPS. Ver [relatório](APK-GOBUS-1.29.1.2.md) |
| GPS/ETA | Não homologados | Veículo, linha, sentido, timestamp de origem, atualização autorizada; validar ETA contra observações |
| Histórico estático | SQLite implementado | Disco persistente e backup para continuidade; cache do Actions é apenas auxiliar |
| Histórico GPS e backend | Código e infraestrutura preparados | Implantar Postgres/PostGIS, API, worker, TLS, monitoramento e restaurar backup em teste |
| Gestão restrita | Chave técnica e painel privado testados localmente | Autenticação municipal nominal, perfis, trilha administrativa e homologação do ambiente |
| Indicadores de programação | Calculados com dados reais | Conferir quadro por data/sentido; não representam viagens realizadas |
| Regularidade e pontualidade observadas | Pendentes de dados | Extrair passagens e associar viagens; definir cobertura/amostragem mínima e tolerâncias com o município |
| Auditoria geográfica | Regras unitárias testadas; sem ocorrências operacionais inventadas | Shapes temporais autorizados, GPS confiável, desvios temporários e revisão humana das evidências |
| Relatórios | CSV/JSON e impressão/PDF do navegador disponíveis | Homologar impressão/download nos dispositivos; relatórios fiscais dependem dos dados reais |
| Análise territorial | Bairros, setores, população e métricas de área | Paradas/linhas para cobertura; rede de pedestres e equipamentos para acessibilidade |
| Qualidade e recuperação | Validações, logs, backoff e fallback implementados | Exercitar falhas da fonte real e procedimentos na infraestrutura de produção |
| Acessibilidade e aceite | Sem auditoria WCAG integral / sem aceite municipal | Teste com teclado, leitor de tela, contraste e usuários; homologação formal |

## Prioridade de execução

1. Solicitar ao responsável pela operação os percursos e paradas municipais com identificadores, sentidos e datas de vigência. O importador permite conferir e publicar geometria sem depender de concluir a análise do APK.
2. **APK 1.29.1.2 recebido e analisado:** executar homologação autorizada dos contratos efetivamente encontrados, validar `cidadesApp`, escopo Canoas e correspondências SIU↔NGS. O APK confirma os caminhos, mas não prova que a API esteja acessível ou autorizada para ingestão.
3. Homologar uma amostra real de GPS: timestamps, coordenadas, identificação, atraso, periodicidade e limites. Só então configurar e executar o worker contínuo.
4. Implantar backend persistente, autenticação nominal e backups. Reprocessar histórico com versões de trajetos e algoritmos identificadas.
5. Homologar indicadores com documentos e evidências operacionais, testar em campo e registrar aceite. Não inferir cancelamento ou infração da ausência de GPS.

Nenhum desses acessos foi contornado. O desenvolvimento independente avançou com mapa, importadores, validações, documentação e testes; dados operacionais ausentes continuam identificados como pendentes.
