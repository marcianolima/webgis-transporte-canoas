import {afterEach,describe,it,expect,vi} from "vitest";
import {cleanup,fireEvent,render,screen} from "@testing-library/react";
import StopCoverage from "./StopCoverage";
import type {AppData} from "../types";
afterEach(cleanup);
const data={network:{routes:[{id:"1",code:"1",name:"SYNTHETIC"}]},stopInventory:{schema_version:1,generated_at:"2026-10-31T10:00:00+00:00",source_stop_ids:3,located_stop_ids:1,unlocated_stop_ids:2,localization_pct:33.33,source_lines_successful:1,catalogue_routes:2,status_counts:{located:1,pending:2},routes:[{route_id:"1",known_stop_ids:3,located_stop_ids:1,unlocated_stop_ids:2,localization_pct:33.33}],stops:[{stop_id:"11",route_ids:["1"],status:"located"},{stop_id:"12",route_ids:["1"],status:"pending"},{stop_id:"13",route_ids:["1"],status:"pending"}],limitations:[]}} as unknown as AppData;
describe("completude do cadastro consultado",()=>{
 it("exibe o recorte sem atribuir cobertura municipal e permite escolher a linha",()=>{
  const select=vi.fn();render(<StopCoverage data={data} onSelectLine={select}/>);
  expect(screen.getByText("33,3%",{selector:"strong"})).toBeTruthy();
  expect(screen.getByText(/não mede cobertura do município/)).toBeTruthy();
  fireEvent.click(screen.getByText("Conferir completude por linha"));
  fireEvent.click(screen.getByRole("button",{name:"Consultar paradas da linha 1"}));expect(select).toHaveBeenCalledWith("1");
 });
 it("não inventa completude quando o inventário não está disponível",()=>{
  const {container}=render(<StopCoverage data={{...data,stopInventory:undefined}}/>);expect(container.textContent).toBe("");
 });
});
