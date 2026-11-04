import { app, BrowserWindow, ipcMain, dialog, session, globalShortcut, shell } from "electron";
import path from "path";
import fs from "fs";
import * as backendService from "./backend-service.js"; // 导入我们创建的服务

// --- 日志记录 ---
const logPath = path.join(app.getPath('userData'), 'main.log');
const logStream = fs.createWriteStream(logPath, { flags: 'a' });
const log = (message) => {
  const timestamp = new Date().toISOString();
  logStream.write(`[${timestamp}] ${message}\n`);
  console.log(message); // 同时在控制台输出
};

log('--- Main process started ---');
import { fileURLToPath } from "url"; // 导入 fileURLToPath
import { dirname, join } from "path"; // 导入 dirname 和 join
import { spawn } from "child_process";
import WebSocket from "ws";
import dotenv from "dotenv";
// --- ESM-safe __dirname replacement ---
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// --- 加载环境变量 (必须保留) ---
const isProd = process.env.NODE_ENV === "production";
const envFile = isProd ? "../../.env.production" : "../../.env.development";
dotenv.config({ path: path.resolve(__dirname, envFile) });

// --- 全局变量 ---
let win;
let pythonV1Process = null; // 用于持有 v1.py 子进程的引用

const preloadPath = path.join(__dirname, '../preload/preload.js')

// --- 核心路径定义：动态计算所有必要的路径 ---
// 生产环境: 指向打包后 app.asar 同级的 'python-dist' 文件夹
// 开发环境: 指向项目根目录下的 'python-dist' 文件夹
const pythonDistPath = !app.isPackaged
  ? path.join(__dirname, "..", "..", "python-dist")
  : path.join(process.resourcesPath, "python-dist");

// 根据打包状态，正确指向可移植的 Python 解释器
const pythonExecutable = path.join(pythonDistPath, "python.exe");
// 创建窗口的函数
const createWindow = () => {
  win = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, "..", "preload", "preload.js"),
      contextIsolation: true,
      nodeIntegration: false, // 出于安全考虑，保持为 false
      devTools: true,
    },
  });

  // --- 权限处理 ---
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === "media") {
      callback(true);
    } else {
      callback(false);
    }
  });

  // --- 加载页面 ---
  if (!app.isPackaged) {
    win.loadURL("http://localhost:5173");
    if (win.webContents) win.webContents.openDevTools();
  } else {
    win.loadFile(path.join(__dirname, "..", "index.html"));
  }
    // 【日志记录】为生产环境添加打开开发者工具的快捷键
  log('Registering DevTools shortcut listener.');
    // 【修正】使用全局快捷键注册开发者工具
  
};

// 当 Electron 完成初始化时调用
app.whenReady().then(() => {
  createWindow();

  // --- 应用启动时，自动启动后端服务 ---
  log("Application is ready, attempting to start backend services automatically...");
  backendService.start()
    .then(() => {
      log("All backend services reported ready.");
    })
    .catch(error => {
      log(`Failed to start backend services automatically: ${error.message}`);
      dialog.showErrorBox("核心服务启动失败", `应用无法启动一个或多个后端服务，部分功能可能无法使用.\n\n错误: ${error.message}`);
    });

  // 【修正】在应用就绪后，注册全局快捷键
  globalShortcut.register('CommandOrControl+Shift+I', () => {
    const focusedWindow = BrowserWindow.getFocusedWindow();
    if (focusedWindow) {
      focusedWindow.webContents.toggleDevTools();
    }
  });

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });

  // 在应用就绪后，立即启动灯光和电机控制服务
  log("Starting hardware control script: v1.py");
  pythonV1Process = runPythonScript("v1.py"); // 启动并保存子进程引用

  tryConnect(); // 启动时尝试连接 WebSocket
});

app.on('will-quit', () => {
  // 注销所有快捷键
  globalShortcut.unregisterAll();

  // --- 关键：终止 Python 子进程 ---
  if (pythonV1Process) {
    log('Terminating the main Python script (v1.py)...');
    pythonV1Process.kill();
    pythonV1Process = null;
  }
  
  // --- 自动停止后端服务 ---
  log("Application is quitting, stopping all backend services...");
  backendService.stop();
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

// 在应用退出前，清除所有会话数据
app.on('before-quit', () => {
  if (session.defaultSession) {
    session.defaultSession.clearStorageData();
    console.log('所有会话数据已在退出时清除。');
  }
});
// 打开文件选择器


ipcMain.on("switch-camera", (event, cameraId) => {
  let scriptName;
  switch (cameraId) {
    case "camera1":
      scriptName = "open_small.py";
      break;
    case "camera2":
      scriptName = "open_mid.py";
      break;
    case "camera3":
      scriptName = "open_big.py";
      break;
    default:
      console.error("未知的摄像头 ID");
      return;
  }
  runPythonScript(scriptName);
  // tryConnect();
});
ipcMain.on("stop-camera", (event) => {
  runPythonScript("Close_WS.py");
  console.log("====================================");
  console.log("关闭ws");
  console.log("====================================");
});

// 保存图片
const userDataPath = app.getPath('userData');
const imgDir = path.join(userDataPath, "img"); // 目标文件夹
// 确保 public/img 目录存在
if (!fs.existsSync(imgDir)) {
  fs.mkdirSync(imgDir, { recursive: true });
}

// 处理保存图片
ipcMain.handle("saveImage", async (_, base64Data, fileName) => {
  try {
    const imagePath = path.join(imgDir, fileName);
    console.log("即将保存图片到:", imagePath);
    await fs.promises.writeFile(imagePath, base64Data, "base64");
    console.log("图片保存成功:", imagePath);
    return imagePath;
  } catch (err) {
    console.error("图片保存失败:", err);
    return null;
  }
});

// 处理图像
// --- 图像处理/模型预测 (通过HTTP请求) ---
ipcMain.on("process-image", async (event, imagePath) => {
  console.log("接收到的文件路径:", imagePath);
  try {
    // 读取文件内容作为 Blob 或 Buffer
    const fileBuffer = fs.readFileSync(imagePath);
    const blob = new Blob([fileBuffer], { type: 'image/png' }); // 假设是 PNG，根据实际文件类型调整

    const formData = new FormData();
    formData.append('files', blob, path.basename(imagePath)); // 'files' 是后端期望的字段名

    // 发送 HTTP 请求到后端进行预测
    // 预测接口为 http://localhost:5000/predict/batch
    const response = await fetch("http://localhost:5000/predict/batch", {
      method: "POST",
      body: formData, // 直接传递 FormData 对象，fetch 会自动设置 Content-Type
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    // 后端 /predict/batch 接口返回的 `result.data` 是一个数组，其中包含每个文件的预测结果。
    // 由于此 IPC 每次只处理一个 `imagePath`，因此 `result.data` 数组将始终只包含一个元素。
    // 注意：`result` 现在是一个 JavaScript 对象，渲染进程接收后无需再进行 `JSON.parse()`。
    // `base64ImageForDisplay` 用于将原始输入图片转换为 Base64 格式，与预测结果一同返回给渲染进程用于显示。
    const base64ImageForDisplay = fs.readFileSync(imagePath).toString("base64");
    event.reply("predict-result", result, `data:image/png;base64,${base64ImageForDisplay}`);
  } catch (error) {
    console.error("预测失败:", error);
    let errorMessage = "未知错误";
    if (error instanceof TypeError) { // 例如，网络连接错误
      errorMessage = `网络连接错误: ${error.message}`;
    } else if (error instanceof Error && error.message.startsWith("HTTP error!")) {
      // 尝试解析后端返回的错误信息
      try {
        // response 变量在 try 块中定义，这里需要确保它在 catch 块中可用
        // 假设 response 在 try 块中成功赋值
        const errorResponse = await response.json(); // 尝试再次解析错误响应体
        errorMessage = errorResponse.message || `HTTP错误: ${response.status}`;
      } catch (jsonError) {
        errorMessage = `HTTP错误: ${response.status} (无法解析错误详情)`;
      }
    } else {
      errorMessage = `预测失败: ${error.message || error}`;
    }
    event.reply("predict-result", { code: 500, message: errorMessage }, ""); // 返回一个结构化的错误对象
  }
});



// --- 核心辅助函数：用于执行所有硬件脚本 ---
const runPythonScript = (scriptName) => {
  const scriptPath = path.join(pythonDistPath, scriptName);
  const options = { windowsHide: true };

  // 【日志记录】记录 spawn 的完整参数
  log(`Spawning Python script. Executable: ${pythonExecutable}, Script: ${scriptPath}, Options: ${JSON.stringify(options)}`);

  const python = spawn(pythonExecutable, [scriptPath], options);

  python.stdout.on("data", (data) => {
    log(`[Python STDOUT - ${scriptName}] ${data.toString()}`);
  });

  python.stderr.on("data", (data) => {
    log(`[Python STDERR - ${scriptName}] ${data.toString()}`);
  });

  python.on("close", (code) => {
    log(`[Python Process - ${scriptName}] exited with code ${code}`);
  });

  return python; // 返回子进程对象
};

// --- WebSocket 连接 (用于视频流) ---
const tryConnect = () => {
  let retries = 0;
  const maxRetries = 5;
  let count = 0;

  const connect = () => {
    const ws = new WebSocket("ws://127.0.0.1:8765");

    ws.onopen = () => {
      console.log("WebSocket 连接成功");
      retries = 0; // 重置重试计数器
    };

    ws.onmessage = (event) => {
      if (ws.readyState !== WebSocket.OPEN) {
        console.log("WebSocket 已关闭，无法接收消息");
        return;
      }
      setImmediate(() => {
        // 假设 event.data 是图像数据
        win.webContents.send("camera-data", event.data);
      });
      if (count % 100 === 0) {
        ws.send("ping"); // 发送心跳包
      }
      count++;
    };

    ws.onclose = (code, reason) => {
      console.log(`连接关闭: ${code} ${reason}`);
      if (retries < maxRetries) {
        retries++;
        console.log(`第 ${retries} 次重试...`);
        setTimeout(connect, 3000);
      } else {
        console.error("超过最大重试次数，放弃连接");
      }
    };
    ws.onerror = (error) => {
      console.error(`连接失败: ${error.message}`);
    };
  };
  connect();
};

// --- 新的IPC通道，用于获取后端就绪状态 ---
ipcMain.handle('get-backend-readiness', () => {
  try {
    const readiness = backendService.getReadinessState();
    return { success: true, readiness: readiness };
  } catch (error) {
    log(`IPC 'get-backend-readiness' failed: ${error.message}`);
    return { success: false, error: error.message };
  }
});

// 新增：处理在文件浏览器中显示文件的请求
ipcMain.on('open-in-explorer', (event, relativePath) => {
  // 基础路径定义
  const devBasePath = process.env.TCM_IMAGE_BASE_PATH || path.resolve(__dirname, "..", "..", "external", "tcm_app");
  const prodBasePath = app.isPackaged 
    ? path.join(path.dirname(app.getAppPath()), "..", "tcm_app", "_internal") 
    : ""; // 生产环境的asar包外路径

  const basePath = app.isPackaged ? prodBasePath : devBasePath;
  const absolutePath = path.join(basePath, relativePath);

  log(`Attempting to show item in folder: ${absolutePath}`);

  if (fs.existsSync(absolutePath)) {
    shell.showItemInFolder(absolutePath);
  } else {
    log(`File not found at: ${absolutePath}`);
    dialog.showErrorBox('文件未找到', `无法在以下路径找到文件：\n${absolutePath}`);
  }
});

// 新增：处理获取图片绝对路径的请求
ipcMain.handle('get-absolute-image-path', (event, relativePath) => {
  const devBasePath = process.env.TCM_IMAGE_BASE_PATH || path.resolve(__dirname, "..", "..", "external", "tcm_app");
  const prodBasePath = app.isPackaged 
    ? path.join(path.dirname(app.getAppPath()), "..", "tcm_app", "_internal") 
    : "";

  const basePath = app.isPackaged ? prodBasePath : devBasePath;
  return path.join(basePath, relativePath);
});
