import socket
import json
import sys
from predict_two_steps import predict

def start_server(host='localhost', port=9999):
    print("启动模型服务器...")
    
    # 创建服务器socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(1)
    print(f"服务器正在监听 {host}:{port}")
    
    while True:
        try:
            client, addr = server.accept()
            print(f"接收到来自 {addr} 的连接")
            
            # 接收图片路径
            data = client.recv(1024).decode()
            if not data:
                continue
                
            # 进行预测
            try:
                result = predict(data)
                response = json.dumps(result, ensure_ascii=False)
            except Exception as e:
                response = json.dumps({"error": str(e)}, ensure_ascii=False)
            
            # 发送结果
            client.send(response.encode())
            client.close()
            
        except Exception as e:
            print(f"发生错误: {e}")
            continue

if __name__ == "__main__":
    start_server() 
