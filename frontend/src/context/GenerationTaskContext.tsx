import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useLocation } from "react-router-dom";

import {
  cancelGenerationTask,
  connectTaskWebSocket,
  disconnectTaskWebSocket,
  getStoredGenerationTaskId,
  getTaskStatus,
  setStoredGenerationTaskId,
  type GenerateResult,
  type TaskStatusPayload,
} from "../services/api";

interface GenerationTaskContextValue {
  taskId: string | null;
  taskStatus: TaskStatusPayload | null;
  /** Latest succeeded result from async pipeline */
  result: GenerateResult | null;
  pollError: string | null;
  isRunning: boolean;
  startTask: (id: string) => void;
  stopPolling: () => void;
  cancelActiveTask: () => Promise<void>;
  clearResult: () => void;
}

const GenerationTaskContext = createContext<GenerationTaskContextValue | null>(null);

const POLL_MS = 3000;

export function GenerationTaskProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [taskId, setTaskId] = useState<string | null>(() => getStoredGenerationTaskId());
  const [taskStatus, setTaskStatus] = useState<TaskStatusPayload | null>(null);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const notifiedTaskRef = useRef<string | null>(null);

  const stopPolling = useCallback(() => {
    setTaskId(null);
    setStoredGenerationTaskId(null);
    setTaskStatus(null);
  }, []);

  const startTask = useCallback((id: string) => {
    setStoredGenerationTaskId(id);
    setTaskId(id);
    setPollError(null);
    setTaskStatus(null);
    setResult(null);
  }, []);

  const clearResult = useCallback(() => {
    setResult(null);
  }, []);

  useEffect(() => {
    if (!taskId) return;

    let cancelled = false;
    let disconnectWs: (() => void) | null = null;

    const applyStatus = (s: TaskStatusPayload) => {
      if (cancelled) return;
      setTaskStatus(s);
      setPollError(null);
      if (s.status === "succeeded" && s.result) {
        setResult(s.result);
        setStoredGenerationTaskId(null);
        setTaskId(null);
        setTaskStatus(s);
      }
      if (s.status === "failed" || s.status === "cancelled") {
        setStoredGenerationTaskId(null);
        setTaskId(null);
        setTaskStatus(s);
      }
    };

    const onWsError = (msg: string) => {
      if (cancelled) return;
      console.warn("[hpr-ws] task=%s error: %s", taskId, msg);
      setPollError(msg);
    };

    const onWsClose = () => {
      if (cancelled) return;
      // Fall back to HTTP polling if WebSocket fails
      if (disconnectWs) {
        disconnectWs();
        disconnectWs = null;
      }
      if (taskId && !cancelled) {
        startPolling();
      }
    };

    const startPolling = () => {
      const tick = async () => {
        try {
          const s = await getTaskStatus(taskId);
          if (cancelled) return;
          applyStatus(s);
        } catch (e) {
          if (!cancelled) {
            const msg = e instanceof Error ? e.message : "轮询任务状态失败。";
            console.error("[hpr-api] generation-task/poll", { taskId, message: msg, error: e });
            setPollError(msg);
          }
        }
      };
      void tick();
      const interval = window.setInterval(() => void tick(), POLL_MS);
      return () => {
        window.clearInterval(interval);
      };
    };

    // Try WebSocket first, fall back to polling
    if (
      typeof WebSocket !== "undefined" &&
      window.location.protocol !== "file:"
    ) {
      disconnectWs = connectTaskWebSocket(
        taskId,
        applyStatus,
        onWsError,
        onWsClose
      );
    } else {
      startPolling();
    }

    return () => {
      cancelled = true;
      if (disconnectWs) disconnectWs();
    };
  }, [taskId]);

  useEffect(() => {
    if (taskStatus?.status !== "succeeded" || !taskStatus.taskId) return;
    if (notifiedTaskRef.current === taskStatus.taskId) return;
    notifiedTaskRef.current = taskStatus.taskId;
    if (location.pathname !== "/" && typeof Notification !== "undefined" && Notification.permission === "granted") {
      new Notification("测试用例生成完成", {
        body: "返回「用例生成」页面即可查看结果。",
      });
    }
  }, [taskStatus, location.pathname]);

  const cancelActiveTask = useCallback(async () => {
    if (!taskId) return;
    await cancelGenerationTask(taskId);
  }, [taskId]);

  const value = useMemo<GenerationTaskContextValue>(
    () => ({
      taskId,
      taskStatus,
      result,
      pollError,
      isRunning: Boolean(
        taskId && (taskStatus === null || taskStatus.status === "running")
      ),
      startTask,
      stopPolling,
      cancelActiveTask,
      clearResult,
    }),
    [taskId, taskStatus, result, pollError, startTask, stopPolling, cancelActiveTask, clearResult]
  );

  return <GenerationTaskContext.Provider value={value}>{children}</GenerationTaskContext.Provider>;
}

export function useGenerationTask(): GenerationTaskContextValue {
  const ctx = useContext(GenerationTaskContext);
  if (!ctx) {
    throw new Error("useGenerationTask must be used within GenerationTaskProvider");
  }
  return ctx;
}
