import { useEffect, useRef } from "react";
import * as d3 from "d3";
import type { VisualizationData, ModuleNode, ModuleEdge } from "../../services/impact";

interface DependencyGraphProps {
  data: VisualizationData;
  width?: number;
  height?: number;
}

const RISK_COLORS: Record<string, string> = {
  high: "#ff4d4f",
  medium: "#faad14",
  low: "#52c41a",
};

const TYPE_COLORS: Record<string, string> = {
  direct: "#1890ff",
  indirect: "#722ed1",
  api: "#13c2c2",
};

interface D3Node extends d3.SimulationNodeDatum {
  id: string;
  name: string;
  moduleType: string;
  riskLevel: string;
  isDirect: boolean;
  changeFrequency: number;
  fx?: number | null;
  fy?: number | null;
}

interface D3Edge extends d3.SimulationLinkDatum<D3Node> {
  source: string | D3Node;
  target: string | D3Node;
  relationType: string;
  weight: number;
}

export function DependencyGraph({ data, width = 600, height = 400 }: DependencyGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!svgRef.current || !data.nodes.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const nodes: D3Node[] = data.nodes.map((n) => ({
      id: n.id,
      name: n.name,
      moduleType: n.moduleType,
      riskLevel: n.riskLevel,
      isDirect: n.isDirect,
      changeFrequency: n.changeFrequency,
      x: n.x ?? width / 2,
      y: n.y ?? height / 2,
    }));

    const edges: D3Edge[] = data.edges
      .filter((e) => e.source && e.target)
      .map((e) => ({
        source: e.source,
        target: e.target,
        relationType: e.relationType,
        weight: e.weight,
      }));

    // Filter out edges where source/target don't match any node id
    const nodeIds = new Set(nodes.map((n) => n.id));
    const validEdges = edges.filter(
      (e) =>
        nodeIds.has(typeof e.source === "string" ? e.source : e.source.id) &&
        nodeIds.has(typeof e.target === "string" ? e.target : e.target.id)
    );

    const margin = { top: 20, right: 20, bottom: 20, left: 20 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Create zoom layer
    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Zoom behavior
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 3])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoom);

    // Arrow marker for edges
    svg
      .append("defs")
      .append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 20)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#8c8c8c");

    // Force simulation
    const simulation = d3
      .forceSimulation<D3Node>(nodes)
      .force(
        "link",
        d3
          .forceLink<D3Node, D3Edge>(validEdges)
          .id((d) => d.id)
          .distance(100)
          .strength(0.5)
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(innerWidth / 2, innerHeight / 2))
      .force("collision", d3.forceCollide().radius(40));

    // Draw edges
    const link = g
      .append("g")
      .selectAll("line")
      .data(validEdges)
      .join("line")
      .attr("stroke", "#d9d9d9")
      .attr("stroke-width", (d) => Math.min(d.weight, 3))
      .attr("marker-end", "url(#arrowhead)");

    // Draw node groups
    const node = g
      .append("g")
      .selectAll<SVGGElement, D3Node>("g")
      .data(nodes)
      .join("g")
      .attr("cursor", "pointer")
      .call(
        d3
          .drag<SVGGElement, D3Node>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    // Node circles
    node
      .append("circle")
      .attr("r", (d) => (d.isDirect ? 18 : 14))
      .attr("fill", (d) => RISK_COLORS[d.riskLevel] ?? "#d9d9d9")
      .attr("fill-opacity", 0.85)
      .attr("stroke", (d) => (d.isDirect ? RISK_COLORS[d.riskLevel] ?? "#d9d9d9" : "transparent"))
      .attr("stroke-width", 2)
      .style("transition", "fill-opacity 0.2s");

    // Node labels
    node
      .append("text")
      .text((d) => {
        const parts = d.name.split("/");
        return parts[parts.length - 1];
      })
      .attr("text-anchor", "middle")
      .attr("dy", (d) => (d.isDirect ? 32 : 26))
      .attr("font-size", 11)
      .attr("font-weight", (d) => (d.isDirect ? "600" : "400"))
      .attr("fill", "#595959");

    // Hover tooltip
    node
      .append("title")
      .text(
        (d) =>
          `${d.name}\n类型: ${d.moduleType}\n风险: ${d.riskLevel}\n${d.isDirect ? "(直接变更)" : "(间接影响)"}`
      );

    // Simulation tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as D3Node).x ?? 0)
        .attr("y1", (d) => (d.source as D3Node).y ?? 0)
        .attr("x2", (d) => (d.target as D3Node).x ?? 0)
        .attr("y2", (d) => (d.target as D3Node).y ?? 0);

      node.attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    return () => {
      simulation.stop();
    };
  }, [data, width, height]);

  return (
    <div ref={containerRef} style={{ width, height, position: "relative" }}>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        style={{
          background: "#fafafa",
          border: "1px solid #f0f0f0",
          borderRadius: 8,
          display: "block",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 8,
          right: 8,
          fontSize: 11,
          color: "#8c8c8c",
          background: "rgba(255,255,255,0.8)",
          padding: "2px 6px",
          borderRadius: 4,
        }}
      >
        拖拽节点 · 滚轮缩放
      </div>
    </div>
  );
}
