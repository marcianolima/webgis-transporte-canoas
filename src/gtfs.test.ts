import { describe, expect, it } from "vitest";
import { isServiceActive, parseCsv, parseGtfs, serviceFirstTime, serviceLastTime } from "./gtfs";
const files = {
  "routes.txt": "route_id,route_short_name,route_long_name,route_type,network_id\n10,05001,\"CENTRO, BAIRRO\",3,5001\n",
  "trips.txt": "route_id,service_id,trip_id,shape_id,direction_id\n10,1,t1,s1,0\n",
  "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\np1,\"Praça, Centro\",-29.92,-51.16\np2,Terminal,-29.93,-51.17\n",
  "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nt1,06:00:00,06:00:00,p1,1\nt1,,,p2,2\n",
  "shapes.txt": "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence,shape_dist_traveled\ns1,-29.93,-51.17,2,100\ns1,-29.92,-51.16,1,0\n",
  "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n1,1,1,1,1,1,0,0,20261106,20270206\n"
};
describe("GTFS estático",()=>{
  it("lê CSV escapado e BOM, preservando vírgulas",()=>{
    expect(parseCsv("\uFEFFa,b\r\n1,\"x,y\"\r\n")[0]).toEqual({a:"1",b:"x,y"});
    expect(parseCsv("a,b\na,\"b\"\"c\"\n")[0].b).toBe('b"c');
  });
  it("indexa shapes e stops por sequência sem estimar horários",()=>{
    const feed=parseGtfs(files);
    expect(feed.routes[0].route_long_name).toBe("CENTRO, BAIRRO");
    expect(feed.shapes.get("s1")).toEqual([[-29.92,-51.16],[-29.93,-51.17]]);
    expect(feed.timesByTrip.get("t1")?.length).toBe(2);
    expect(serviceFirstTime(feed,feed.trips[0])).toBe("06:00:00");
    expect(serviceLastTime(feed,feed.trips[0])).toBe("06:00:00");
    expect(feed.timesByTrip.get("t1")?.[1].departure_time).toBe("");
  });
  it("distingue vigência do calendário e não inventa serviço",()=>{
    const feed=parseGtfs(files);
    const c=feed.calendars[0];
    expect(isServiceActive(c,new Date("2026-11-16T12:00:00"))).toBe(true);
    expect(isServiceActive(c,new Date("2026-11-15T12:00:00"))).toBe(false);
    expect(isServiceActive(c,new Date("2027-03-01T12:00:00"))).toBe(false);
  });
  it("rejeita ausência de arquivo e referências inválidas",()=>{
    const missing={...files};delete (missing as Partial<typeof files>)["shapes.txt"];
    expect(()=>parseGtfs(missing)).toThrow(/shapes.txt/);
    expect(()=>parseGtfs({...files,"trips.txt":files["trips.txt"].replace("10,1,t1","X,1,t1")})).toThrow(/sem linha/);
    expect(()=>parseGtfs({...files,"stop_times.txt":files["stop_times.txt"].replace(",p2,2",",p999,2")})).toThrow(/stop_id ausente/);
  });
});
