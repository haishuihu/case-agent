import { Card, Space, Tabs, Typography } from "antd";
import { TimestampTool } from "../components/tools/TimestampTool";
import { JsonFormatterTool } from "../components/tools/JsonFormatterTool";

const TAB_ITEMS = [
  {
    key: "timestamp",
    label: "时间戳转换",
    children: <TimestampTool />,
  },
  {
    key: "json",
    label: "JSON 格式化",
    children: <JsonFormatterTool />,
  },
];

export function ToolsPage() {
  return (
    <div className="tools-page">
      <div className="tools-page-header">
        <Space direction="vertical" size={4}>
          <Typography.Text className="workbench-intro-eyebrow">Tools</Typography.Text>
          <Typography.Title level={4} style={{ margin: 0 }}>
            测试工具集
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
            常用开发调试工具，提升日常工作效率。
          </Typography.Paragraph>
        </Space>
      </div>

      <Card bodyStyle={{ padding: 0 }}>
        <Tabs
          defaultActiveKey="timestamp"
          items={TAB_ITEMS}
          style={{ padding: "0 24px" }}
          tabBarStyle={{ marginBottom: 0 }}
        />
      </Card>
    </div>
  );
}
