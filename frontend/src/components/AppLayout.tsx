import { useEffect, useRef, useState } from "react";
import { Button, Layout, Menu, Space, Typography } from "antd";
import {
  ExperimentOutlined,
  BookOutlined,
  ToolOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  SendOutlined,
  ThunderboltOutlined,
  SafetyCertificateOutlined,
  BugOutlined,
  SettingOutlined,
  RocketOutlined,
} from "@ant-design/icons";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { useGenerationTask } from "../context/GenerationTaskContext";

const NAV_ITEMS = [
  { key: "/", label: "用例生成", icon: <ExperimentOutlined /> },
  { key: "/quick", label: "快速生成", icon: <ThunderboltOutlined /> },
  { key: "/submissions", label: "提测申请", icon: <SendOutlined /> },
  { key: "/reviews", label: "用例评审", icon: <SafetyCertificateOutlined /> },
  { key: "/defects", label: "缺陷管理", icon: <BugOutlined /> },
  { key: "/knowledge", label: "知识库", icon: <BookOutlined /> },
  { key: "/auto-test", label: "自动化测试", icon: <RocketOutlined /> },
  { key: "/tools", label: "测试工具", icon: <ToolOutlined /> },
];

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isRunning, taskStatus } = useGenerationTask();
  const [showDone, setShowDone] = useState(false);
  const prevIdRef = useRef<string | null>(null);

  const activeKey = location.pathname.startsWith("/submissions")
    ? "/submissions"
    : location.pathname.startsWith("/quick")
    ? "/quick"
    : location.pathname.startsWith("/reviews")
    ? "/reviews"
    : location.pathname.startsWith("/defects")
    ? "/defects"
    : location.pathname.startsWith("/knowledge")
    ? "/knowledge"
    : location.pathname.startsWith("/auto-test")
    ? "/auto-test"
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
      <LoadingOutlined style={{ fontSize: 14, color: "var(--text-secondary)" }} />
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
    </Space>
  ) : null;

  return (
    <Layout className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <div className="app-header-brand">
            <h2>
              智能测试助手
            </h2>
          </div>
          <Space size="middle" className="app-header-right">
            {taskHint}
            <Button
              type="text"
              icon={<SettingOutlined style={{ fontSize: 18 }} />}
              onClick={() => navigate("/settings")}
              style={{ color: "var(--text-secondary)" }}
              title="模型配置"
            />
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
