const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("electron", {
  openFileDialog: () => {
    return ipcRenderer.invoke("openFileDialog");
  },
  processImage: (filePath) => {
    ipcRenderer.send("process-image", filePath);
  },
  onPredictResult: (callback) => {
    ipcRenderer.on("predict-result", (event, result, base64Image) => {
      callback(result, base64Image); // 渲染进程接收到结果并调用回调
    });
  },
  switchCamera: (cameraId) => ipcRenderer.send("switch-camera", cameraId),
  StopCamera: async() => {
    await ipcRenderer.send("stop-camera");
  },
  // receiveFrame: (callback) => {
  //   ipcRenderer.on("camera-data", (event, videoUrl) => {
  //     callback(videoUrl); // 将 videoUrl 传递给渲染进程中的回调函数
  //   });
  // },
  receiveFrame: (callback) => {
    ipcRenderer.on("camera-data", (event, data) => {
      // const arrayBuffer = new Uint8Array(data).buffer;
      callback(data);
    });
  },
  saveImage: (base64Data, fileName) =>
    ipcRenderer.invoke("saveImage", base64Data, fileName),
    lightControl: () => {
    ipcRenderer.send("light-control");
  },
  // 新增：获取后端就绪状态
  getBackendReadiness: () => ipcRenderer.invoke('get-backend-readiness'),
  // 新增：监听后端就绪状态的更新
  onBackendReadinessUpdate: (callback) => ipcRenderer.on('backend-readiness-update', (_event, value) => callback(value)),
  // 新增：在文件浏览器中显示
  openInExplorer: (relativePath) => ipcRenderer.send('open-in-explorer', relativePath)
});
