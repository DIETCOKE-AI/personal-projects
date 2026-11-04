import { ref } from "vue";

export const useMediaSource = () => {
  const mediaSource = ref<MediaSource>(new MediaSource());
  const sourceBuffer = ref<SourceBuffer | null>(null);
  const bufferQueue = ref<Uint8Array[]>([]);
  const mediaSourceUrl = ref<string>(""); // 存储 Object URL

  // 初始化MediaSource
  const initMediaSource = (): Promise<string> => {
    return new Promise((resolve) => {
      mediaSource.value.addEventListener("sourceopen", () => {
        sourceBuffer.value = mediaSource.value.addSourceBuffer(
          'video/mp4; codecs="avc1.64001F"'
        );
        sourceBuffer.value.addEventListener("updateend", processQueue);
        mediaSourceUrl.value = URL.createObjectURL(mediaSource.value);
        resolve(mediaSourceUrl.value);
      });
    });
  };

  // 缓冲队列处理
  const processQueue = () => {
    if (sourceBuffer.value && !sourceBuffer.value.updating) {
      if (bufferQueue.value.length > 0) {
        sourceBuffer.value.appendBuffer(bufferQueue.value.shift()!);
      }
    }
  };

  // 追加媒体分片
  const appendBuffer = (chunk: Uint8Array) => {
    if (sourceBuffer.value) {
      bufferQueue.value.push(chunk);
      processQueue();
    }
  };

  // 资源释放
  const destroy = () => {
    if (mediaSource.value.readyState === "open") {
      mediaSource.value.endOfStream();
    }
    if (mediaSourceUrl.value) {
      URL.revokeObjectURL(mediaSourceUrl.value);
      mediaSourceUrl.value = "";
    }
  };

  return { initMediaSource, appendBuffer, destroy, mediaSourceUrl };
};
