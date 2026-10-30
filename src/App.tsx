import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  BookOpen,
  BusFront,
  CalendarDays,
  Check,
  ChevronRight,
  Clock3,
  Database,
  FileText,
  Globe2,
  LayoutDashboard,
  Map,
  MapPin,
  Moon,
  Navigation,
  Radio,
  RefreshCw,
  Search,
  ShieldCheck,
  Sun,
  Target,
  TriangleAlert,
  WifiOff,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  base,
  brDate,
  csv,
  currentVehicles,
  download,
  filterDepartures,
  freshness,
  groupSchedules,
  headways,
  loadData,
  number,
} from "./data";
import type { AppData, Departure, Vehicles } from "./types";
const TransportMap = lazy(() => import("./components/TransportMap"));
const Chart = lazy(() => import("./components/Chart"));
const github = "https://github.com/marcianolima/webgis-transporte-canoas";
const pages = [
  {
    id: "geral",
    label: "Painel geral",
    icon: LayoutDashboard,
    group: "Visão municipal",
  },
  {
    id: "mapa",
    label: "Mapa de transporte",
    icon: Map,
    group: "Explorar a rede",
  },
  { id: "linhas", label: "Linhas e itinerários", icon: BusFront, group: "" },
  { id: "paradas", label: "Pontos de parada", icon: MapPin, group: "" },
  {
    id: "monitoramento",
    label: "Monitoramento",
    icon: Radio,
    group: "Operação e gestão",
  },
  {
    id: "auditoria",
    label: "Auditoria operacional",
    icon: ShieldCheck,
    group: "",
  },
  { id: "indicadores", label: "Indicadores", icon: BarChart3, group: "" },
  { id: "territorio", label: "Análise territorial", icon: Globe2, group: "" },
  {
    id: "relatorios",
    label: "Relatórios",
    icon: FileText,
    group: "Dados abertos",
  },
  { id: "dados", label: "Dados e metodologia", icon: BookOpen, group: "" },
];
const subtitles: Record<string, string> = {
  geral: "Rede municipal, programação e qualidade da informação.",
  mapa: "Explore as bases geográficas e as camadas disponíveis.",
  linhas: "Consulte saídas programadas e a sequência de logradouros.",
  paradas: "Localização e proveniência dos pontos disponíveis.",
  monitoramento: "Posições observadas, atualização e disponibilidade do GPS.",
  auditoria: "Critérios técnicos para a análise de evidências operacionais.",
  indicadores: "Indicadores reproduzíveis, com suas fórmulas e limitações.",
  territorio: "Transporte e território: bairros e setores do Censo 2022.",
  relatorios: "Selecione um recorte e exporte os dados com sua origem.",
  dados: "Fontes, situação das integrações e metodologia aberta.",
};
const statusLabel: Record<string, string> = {
  available: "Disponível",
  partial: "Parcial",
  pending: "Pendente",
  blocked: "Não homologado",
};
function Card({
  title,
  value,
  description,
  icon: Icon,
  tone = "",
}: {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
  tone?: string;
}) {
  return (
    <article className={"metric " + tone}>
      <div className="metric-top">
        <span>{title}</span>
        <Icon size={19} />
      </div>
      <strong>{value}</strong>
      <p>{description}</p>
    </article>
  );
}
function Panel({
  title,
  subtitle,
  children,
  action,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-title">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
function Empty({
  title,
  children,
  icon: Icon = WifiOff,
}: {
  title: string;
  children: React.ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Icon size={25} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function Method({
  name,
  formula,
  unit,
  requirements,
  limitation,
}: {
  name: string;
  formula: string;
  unit: string;
  requirements: string;
  limitation: string;
}) {
  return (
    <details className="method">
      <summary>
        {name}
        <ChevronRight size={16} />
      </summary>
      <dl>
        <dt>Fórmula</dt>
        <dd>{formula}</dd>
        <dt>Unidade</dt>
        <dd>{unit}</dd>
        <dt>Requisitos</dt>
        <dd>{requirements}</dd>
        <dt>Limitação</dt>
        <dd>{limitation}</dd>
      </dl>
    </details>
  );
}
function MapBox({
  data,
  territorial = false,
}: {
  data: AppData;
  territorial?: boolean;
}) {
  return (
    <Suspense fallback={<div className="loading-map">Carregando mapa…</div>}>
      <TransportMap data={data} territorial={territorial} />
    </Suspense>
  );
}
function Schedules({ items }: { items: Departure[] }) {
  const groups = groupSchedules(items);
  return groups.length ? (
    <div className="schedules">
      {groups.map((g) => (
        <div key={g.direction}>
          <h3>
            <Navigation size={15} />
            {g.direction}
            <span>{number(g.items.length)} saídas</span>
          </h3>
          <div className="time-grid">
            {g.items.map((d, i) => (
              <span
                key={i}
                title={
                  "Minuto de serviço: " +
                  d.service_minute +
                  (d.service_minute >= 1440 ? " · madrugada seguinte" : "")
                }
              >
                {d.time}
                {d.service_minute >= 1440 && <sup>+1</sup>}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  ) : (
    <Empty title="Sem horário neste recorte" icon={Clock3}>
      Não há partidas validadas para os filtros selecionados. Consulte a
      situação da coleta e a fonte.
    </Empty>
  );
}
function App() {
  const [data, setData] = useState<AppData | null>(null),
    [error, setError] = useState(""),
    [page, setPage] = useState(() => window.location.hash.slice(1) || "geral"),
    [dark, setDark] = useState(
      () => localStorage.getItem("transporte-theme") === "dark",
    ),
    [date, setDate] = useState(""),
    [routeId, setRouteId] = useState(""),
    [query, setQuery] = useState(""),
    [revision, setRevision] = useState(0),
    [clock, setClock] = useState(Date.now());
  const mobileNav = useRef<HTMLElement>(null),
    main = useRef<HTMLElement>(null);
  useEffect(() => {
    const sync = () => {
      setPage(
        pages.some((p) => p.id === location.hash.slice(1))
          ? location.hash.slice(1)
          : "geral",
      );
      setQuery("");
    };
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("transporte-theme", dark ? "dark" : "light");
  }, [dark]);
  useEffect(() => {
    let active = true;
    loadData()
      .then((d) => {
        if (!active) return;
        setData(d);
        setError("");
        setDate((old) =>
          d.network.source_dates.some((x) => x.date === old)
            ? old
            : d.network.source_dates[0]?.date || "",
        );
        setRouteId((old) =>
          d.network.routes.some((r) => r.id === old)
            ? old
            : d.network.routes[0]?.id || "",
        );
      })
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [revision]);
  useEffect(() => {
    document.title =
      (pages.find((p) => p.id === page)?.label || "Painel geral") +
      " · Transporte Canoas";
    mobileNav.current
      ?.querySelector('[aria-current="page"]')
      ?.scrollIntoView?.({ inline: "start", block: "nearest" });
    if (main.current) main.current.scrollTop = 0;
    window.scrollTo(0, 0);
  }, [page]);
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 15000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    const api = import.meta.env.VITE_PUBLIC_API_BASE;
    if (!api) return;
    let stopped = false;
    const update = async () => {
      try {
        const r = await fetch(api.replace(/\/$/, "") + "/v1/vehicles", {
          signal: AbortSignal.timeout(10000),
        });
        if (!r.ok) throw new Error("API indisponível");
        const v = (await r.json()) as Vehicles;
        if (!Array.isArray(v.vehicles)) throw new Error("Contrato inválido");
        if (!stopped) setData((d) => (d ? { ...d, vehicles: v } : d));
      } catch {
        if (!stopped)
          setData((d) =>
            d
              ? {
                  ...d,
                  vehicles: {
                    ...d.vehicles,
                    status: "unavailable",
                    message:
                      "Falha de atualização da API. Posições antigas expiram em 3 minutos.",
                  },
                }
              : d,
          );
      }
    };
    update();
    const timer = setInterval(update, 60_000);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, []);
  const active = pages.find((p) => p.id === page) || pages[0];
  const routes = useMemo(
    () => data?.network.routes.filter((r) => r.dates.includes(date)) || [],
    [data, date],
  );
  const departures = useMemo(
    () => data?.network.departures.filter((d) => d.date === date) || [],
    [data, date],
  );
  useEffect(() => {
    if (routes.length && !routes.some((r) => r.id === routeId))
      setRouteId(routes[0].id);
  }, [routes, routeId]);
  const selected = data?.network.routes.find((r) => r.id === routeId);
  const live = data ? currentVehicles(data.vehicles.vehicles, clock) : [];
  const chartByHour = useMemo(
    () =>
      Array.from(
        { length: 24 },
        (_, i) =>
          departures.filter((d) => Math.floor(d.service_minute / 60) % 24 === i)
            .length,
      ),
    [departures],
  );
  const ranked = useMemo(
    () =>
      routes
        .map((r) => ({
          ...r,
          count: departures.filter((d) => d.route_id === r.id).length,
        }))
        .sort((a, b) => b.count - a.count),
    [routes, departures],
  );
  const nav = (mobile = false) => (
    <nav
      className={mobile ? "mobile-nav" : "side-nav"}
      aria-label={mobile ? "Menu móvel" : "Menu principal"}
      ref={mobile ? mobileNav : undefined}
    >
      {pages.map(({ id, label, icon: Icon, group }) => (
        <div key={id}>
          {!mobile && group && <p className="nav-group">{group}</p>}
          <a
            href={"#" + id}
            aria-current={page === id ? "page" : undefined}
            className={page === id ? "active" : ""}
          >
            <Icon size={18} />
            <span>{label}</span>
            {!mobile && page === id && <i />}
          </a>
        </div>
      ))}
    </nav>
  );
  return (
    <div className="app-shell">
      <a
        className="skip"
        href="#conteudo"
        onClick={(e) => {
          e.preventDefault();
          main.current?.focus();
        }}
      >
        Ir para conteúdo
      </a>
      <aside className="sidebar">
        <a href="#geral" className="brand">
          <span className="brand-icon">
            <BusFront size={25} />
          </span>
          <span>
            GeoCanoas<small>TRANSPORTE E MOBILIDADE</small>
          </span>
        </a>
        {nav()}
        <div className="side-foot">
          <span className="location-dot" />
          Canoas · Rio Grande do Sul
          <p>
            Dados abertos para uma cidade
            <br />
            mais conectada.
          </p>
          <a href={github} target="_blank" rel="noreferrer">
            Código e documentação <ArrowUpRight size={13} />
          </a>
          <small>v0.1 · integração em homologação</small>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            <span>GeoCanoas</span>
            <ChevronRight size={13} />
            <strong>Transporte coletivo</strong>
          </div>
          <div className="top-actions">
            <span className="scope">
              <span className="location-dot" />
              Municipal · Canoas
            </span>
            <button
              className="icon-button"
              onClick={() => setDark(!dark)}
              aria-label={dark ? "Usar tema claro" : "Usar tema escuro"}
            >
              {dark ? <Sun size={19} /> : <Moon size={19} />}
            </button>
            <a
              href={github}
              target="_blank"
              rel="noreferrer"
              className="documentation"
            >
              <BookOpen size={17} />
              Documentação
              <ArrowUpRight size={13} />
            </a>
          </div>
        </header>
        {nav(true)}
        <main ref={main} tabIndex={-1} id="conteudo">
          <div className="page-heading">
            <div>
              <p className="eyebrow">OBSERVATÓRIO DO TRANSPORTE</p>
              <h1>{active.label}</h1>
              <p>{subtitles[active.id]}</p>
            </div>
            <button
              className="refresh"
              onClick={() => setRevision((r) => r + 1)}
              title="Recarregar os arquivos publicados"
            >
              <RefreshCw size={16} />
              Atualizar leitura
            </button>
          </div>
          {error ? (
            <Empty title="Dados temporariamente indisponíveis">
              {error}.{" "}
              <button onClick={() => setRevision((r) => r + 1)}>
                Tentar novamente
              </button>
            </Empty>
          ) : !data ? (
            <div className="loading" role="status">
              Carregando fontes e dados publicados…
            </div>
          ) : (
            <>
              <div className="status-strip">
                <span>
                  <i
                    className={
                      freshness(data.network.generated_at) === "recent"
                        ? "dot"
                        : "dot amber"
                    }
                  />
                  <strong>
                    Programação{" "}
                    {data.network.status === "partial" ? "parcialmente " : ""}
                    disponível
                  </strong>
                  <span className="status-date">
                    · coletada em {brDate(data.network.generated_at, true)}
                  </span>
                </span>
                <a href="#dados">
                  <WifiOff size={14} />
                  {live.length
                    ? number(live.length) + " veículos recentes"
                    : data.vehicles.status === "available"
                      ? "Sem posições recentes"
                      : "GPS não homologado"}
                  <ArrowRight size={13} />
                </a>
              </div>
              {["geral", "linhas", "indicadores", "relatorios"].includes(
                page,
              ) && (
                <div className="filters">
                  <label>
                    <CalendarDays size={16} />
                    <span>Data de serviço</span>
                    <select
                      aria-label="Data de serviço"
                      value={date}
                      onChange={(e) => setDate(e.target.value)}
                    >
                      {data.network.source_dates.map((d) => (
                        <option key={d.date} value={d.date}>
                          {brDate(d.date)}
                          {!d.complete ? " · parcial" : ""}
                        </option>
                      ))}
                    </select>
                  </label>
                  <span className="filter-note">
                    Horários publicados pela operadora · fuso de Brasília
                  </span>
                </div>
              )}
              {freshness(data.network.generated_at) === "stale" && (
                <div className="notice warning">
                  <TriangleAlert size={18} />A última coleta tem mais de 48
                  horas. Verifique a fonte antes de planejar seu deslocamento.
                </div>
              )}
              {page === "geral" && (
                <>
                  <div className="overview-intro">
                    <div>
                      <span className="tag">REDE MUNICIPAL · SOGAL</span>
                      <h2>
                        Informação para se mover.
                        <br />
                        <em>Evidência para planejar.</em>
                      </h2>
                      <p>
                        Consulte a programação do transporte de Canoas e
                        acompanhe a disponibilidade das informações
                        operacionais.
                      </p>
                      <a className="primary" href="#linhas">
                        Consultar minha linha <ArrowRight size={17} />
                      </a>
                    </div>
                    <div className="intro-summary">
                      <div className="intro-symbol">
                        <BusFront size={48} />
                        <span className="orbit one" />
                        <span className="orbit two" />
                      </div>
                      <div>
                        <strong>{number(routes.length)}</strong>
                        <span>
                          linhas publicadas
                          <br />
                          para {brDate(date)}
                        </span>
                      </div>
                      <small>
                        Cadastro publicado por data.
                        <br />
                        Não comprova operação em tempo real.
                      </small>
                    </div>
                  </div>
                  <div className="metrics">
                    <Card
                      title="Linhas na programação"
                      value={number(routes.length)}
                      description={"Disponíveis em " + brDate(date)}
                      icon={BusFront}
                    />
                    <Card
                      title="Saídas programadas"
                      value={number(departures.length)}
                      description="Soma dos dois sentidos publicados"
                      icon={Clock3}
                    />
                    <Card
                      title="Bairros oficiais"
                      value={number(data.neighborhoods.features.length)}
                      description="Base cartográfica do GeoCanoas"
                      icon={MapPin}
                    />
                    <Card
                      title="Veículos com GPS recente"
                      value={
                        data.vehicles.status === "available"
                          ? number(live.length)
                          : "Não disponível"
                      }
                      description="Depende da homologação da fonte"
                      icon={Radio}
                      tone="muted-metric"
                    />
                  </div>
                  <div className="dashboard-grid">
                    <Panel
                      title="O transporte no território"
                      subtitle="Bairros e setores censitários · bases locais"
                      action={
                        <a href="#mapa" className="text-link">
                          Explorar mapa
                          <ArrowUpRight size={15} />
                        </a>
                      }
                    >
                      <MapBox data={data} />
                    </Panel>
                    <Panel
                      title="Linhas na programação"
                      subtitle={
                        "Maiores quantidades de saídas · " + brDate(date)
                      }
                      action={
                        <a
                          href="#linhas"
                          className="small-icon"
                          aria-label="Ver todas as linhas"
                        >
                          <ArrowUpRight size={17} />
                        </a>
                      }
                    >
                      <div className="rank-list">
                        {ranked.slice(0, 6).map((r, i) => (
                          <button
                            key={r.id}
                            onClick={() => {
                              setRouteId(r.id);
                              location.hash = "linhas";
                            }}
                          >
                            <span className="rank-no">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <span className="route-chip">{r.code}</span>
                            <span className="rank-name">
                              {r.name}
                              <small>
                                {number(r.count)} saídas programadas
                              </small>
                            </span>
                            <ChevronRight size={15} />
                          </button>
                        ))}
                      </div>
                      <a className="panel-bottom" href="#linhas">
                        Consultar todas as linhas <ArrowRight size={15} />
                      </a>
                    </Panel>
                  </div>
                  <div className="two-columns">
                    <Panel
                      title="Oferta programada ao longo do dia"
                      subtitle="Quantidade de saídas por hora, incluindo a madrugada seguinte"
                    >
                      <Suspense fallback={<p>Carregando gráfico…</p>}>
                        <Chart
                          labels={Array.from(
                            { length: 24 },
                            (_, i) => String(i).padStart(2, "0") + "h",
                          )}
                          values={chartByHour}
                        />
                      </Suspense>
                      <p className="caption">
                        Fonte: Sogal / NGS. Não representa viagens realizadas.
                      </p>
                    </Panel>
                    <Panel
                      title="Qualidade e transparência"
                      subtitle="O que você pode consultar nesta versão"
                    >
                      <div className="source-list">
                        {data.catalogue.integrations.slice(0, 4).map((s) => (
                          <div key={s.id}>
                            <span className={"source-icon " + s.status}>
                              {s.status === "available" ? (
                                <Check size={17} />
                              ) : (
                                <Clock3 size={17} />
                              )}
                            </span>
                            <div>
                              <strong>{s.name}</strong>
                              <small>{s.description}</small>
                            </div>
                            <span className={"badge " + s.status}>
                              {statusLabel[s.status]}
                            </span>
                          </div>
                        ))}
                      </div>
                      <a className="text-link" href="#dados">
                        Ver fontes e limitações
                        <ArrowRight size={15} />
                      </a>
                    </Panel>
                  </div>
                </>
              )}
              {page === "mapa" && (
                <>
                  <div className="notice">
                    <MapPin size={18} />
                    <div>
                      Base territorial disponível. Trajetos geográficos das
                      linhas e associação entre linhas e paradas aguardam uma
                      fonte homologada. O itinerário textual está em{" "}
                      <a href="#linhas">Linhas e itinerários</a>.
                    </div>
                  </div>
                  <MapBox data={data} />
                  <div className="three-columns">
                    <Panel title="Bairros oficiais">
                      <p>
                        {number(data.neighborhoods.features.length)} polígonos
                        da base do GeoCanoas, preservados localmente.
                      </p>
                    </Panel>
                    <Panel title="Censo 2022">
                      <p>
                        {number(data.sectors.features.length)} setores com
                        população. Use o seletor de camadas do mapa.
                      </p>
                    </Panel>
                    <Panel title="Posições observadas">
                      <p>
                        {live.length
                          ? number(live.length) +
                            " veículos com posição de até 3 minutos."
                          : "Não há integração GPS homologada. Nenhum veículo simulado é exibido."}
                      </p>
                    </Panel>
                  </div>
                </>
              )}
              {page === "linhas" && (
                <div className="lines-layout">
                  <Panel
                    title="Encontre sua linha"
                    subtitle={
                      number(routes.length) + " linhas publicadas nesta data"
                    }
                  >
                    <div className="search">
                      <Search size={17} />
                      <input
                        aria-label="Buscar linha"
                        placeholder="Código, bairro ou destino"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                      />
                    </div>
                    <div className="line-list">
                      {routes
                        .filter((r) =>
                          (r.code + " " + r.name)
                            .normalize("NFD")
                            .replace(/[\u0300-\u036f]/g, "")
                            .toLowerCase()
                            .includes(
                              query
                                .normalize("NFD")
                                .replace(/[\u0300-\u036f]/g, "")
                                .toLowerCase(),
                            ),
                        )
                        .map((r) => (
                          <button
                            key={r.id}
                            className={r.id === routeId ? "selected" : ""}
                            onClick={() => setRouteId(r.id)}
                            aria-pressed={r.id === routeId}
                          >
                            <span className="route-chip">{r.code}</span>
                            <span>{r.name}</span>
                            <ChevronRight size={14} />
                          </button>
                        ))}
                    </div>
                  </Panel>
                  <div>
                    {selected ? (
                      <>
                        <Panel
                          title={selected.code + " · " + selected.name}
                          subtitle="Programação publicada pela operadora"
                        >
                          <div className="route-meta">
                            <span>
                              <BusFront size={16} />
                              Sogal · municipal
                            </span>
                            <span>
                              <CalendarDays size={16} />
                              {brDate(date)}
                            </span>
                            <span>
                              <Clock3 size={16} />
                              {number(
                                departures.filter(
                                  (d) => d.route_id === selected.id,
                                ).length,
                              )}{" "}
                              saídas
                            </span>
                          </div>
                          <Schedules
                            items={departures.filter(
                              (d) => d.route_id === selected.id,
                            )}
                          />
                          <p className="caption">
                            As horas são saídas programadas. Não são previsões
                            de chegada às paradas. “+1” indica a madrugada
                            seguinte.
                          </p>
                          <a
                            className="text-link"
                            href={data.network.source_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Conferir na fonte
                            <ArrowUpRight size={14} />
                          </a>
                        </Panel>
                        <Panel
                          title="Itinerário em logradouros"
                          subtitle="Sequência original publicada, sem separação homologada de sentidos ou variantes"
                        >
                          {selected.itinerary.length ? (
                            <details className="itinerary">
                              <summary>
                                {number(selected.itinerary.length)} registros de
                                logradouros · expandir
                              </summary>
                              <ol>
                                {selected.itinerary.map((p, i) => (
                                  <li key={i}>
                                    <span>
                                      {p.street_type} {p.street}
                                    </span>
                                    <small>
                                      {p.city} · ordem {p.sequence}
                                    </small>
                                  </li>
                                ))}
                              </ol>
                            </details>
                          ) : (
                            <Empty
                              title="Itinerário não disponível"
                              icon={Navigation}
                            >
                              A fonte não forneceu uma sequência validada para
                              esta linha.
                            </Empty>
                          )}
                          <p className="caption">
                            Repetições são preservadas. A lista não permite
                            deduzir coordenadas de paradas.
                          </p>
                        </Panel>
                      </>
                    ) : null}
                  </div>
                </div>
              )}
              {page === "paradas" && (
                <>
                  <div className="notice warning">
                    <TriangleAlert size={18} />
                    <span>
                      {data.stops.features.length
                        ? "Paradas do OpenStreetMap são referências colaborativas. Sua vinculação à rede municipal e situação de atendimento não estão homologadas."
                        : "Cadastro geográfico de paradas municipais ainda não homologado. A ausência de pontos não significa ausência de atendimento."}
                    </span>
                  </div>
                  <MapBox data={data} />
                  {data.stops.features.length ? (
                    <Panel
                      title="Pontos disponíveis"
                      subtitle="OpenStreetMap · dados colaborativos"
                    >
                      <div className="search">
                        <Search size={17} />
                        <input
                          aria-label="Buscar ponto"
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                          placeholder="Nome ou identificador"
                        />
                      </div>
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>Identificador OSM</th>
                              <th>Nome informado</th>
                              <th>Bairro</th>
                              <th>Fonte</th>
                            </tr>
                          </thead>
                          <tbody>
                            {data.stops.features
                              .filter((f) =>
                                JSON.stringify(f.properties)
                                  .toLowerCase()
                                  .includes(query.toLowerCase()),
                              )
                              .map((f) => (
                                <tr key={String(f.id)}>
                                  <td>
                                    <a
                                      href={
                                        "https://www.openstreetmap.org/node/" +
                                        f.id
                                      }
                                      target="_blank"
                                      rel="noreferrer"
                                    >
                                      {String(f.id)}
                                    </a>
                                  </td>
                                  <td>
                                    {f.properties?.name ||
                                      "Sem nome cadastrado"}
                                  </td>
                                  <td>
                                    {f.properties?.neighborhood ||
                                      "Não identificado"}
                                  </td>
                                  <td>OSM</td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    </Panel>
                  ) : (
                    <Panel title="Cadastro de pontos">
                      <Empty title="Fonte de paradas pendente" icon={MapPin}>
                        As consultas de linhas atendidas, sequências e previsões
                        serão habilitadas com dados validados. Veja o
                        diagnóstico em Dados e metodologia.
                      </Empty>
                    </Panel>
                  )}
                </>
              )}
              {page === "monitoramento" && (
                <>
                  <div className="metrics">
                    <Card
                      title="Posições recentes"
                      value={
                        data.vehicles.status === "available"
                          ? number(live.length)
                          : "Não disponível"
                      }
                      description="Até 3 minutos desde a observação"
                      icon={Radio}
                    />
                    <Card
                      title="Linhas observadas"
                      value={
                        data.vehicles.status === "available"
                          ? number(new Set(live.map((v) => v.route_id)).size)
                          : "Não disponível"
                      }
                      description="Não equivale à oferta total"
                      icon={BusFront}
                    />
                    <Card
                      title="Última coleta GPS"
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
                    subtitle="Somente posições efetivamente observadas"
                  >
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
                              <th>Posição observada</th>
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
                                  <td>{brDate(v.observed_at, true)}</td>
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
                </>
              )}
              {page === "auditoria" && (
                <>
                  <div className="notice warning">
                    <ShieldCheck size={19} />
                    <span>
                      Ocorrências técnicas apoiam a fiscalização; não constituem
                      infração automática. Sem histórico GPS validado, os
                      resultados operacionais são inconclusivos.
                    </span>
                  </div>
                  <div className="two-columns">
                    <Panel title="Evidências operacionais">
                      <Empty
                        title="Sem histórico operacional homologado"
                        icon={ShieldCheck}
                      >
                        Não há base para calcular atrasos, viagens não
                        observadas, desvios ou comboios. A ausência de GPS não
                        comprova cancelamento de viagem.
                      </Empty>
                    </Panel>
                    <Panel title="Camadas de acesso">
                      <div className="check-list">
                        <p>
                          <Check size={18} />
                          Público: programação, fontes e metodologia
                        </p>
                        <p>
                          <Check size={18} />
                          Backend: histórico de posições e ocorrências
                        </p>
                        <p>
                          <Check size={18} />
                          Autenticado: evidências e registros de revisão
                        </p>
                      </div>
                      <p className="caption">
                        O GitHub Pages não armazena registros administrativos
                        restritos.
                      </p>
                    </Panel>
                  </div>
                  <Panel
                    title="Critérios implementados no motor de análise"
                    subtitle="Algoritmos testados com fixtures sintéticas isoladas; não homologados sobre operação real"
                  >
                    {data.catalogue.methodologies
                      .filter((m) =>
                        ["jump", "deviation", "stopped", "headway"].includes(
                          m.id,
                        ),
                      )
                      .map((m) => (
                        <Method key={m.id} {...m} />
                      ))}
                  </Panel>
                  <Panel title="Qualificação das conclusões">
                    <div className="three-columns">
                      <div>
                        <span className="badge available">Confirmada</span>
                        <p>
                          Exige evidência documental ou validação humana. O
                          motor não produz infrações confirmadas.
                        </p>
                      </div>
                      <div>
                        <span className="badge partial">Provável</span>
                        <p>
                          Evidências consistentes e cobertura suficiente,
                          sujeitas à conferência de desvios autorizados.
                        </p>
                      </div>
                      <div>
                        <span className="badge pending">Inconclusiva</span>
                        <p>
                          Dados insuficientes, intervalos de coleta grandes ou
                          divergência compatível com erro GPS.
                        </p>
                      </div>
                    </div>
                  </Panel>
                </>
              )}
              {page === "indicadores" && (
                <>
                  <div className="metrics">
                    <Card
                      title="Saídas programadas"
                      value={number(departures.length)}
                      description={brDate(date) + " · todos os sentidos"}
                      icon={Clock3}
                    />
                    <Card
                      title="Linhas com horário"
                      value={number(
                        new Set(departures.map((d) => d.route_id)).size,
                      )}
                      description="Pelo menos uma saída na fonte"
                      icon={BusFront}
                    />
                    <Card
                      title="Datas disponíveis"
                      value={number(data.network.source_dates.length)}
                      description="Sem extrapolação de calendário"
                      icon={CalendarDays}
                    />
                    <Card
                      title="Pontualidade observada"
                      value="Não disponível"
                      description="Exige GPS e associação a viagens"
                      icon={Target}
                    />
                  </div>
                  <div className="two-columns">
                    <Panel
                      title="Programação por linha"
                      subtitle="10 linhas com mais saídas na data selecionada"
                    >
                      <Suspense fallback={<p>Carregando gráfico…</p>}>
                        <Chart
                          labels={ranked
                            .slice(0, 10)
                            .reverse()
                            .map((r) => r.code)}
                          values={ranked
                            .slice(0, 10)
                            .reverse()
                            .map((r) => r.count)}
                          horizontal
                        />
                      </Suspense>
                    </Panel>
                    <Panel
                      title="Comparação entre datas"
                      subtitle="Totais publicados; calendário limitado às datas da fonte"
                    >
                      <Suspense fallback={<p>Carregando gráfico…</p>}>
                        <Chart
                          labels={data.network.source_dates.map((d) =>
                            brDate(d.date),
                          )}
                          values={data.network.source_dates.map(
                            (d) =>
                              data.network.departures.filter(
                                (r) => r.date === d.date,
                              ).length,
                          )}
                        />
                      </Suspense>
                    </Panel>
                  </div>
                  <Panel title="Indicadores por linha">
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Linha</th>
                            <th>Nome</th>
                            <th>Saídas</th>
                            <th>Intervalo médio programado¹</th>
                            <th>Observações para o intervalo</th>
                          </tr>
                        </thead>
                        <tbody>
                          {ranked.map((r) => {
                            const gaps = headways(
                              departures.filter((d) => d.route_id === r.id),
                            );
                            return (
                              <tr key={r.id}>
                                <td>{r.code}</td>
                                <td>{r.name}</td>
                                <td>{r.count}</td>
                                <td>
                                  {gaps.length
                                    ? number(
                                        gaps.reduce((a, b) => a + b, 0) /
                                          gaps.length,
                                        1,
                                      ) + " min"
                                    : "Não disponível"}
                                </td>
                                <td>{number(gaps.length)}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                    <p className="caption">
                      ¹ Média das diferenças entre saídas consecutivas,
                      calculadas separadamente por sentido. Inclui todos os
                      períodos publicados; não mede regularidade observada.
                    </p>
                  </Panel>
                  <Panel title="Fórmulas e requisitos">
                    {data.catalogue.methodologies.map((m) => (
                      <Method key={m.id} {...m} />
                    ))}
                  </Panel>
                </>
              )}
              {page === "territorio" && (
                <>
                  <div className="notice">
                    <Globe2 size={18} />
                    <span>
                      Proximidade espacial não comprova atendimento. A cobertura
                      depende de um cadastro de paradas atualizado e da oferta
                      operacional.
                    </span>
                  </div>
                  <div className="metrics">
                    <Card
                      title="Bairros oficiais"
                      value={number(data.territory.neighborhoods.length)}
                      description="GeoCanoas · polígonos locais"
                      icon={MapPin}
                    />
                    <Card
                      title="Setores censitários"
                      value={number(data.territory.sectors)}
                      description="IBGE · Censo Demográfico 2022"
                      icon={Globe2}
                    />
                    <Card
                      title="Paradas georreferenciadas"
                      value={
                        data.stops.features.length
                          ? number(data.stops.features.length)
                          : "Não disponível"
                      }
                      description="Cadastro de referência; não inventário oficial"
                      icon={Navigation}
                    />
                    <Card
                      title="População coberta"
                      value="Não disponível"
                      description="Não inferida a partir da área"
                      icon={Target}
                    />
                  </div>
                  <MapBox data={data} territorial />
                  <Panel
                    title="Leitura por bairro"
                    subtitle="Área calculada em SIRGAS 2000 / UTM 22S (EPSG:31982)"
                  >
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Bairro</th>
                            <th>População 2022²</th>
                            <th>Área (km²)</th>
                            <th>Paradas da base</th>
                            <th>Paradas/km²</th>
                            <th>Área até 300 m³</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.territory.neighborhoods.map((n) => (
                            <tr key={n.name}>
                              <td>{n.name}</td>
                              <td>{number(n.population)}</td>
                              <td>{number(n.area_km2, 2)}</td>
                              <td>{number(n.stops)}</td>
                              <td>{number(n.stops_per_km2, 2)}</td>
                              <td>
                                {n.covered_area_pct == null
                                  ? "Não disponível"
                                  : number(n.covered_area_pct, 1) + "%"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <p className="caption">
                      ² Atributo do arquivo de bairros de referência. Não
                      recalculado por distribuição de área. ³ Buffer euclidiano,
                      não percurso a pé nem população atendida.
                    </p>
                  </Panel>
                  <Panel title="Limitações da análise">
                    {data.territory.limitations.map((l) => (
                      <p key={l} className="limitation">
                        <TriangleAlert size={15} />
                        {l}
                      </p>
                    ))}
                  </Panel>
                </>
              )}
              {page === "relatorios" && (
                <Reports
                  data={data}
                  date={date}
                  routeId={routeId}
                  setRouteId={setRouteId}
                />
              )}
              {page === "dados" && (
                <>
                  <Panel
                    title="Catálogo de fontes"
                    subtitle={
                      "Última consolidação: " +
                      brDate(data.catalogue.generated_at, true)
                    }
                  >
                    <div className="integration-grid">
                      {data.catalogue.integrations.map((s) => (
                        <article key={s.id} className="integration">
                          <div>
                            <Database size={20} />
                            <span className={"badge " + s.status}>
                              {statusLabel[s.status]}
                            </span>
                          </div>
                          <h3>{s.name}</h3>
                          <p>{s.description}</p>
                          <ul>
                            {s.features.map((f) => (
                              <li key={f}>{f}</li>
                            ))}
                          </ul>
                          <small>
                            Verificação: {brDate(s.checked_at, true)}
                          </small>
                          <a href={s.url} target="_blank" rel="noreferrer">
                            Consultar fonte
                            <ArrowUpRight size={14} />
                          </a>
                        </article>
                      ))}
                    </div>
                  </Panel>
                  <Panel title="Proveniência e atualização">
                    <p>
                      Datas são exibidas em America/Sao_Paulo. Arquivos e
                      registros preservam origem, hora de obtenção e hash
                      SHA-256. Os horários consultados correspondem apenas às
                      datas fornecidas pela operadora.
                    </p>
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Data de serviço</th>
                            <th>Linhas</th>
                            <th>Coleta de horários</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.network.source_dates.map((d) => (
                            <tr key={d.date}>
                              <td>{brDate(d.date)}</td>
                              <td>{d.routes}</td>
                              <td>
                                {d.complete
                                  ? "Completa para o cadastro recebido"
                                  : d.failed_routes.length +
                                    " linhas com falha"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {data.network.errors.length > 0 && (
                      <details>
                        <summary>
                          {data.network.errors.length} falhas ou avisos de
                          coleta
                        </summary>
                        <pre>
                          {JSON.stringify(data.network.errors, null, 2)}
                        </pre>
                      </details>
                    )}
                  </Panel>
                  <Panel title="Documentação técnica">
                    <div className="doc-links">
                      {[
                        [
                          "ENGENHARIA-REVERSA.md",
                          "Engenharia reversa e hipóteses",
                        ],
                        ["ENDPOINTS.md", "Contratos dos endpoints"],
                        ["MODELO-DADOS.md", "Modelo e histórico"],
                        ["METODOLOGIA.md", "Indicadores e auditoria"],
                        ["OPERACAO.md", "Infraestrutura e recuperação"],
                        ["HOMOLOGACAO.md", "Relatório de testes e limitações"],
                      ].map(([file, title]) => (
                        <a
                          key={file}
                          href={github + "/blob/main/docs/" + file}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <FileText size={19} />
                          {title}
                          <ArrowUpRight size={14} />
                        </a>
                      ))}
                    </div>
                  </Panel>
                </>
              )}
              <footer className="footer">
                <span>
                  <span className="footer-brand">GeoCanoas</span>Transporte
                  coletivo municipal
                </span>
                <a href="#dados">
                  Fontes, qualidade e metodologia <ArrowUpRight size={13} />
                </a>
                <small>Informação programada ≠ operação observada</small>
              </footer>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
function Reports({
  data,
  date,
  routeId,
  setRouteId,
}: {
  data: AppData;
  date: string;
  routeId: string;
  setRouteId: (id: string) => void;
}) {
  const [all, setAll] = useState(true),
    [direction, setDirection] = useState(""),
    [start, setStart] = useState(0),
    [end, setEnd] = useState(48);
  const list = filterDepartures(
    data.network.departures,
    all ? "" : routeId,
    date,
    direction,
    start * 60,
    end * 60,
  );
  const dirs = [
    ...new Set(
      data.network.departures
        .filter((d) => d.date === date && (all || d.route_id === routeId))
        .map((d) => d.direction),
    ),
  ];
  useEffect(() => {
    setDirection("");
  }, [date, all, routeId]);
  const rows = list.map((d) => ({
    linha: d.route_id,
    data: d.date,
    sentido: d.direction,
    horario: d.time,
    minuto_servico: d.service_minute,
    origem: d.url,
    obtido_em: d.fetched_at,
  }));
  return (
    <>
      <Panel
        title="Relatório de programação"
        subtitle="Selecione linha, sentido e intervalo de serviço"
      >
        <div className="report-filters">
          <label>
            Linha
            <select
              aria-label="Linha do relatório"
              value={all ? "" : routeId}
              onChange={(e) => {
                setAll(!e.target.value);
                if (e.target.value) setRouteId(e.target.value);
              }}
            >
              <option value="">Todas as linhas</option>
              {data.network.routes.map((r) => (
                <option value={r.id} key={r.id}>
                  {r.code} · {r.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Sentido
            <select
              aria-label="Sentido do relatório"
              value={direction}
              onChange={(e) => setDirection(e.target.value)}
            >
              <option value="">Todos</option>
              {dirs.map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          </label>
          <label>
            A partir de (hora de serviço)
            <input
              type="number"
              min="0"
              max="47"
              value={start}
              onChange={(e) => setStart(Number(e.target.value))}
            />
          </label>
          <label>
            Até (exclusivo)
            <input
              type="number"
              min="1"
              max="48"
              value={end}
              onChange={(e) => setEnd(Number(e.target.value))}
            />
          </label>
        </div>
        {start >= end && (
          <p role="alert" className="error">
            O início precisa ser anterior ao fim.
          </p>
        )}
        <p>
          <strong>{number(list.length)}</strong> saídas programadas em{" "}
          {brDate(date)}. Madrugada seguinte usa horas de serviço 24 a 47.
        </p>
        <div className="export-actions">
          <button
            className="primary"
            disabled={!list.length || start >= end}
            onClick={() =>
              download(
                "programacao-canoas-" + date + ".csv",
                csv(rows),
                "text/csv",
              )
            }
          >
            <ArrowDownToLine size={16} />
            Baixar CSV
          </button>
          <button
            disabled={!list.length || start >= end}
            onClick={() =>
              download(
                "programacao-canoas-" + date + ".json",
                JSON.stringify(
                  {
                    generated_at: data.network.generated_at,
                    filters: {
                      date,
                      route: all ? null : routeId,
                      direction,
                      start,
                      end,
                    },
                    count: list.length,
                    data: rows,
                  },
                  null,
                  2,
                ),
              )
            }
          >
            Baixar JSON
          </button>
          <button onClick={() => window.print()}>
            <FileText size={16} />
            Imprimir / PDF
          </button>
        </div>
        <div className="print-heading">
          <h2>GeoCanoas · Relatório de programação</h2>
          <p>
            Data: {brDate(date)} · Linha: {all ? "Todas" : routeId} · Sentido:{" "}
            {direction || "Todos"} · Horas de serviço: {start}–{end} · Gerado a
            partir da coleta: {brDate(data.network.generated_at, true)}
          </p>
        </div>
        <div className="table-scroll report-table">
          <table>
            <thead>
              <tr>
                <th>Linha</th>
                <th>Sentido</th>
                <th>Saída</th>
                <th>Data de serviço</th>
                <th>Obtido em</th>
              </tr>
            </thead>
            <tbody>
              {list.map((d, i) => (
                <tr key={i}>
                  <td>{d.route_id}</td>
                  <td>{d.direction}</td>
                  <td>
                    {d.time}
                    {d.service_minute >= 1440 ? " (+1)" : ""}
                  </td>
                  <td>{brDate(d.date)}</td>
                  <td>{brDate(d.fetched_at, true)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="caption">
          Fonte: {data.network.source_url}. Programação publicada não comprova
          viagem realizada. Todos os registros do filtro são incluídos na
          impressão.
        </p>
      </Panel>
      <Panel title="Bases cartográficas abertas">
        <div className="export-actions">
          {[
            ["bairros-oficiais.geojson", "Bairros oficiais"],
            ["censo2022-setores.geojson", "Setores 2022"],
            ["stops.geojson", "Pontos disponíveis"],
          ].map(([file, title]) => (
            <a
              className="download-link"
              key={file}
              download
              href={base + "data/" + file}
            >
              <ArrowDownToLine size={16} />
              {title} · GeoJSON
            </a>
          ))}
        </div>
        <p className="caption">
          Registros de fiscalização restritos são consultados e exportados
          somente pelo backend autenticado.
        </p>
      </Panel>
    </>
  );
}
export default App;
