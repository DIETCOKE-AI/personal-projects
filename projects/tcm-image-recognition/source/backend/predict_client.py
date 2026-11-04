import socket
import json
import sys
import time
def predict(image_path, host='localhost', port=9999):
    # 创建客户端socket
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # 连接服务器
        client.connect((host, port))
        
        # 发送图片路径
        client.send(image_path.encode())
        
        # 接收结果
        response = client.recv(4096).decode()
        result = json.loads(response)
        
        return result
    except Exception as e:
        return {"error": f"连接服务器失败: {str(e)}"}
    finally:
        client.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python predict_client.py <图片路径>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    start = time.time()
    result = predict(image_path)
    end = time.time()
    print(json.dumps(result, ensure_ascii=False)) 
    print(f"预测时间: {end - start}秒")
