import "@ant-design/v5-patch-for-react-19";
import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";

import App from "./App";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: "#1A1A1A",
          borderRadius: 6,
          fontFamily:
            '"Inter", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
          colorBorder: "#E5E7EB",
          colorBgContainer: "#FFFFFF",
          colorBgLayout: "#F8F9FA",
          colorText: "#111827",
          colorTextSecondary: "#6B7280",
        },
        algorithm: theme.defaultAlgorithm,
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>
);
