import { ArrowUpRight, BusFront, Database, Radio, RefreshCw, Search } from "lucide-react";
import type { AppData, Vehicle } from "../types";
import { Card, Panel, Empty } from "./Layout";
import { brDate, number } from "../data";

/** Tela de monitoramento: referências efetivamente recebidas, sem simulação. */
export default function MonitoringPage({
  data, live, clock, query, setQuery, github
}: {
  data: AppData;
  live: Vehicle[];
  clock: number;
  query: string;
  setQuery: (value: string) => void;
  github: string;
}) {
  return (<>

                  <div className="metrics">
                    <Card
                      title="Posições recentes"
                      value={
                        ["available", "reference"].includes(data.vehicles.status)
                          ? number(live.length)
                          : "Não disponível"
                      }
                      description="Até 3 minutos desde a consulta, não do GPS original"
                      icon={Radio}
                    />
                    <Card
                      title="Linhas observadas"
                      value={
                        ["available", "reference"].includes(data.vehicles.status)
                          ? number(new Set(live.map((v) => v.route_id)).size)
                          : "Não disponível"
                      }
                      description="Não equivale à oferta total"
                      icon={BusFront}
                    />
                    <Card
                      title="Última consulta da posição"
                      value={
                        data.vehicles.generated_at
                          ? brDate(data.vehicles.generated_at, true)
                          : "Não disponível"
                      }
                      description="Hora de obtenção do arquivo"
                      icon={RefreshCw}
                    />
                    <Card
                      title="Histórico operacional"
                      value="Pendente"
                      description="Worker e armazenamento a implantar"
                      icon={Database}
                    />
                  </div>
                  <Panel
                    title="Monitoramento da frota"
                    subtitle="Coordenadas reais consultadas, sem interpolação ou simulação"
                  >
                    {data.vehicles.status === "reference" && (
                      <p className="notice warning" role="note">
                        Posição obtida em consulta à TACOM, sem timestamp original de GPS.
                        Itinerários/linhas são referências ainda não homologadas.
                        SC significa sem comunicação e SG, sem GPS. Um ícone parado
                        não comprova ônibus imobilizado.
                      </p>
                    )}
                    <div className="search">
                      <Search size={17} />
                      <input
                        aria-label="Buscar veículo"
                        placeholder="Identificador do veículo ou linha"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                      />
                    </div>
                    {live.length ? (
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>Veículo</th>
                              <th>Linha</th>
                              <th>Última consulta</th>
                              <th>Idade da consulta</th>
                              <th>Sinal</th>
                              <th>Velocidade</th>
                            </tr>
                          </thead>
                          <tbody>
                            {live
                              .filter((v) =>
                                (v.vehicle_id + " " + v.route_id).includes(
                                  query,
                                ),
                              )
                              .map((v) => (
                                <tr key={v.source_id + v.vehicle_id}>
                                  <td>{v.vehicle_id}</td>
                                  <td>{v.route_id}</td>
                                  <td>{brDate(v.fetched_at, true)}</td>
                                  <td>{Math.max(0, Math.floor((clock - Date.parse(v.fetched_at))/1000))} s</td>
                                  <td>{v.signal_status === "SC" ? "Sem comunicação" : v.signal_status === "SG" ? "Sem GPS" : "Recebido"}</td>
                                  <td>
                                    {number(v.speed_kmh, 1)}{" "}
                                    {v.speed_kmh != null ? "km/h" : ""}
                                  </td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <Empty
                        title="GPS de Canoas ainda não homologado"
                        icon={Radio}
                      >
                        {data.vehicles.message} Os horários programados
                        continuam disponíveis. Não é possível inferir veículos
                        em operação ou viagens canceladas.
                      </Empty>
                    )}
                  </Panel>
                  <Panel title="Próxima condição para ativação">
                    <p>
                      Validar a origem e o contrato da API municipal, obter a
                      frequência autorizada e implantar o worker persistente. A
                      estrutura de ingestão, histórico e consulta protegida está
                      no repositório.
                    </p>
                    <a
                      className="text-link"
                      href={github + "/blob/main/docs/OPERACAO.md"}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Consultar operação da infraestrutura
                      <ArrowUpRight size={15} />
                    </a>
                  </Panel>
                
  </>);
}
