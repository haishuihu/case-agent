import { useEffect, useRef, useState } from "react";
import { Layout, Menu, Space, Typography } from "antd";
import {
  ExperimentOutlined,
  BookOutlined,
  ToolOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  FireOutlined,
} from "@ant-design/icons";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { useGenerationTask } from "../context/GenerationTaskContext";

const NAV_ITEMS = [
  { key: "/", label: "用例生成", icon: <ExperimentOutlined /> },
  { key: "/knowledge", label: "知识库", icon: <BookOutlined /> },
  { key: "/tools", label: "测试工具", icon: <ToolOutlined /> },
];

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isRunning, taskStatus } = useGenerationTask();
  const [showDone, setShowDone] = useState(false);
  const prevIdRef = useRef<string | null>(null);

  const activeKey = location.pathname.startsWith("/knowledge")
    ? "/knowledge"
    : location.pathname.startsWith("/tools")
    ? "/tools"
    : "/";

  useEffect(() => {
    const id = taskStatus?.taskId ?? null;
    const st = taskStatus?.status;
    if (st === "succeeded" && id && prevIdRef.current !== id) {
      prevIdRef.current = id;
      setShowDone(true);
      const t = window.setTimeout(() => setShowDone(false), 8000);
      return () => clearTimeout(t);
    }
    if (st === "running") {
      setShowDone(false);
    }
  }, [taskStatus?.taskId, taskStatus?.status]);

  const taskHint = isRunning ? (
    <Space
      className="header-task-indicator header-task-running"
      size="small"
      onClick={() => navigate("/")}
      style={{ cursor: "pointer" }}
    >
      <span className="header-task-dot" />
      <Typography.Text style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>生成中...</Typography.Text>
      <LoadingOutlined style={{ fontSize: 14, color: "var(--color-info)" }} />
    </Space>
  ) : showDone ? (
    <Space
      className="header-task-indicator header-task-done"
      size="small"
      onClick={() => navigate("/")}
      style={{ cursor: "pointer" }}
    >
      <CheckCircleOutlined style={{ color: "var(--color-success)", fontSize: 14 }} />
      <Typography.Text style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>生成完成</Typography.Text>
      <FireOutlined style={{ color: "var(--color-warning)", fontSize: 12 }} />
    </Space>
  ) : null;

  return (
    <Layout className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <div className="app-header-brand">
            <h2>
              <span className="brand-icon">
                <ExperimentOutlined />
              </span>
              智能测试助手
            </h2>
          </div>
          <Space size="large" className="app-header-right">
            {taskHint}
            <Menu
              mode="horizontal"
              selectedKeys={[activeKey]}
              items={NAV_ITEMS}
              onClick={({ key }) => navigate(key)}
              className="app-header-nav"
              triggerSubMenuAction="hover"
            />
          </Space>
        </div>
      </header>
      <Layout.Content className="app-content">
        <Outlet />
      </Layout.Content>
    </Layout>
  );
}
