import { Col, Row, Segmented, Typography } from "antd";
import { useState } from "react";
import { TimestampTool } from "../components/tools/TimestampTool";
import { JsonFormatterTool } from "../components/tools/JsonFormatterTool";

const TOOL_ITEMS = [
  { label: "时间戳转换", value: "timestamp" },
  { label: "JSON 格式化", value: "json" },
];

export function ToolsPage() {
  const [activeTool, setActiveTool] = useState<string>("timestamp");

  return (
    <div className="tools-page">
      <div className="tools-page-header">
        <Typography.Text className="workbench-intro-eyebrow">Tools</Typography.Text>
        <Typography.Title level={4} style={{ margin: "8px 0 10px" }}>
          测试工具集
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ margin: 0, fontSize: 14 }}>
          常用开发调试工具，提升日常工作效率。
        </Typography.Paragraph>
      </div>

      <div className="tools-nav-bar">
        <Segmented
          value={activeTool}
          onChange={(value) => setActiveTool(value as string)}
          options={TOOL_ITEMS}
          block
        />
      </div>

      <Row gutter={[24, 24]} className="tools-layout">
        <Col xs={24}>
          <div className="tool-card-wrapper">
            {activeTool === "timestamp" && <TimestampTool />}
            {activeTool === "json" && <JsonFormatterTool />}
          </div>
        </Col>
      </Row>
    </div>
  );
}