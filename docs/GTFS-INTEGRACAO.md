# Integração GTFS Static — Canoas (2026-11-15)

## Escopo implementado
A rota **#gtfs** do WebGIS adiciona um explorador da rede e da programação estática, mantendo isoladas as coletas de ônibus ao vivo e as camadas de referência Sogal/NGS/TACOM.

- Leitura no próprio navegador de ZIP GTFS ou de múltiplos arquivos `.txt` descompactados (navegador com `DecompressionStream('deflate-raw')` para ZIP).
- Verificação de arquivos obrigatórios, IDs e integridade referencial básica; limite de tamanho contra ZIP bombs.
- Consulta das linhas por `route_short_name`, seleção das variantes por `route_id`, distinção de `direction_id`, shapes por `shape_id`.
- Mapa Leaflet da variante, pontos ordenados por `stop_sequence` e limite oficial do município local já presente no projeto.
- Data de serviço com avaliação de `calendar.txt`, listagem de viagens reais do feed e histograma das horas **preenchidas**; exportação CSV.
- Nenhuma interpolação de horários: 107.669 das 113.387 linhas de `stop_times.txt` não possuem `departure_time` no anexo. Ausência não é motivo para calcular ETA.
- Upload processado localmente, sem envio para servidor. Caso exista `public/data/gtfs-canoas.zip` no deploy, a página carrega o arquivo automaticamente.

## Diagnóstico do arquivo fornecido
Arquivo: **Dados GTFS.zip**; SHA-256 `d3f56b27364fa620c6eb619c2a757c34b71539bac8f6e61152809ac8f60aab9b`.

| Entidade | Quantidade |
| --- | ---: |
| `routes.txt` | 122 variantes, 76 códigos distintos |
| `trips.txt` | 2.860 viagens |
| `stops.txt` | 1.582 pontos, 1.410 referenciados em viagens |
| `stop_times.txt` | 113.387 registros |
| `shapes.txt` | 47.990 vértices, 324 shapes |
| `calendar.txt` | 6 serviços declarados |
| Vigência declarada | 06/11/2026 a 06/02/2027 |

**Atenção:** não concluir que 76 códigos GTFS são equivalentes a 76 linhas operacionais vigentes. `fare_attributes.price = 0.0` não é prova de tarifa gratuita. O feed não contém `calendar_dates.txt`; feriados e exceções não estão especificados. A agência informada é `Teu Bilhete`.

## Publicação permanente e automatizada
**Concluído no GitHub:** o ZIP original foi incluído no repositório, renomeado sem recompressão, e está nas duas pastas: `inputs/gtfs-canoas.zip` e `public/data/gtfs-canoas.zip`. Ambos referenciam o mesmo blob Git; o SHA-256 foi conferido. A publicação automática no Pages depende de o GitHub Actions voltar a iniciar jobs. Para atualizar o feed futuramente, substitua o ZIP de origem neste caminho:

```
inputs/gtfs-canoas.zip
```

O workflow `.github/workflows/ci-pages.yml` verificará esse caminho, executará:

```bash
python scripts/publish_gtfs.py inputs/gtfs-canoas.zip
```

O script audita os relacionamentos do feed e copia o **ZIP original** sem modificações para `public/data/gtfs-canoas.zip` (entregue pelo Pages), mais `public/data/gtfs-feed-manifest.json` com SHA-256 e quantidades. Falha de validação interrompe o build. Com o ZIP versionado, a compilação está preparada para expor o feed automaticamente. A página também oferece importação local como contingência. O GitHub Actions vinha falhando **antes do início do job** em execuções anteriores, sem consumir minutos de runner; ver [Issue #3](https://github.com/marcianolima/webgis-transporte-canoas/issues/3).

Não adicionar tokens, credenciais, URLs autenticadas ou dados sensíveis ao repositório. Uma atualização do GTFS deve substituir o ZIP e repetir a verificação de consistência; o painel indica vigência e não presume atualização automática do fornecedor.

## Compatibilidade e cruzamentos
- **NGS/Sogal**: saída programada coletada do sistema existente; não sobrescrever com dados GTFS.
- **TACOM/GoBus**: coordenadas e eventos observados, quando disponíveis; nunca gerar posição de ônibus a partir de `shapes.txt`, `trips.txt` ou horários estáticos.
- **GTFS**: itinerários e calendário **de referência**, que podem ajudar a sanar lacunas geográficas ou a avaliar completude, sem homologar automaticamente equivalência dos IDs.
- **Segurança viária** (MHTML fornecido): a página de referência menciona 7.664 sinistros com vítimas de 2023 a agosto/2026, 9.232 vítimas, 102 óbitos e somente 2.049 sinistros com ponto cartográfico (27%). Isso **não constitui um dataset** de sinistros importado no WebGIS. Integração de exposição espacial exigirá dados originais georreferenciados, procedência e critérios por trecho e período. Um corredor de ônibus próximo a um sinistro não demonstra relação causal.

## Validação
A pipeline contém `npm run lint`, `npm test`, `npm run build`, `pytest` e validação das camadas existentes, agora com exceção estrita para o ZIP GTFS e conferência de SHA-256, quantidades e calendário contra o manifesto. A execução do Actions não está homologada enquanto o GitHub não provisionar o runner. Testes específicos de parsing e consistência do GTFS foram adicionados. A homologação do feed operacional por TACOM/Secretaria permanece distinta dos testes técnicos da interface.
