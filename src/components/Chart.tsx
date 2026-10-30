import { useEffect, useRef } from "react";
import * as echarts from "echarts";
export default function Chart({
  labels,
  values,
  label = "Saídas programadas",
  horizontal = false,
}: {
  labels: string[];
  values: number[];
  label?: string;
  horizontal?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const category = {
      type: "category" as const,
      data: labels,
      axisLabel: {
        color: "#788b8d",
        fontSize: 11,
        overflow: "truncate" as const,
        width: 100,
      },
    };
    const value = {
      type: "value" as const,
      axisLabel: { color: "#788b8d" },
      splitLine: { lineStyle: { color: "#c5d1ce33" } },
    };
    chart.setOption({
      textStyle: { fontFamily: "system-ui" },
      grid: { left: horizontal ? 125 : 45, right: 20, top: 25, bottom: 35 },
      tooltip: { trigger: "axis", confine: true },
      xAxis: horizontal ? value : category,
      yAxis: horizontal ? category : value,
      series: [
        {
          name: label,
          type: "bar",
          data: values,
          itemStyle: {
            color: "#2b8a7b",
            borderRadius: horizontal ? [0, 5, 5, 0] : [4, 4, 0, 0],
          },
          barMaxWidth: 28,
        },
      ],
      aria: { enabled: true, description: label },
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [labels, values, label, horizontal]);
  return <div className="chart" ref={ref} role="img" aria-label={label} />;
}
