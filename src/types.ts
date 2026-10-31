import type { FeatureCollection, Geometry } from "geojson";
export interface Provenance {
  url: string;
  fetched_at: string;
  sha256: string;
}
export interface Route extends Provenance {
  id: string;
  code: string;
  name: string;
  dates: string[];
  source_id: string;
  itinerary: {
    sequence: number;
    street: string;
    street_type: string | null;
    city: string;
  }[];
  itinerary_status: string;
  itinerary_provenance?: Provenance;
}
export interface Departure extends Provenance {
  route_id: string;
  date: string;
  direction: string;
  time: string;
  service_minute: number;
  sequence: number;
  accessibility_source: string | null;
  source_id: string;
}
export interface Network {
  schema_version: number;
  generated_at: string;
  source_id: string;
  source_url: string;
  source_dates: {
    date: string;
    routes: number;
    complete: boolean;
    failed_routes: string[];
  }[];
  routes: Route[];
  departures: Departure[];
  errors: {
    route_id?: string;
    date?: string;
    resource: string;
    error: string;
  }[];
  status: string;
  limitations: string[];
}
export interface Integration {
  id: string;
  name: string;
  status: "available" | "partial" | "pending" | "blocked";
  description: string;
  url: string;
  checked_at: string;
  features: string[];
}
export interface Catalogue {
  generated_at: string;
  integrations: Integration[];
  methodologies: {
    id: string;
    name: string;
    formula: string;
    unit: string;
    requirements: string;
    limitation: string;
  }[];
}
export interface Territory {
  generated_at: string;
  neighborhoods: {
    name: string;
    area_km2: number;
    population: number | null;
    stops: number | null;
    stops_per_km2: number | null;
    covered_area_pct: number | null;
    reference_route_count?: number;
    reference_route_km?: number | null;
  }[];
  stops_status: string;
  stops_source: string | null;
  sectors: number;
  limitations: string[];
}
export interface Vehicle {
  vehicle_id: string;
  route_id: string;
  longitude: number;
  latitude: number;
  observed_at: string;
  fetched_at: string;
  speed_kmh?: number | null;
  bearing?: number | null;
  source_id: string;
}
export interface Vehicles {
  status: string;
  generated_at: string | null;
  vehicles: Vehicle[];
  message: string;
}
export interface MapManifest {
  schema_version: number;
  file: string;
  sha256: string;
  bytes: number;
  bounds: [number, number, number, number];
  minzoom: number;
  maxzoom: number;
  tile_count: number;
  layers: Record<string, number>;
  route_geometry_count: number;
  route_catalogue_count: number;
  route_status: Record<string, { status: string; shape_count: number }>;
}
export interface StopInventory {
  schema_version: 1;
  generated_at: string;
  source_stop_ids: number;
  located_stop_ids: number;
  unlocated_stop_ids: number;
  localization_pct: number | null;
  source_lines_successful: number;
  catalogue_routes: number;
  status_counts: Record<string, number>;
  routes: {route_id:string;known_stop_ids:number;located_stop_ids:number;unlocated_stop_ids:number;localization_pct:number|null;source_url:string;source_sha256:string;fetched_at:string}[];
  stops: {stop_id:string;name:string;route_ids:string[];status:string}[];
  limitations: string[];
}
export interface AppData {
  stopInventory?: StopInventory;
  routeShapes?: FeatureCollection;
  mapManifest?: MapManifest;
  network: Network;
  catalogue: Catalogue;
  territory: Territory;
  neighborhoods: FeatureCollection;
  sectors: FeatureCollection;
  stops: FeatureCollection;
  boundary: FeatureCollection;
  vehicles: Vehicles;
}
export type GeoCollection = FeatureCollection<Geometry>;
