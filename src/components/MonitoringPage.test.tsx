import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import MonitoringPage from "./MonitoringPage";
import type { AppData, Vehicle } from "../types";

afterEach(cleanup);
const observed="2026-10-31T15:00:00Z";
const example: Vehicle = {
  source_id:"SYNTHETIC",
  vehicle_id:"SYNTHETIC-101",
  route_id:"05000",
  source_itinerary_id:"2457",
  route_relation:"reference_not_homologated",
  longitude:-51.2, latitude:-29.91,
  observed_at:observed, fetched_at:observed,
  source_observed_at:null,time_basis:"client_fetch",
  bearing:null, signal_status:"SG", stale_polls:2
};
const fixture={
  vehicles:{
    status:"reference",
    generated_at:observed,
    vehicles:[example],
    message:"Referência por consulta."
  }
} as AppData;

describe("MonitoramentoPage",()=>{
  it("identifica explicitamente a falta de timestamp GPS e SC/SG",()=>{
    render(<MonitoringPage data={fixture} live={[example]}
      clock={Date.parse(observed)+30_000} query="" setQuery={()=>{}}
      github="https://github.com/example/repo" />);
    expect(screen.getByRole("note").textContent).toMatch(/sem timestamp original de GPS/i);
    expect(screen.getByText("Sem GPS")).toBeTruthy();
    expect(screen.getByText("30 s")).toBeTruthy();
    expect(screen.getByText("SYNTHETIC-101")).toBeTruthy();
    expect(screen.getByText("05000")).toBeTruthy();
    expect(screen.getByText("Não disponível")).toBeTruthy();
  });

  it("mantém busca acessível por teclado",()=>{
    let q="";
    const onQuery=(value:string)=>{q=value;};
    render(<MonitoringPage data={fixture} live={[example]}
      clock={Date.parse(observed)} query="" setQuery={onQuery}
      github="https://github.com/example/repo" />);
    fireEvent.change(screen.getByRole("textbox",{name:"Buscar veículo"}),{
      target:{value:"101"}
    });
    expect(q).toBe("101");
  });
});
