import os
import sys
import time
import torch
import torch.nn.functional as F
import json
import glob
import pandas as pd
from PIL import Image
from torchvision import transforms
from tqdm import tqdm

# --- 路径设置 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)
from modelEnsemble.evaluate_threeaccept_ensemble import load_ensemble_models
from conf import configs

def time_process_for_single_image(models_to_test, image_path, transform, device, threshold):
    """对单张图片进行端到端的全流程计时，并分解到最精细的各个阶段。"""
    timings = {}
    
    # 阶段1: IO与预处理
    t0 = time.perf_counter()
    try:
        image = Image.open(image_path).convert('RGB')
        image_tensor_cpu = transform(image).unsqueeze(0)
    except Exception as e:
        print(f"\n错误：处理图片 '{os.path.basename(image_path)}' 时失败: {e}")
        return None
    t1 = time.perf_counter()
    timings['io_preprocess_ms'] = (t1 - t0) * 1000

    # 阶段2: 数据传输
    t2 = time.perf_counter()
    image_tensor_gpu = image_tensor_cpu.to(device)
    if device.type == 'cuda': torch.cuda.synchronize()
    t3 = time.perf_counter()
    timings['transfer_ms'] = (t3 - t2) * 1000

    # 阶段3: 纯模型推理
    t4 = time.perf_counter()
    with torch.no_grad():
        model_outputs = [F.softmax(model(image_tensor_gpu), dim=1) for model in models_to_test]
    if device.type == 'cuda': torch.cuda.synchronize()
    t5 = time.perf_counter()
    timings['pure_inference_ms'] = (t5 - t4) * 1000

    # 阶段4: 决策逻辑
    t6 = time.perf_counter()
    if len(models_to_test) == 1:
        final_conf, _ = torch.max(model_outputs[0], dim=1)
        if final_conf.item() >= threshold: final_decision = "ACCEPT"
        else: final_decision = "REJECT"
    else:
        preds_indices = [torch.max(p[0], dim=0)[1].item() for p in model_outputs]
        confs = [torch.max(p[0], dim=0)[0].item() for p in model_outputs]
        final_decision = "REJECT"
        votes = {}
        for p_idx, c_val in zip(preds_indices, confs):
            if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
        if votes and max(votes.values()) >= 3: final_decision = "ACCEPT"
    t7 = time.perf_counter()
    timings['decision_logic_ms'] = (t7 - t6) * 1000
    
    timings['total_ms'] = timings['io_preprocess_ms'] + timings['transfer_ms'] + timings['pure_inference_ms'] + timings['decision_logic_ms']
    return timings

def run_batch_test(models_to_run, image_paths, desc, transform, device, threshold):
    """一个辅助函数，用于执行一批测试并返回结果的DataFrame。"""
    all_timings_list = []
    for img_path in tqdm(image_paths, desc=desc, unit="张"):
        timings_dict = time_process_for_single_image(models_to_run, img_path, transform, device, threshold)
        if timings_dict:
            all_timings_list.append(timings_dict)
    return pd.DataFrame(all_timings_list)

def generate_report(df, title, input_path, num_images_total):
    """一个辅助函数，用于生成标准化的性能报告 (已移除FLOPs)。"""
    print("\n" + "=" * 65)
    print(f"📊 {title}")
    print("-" * 65)

    if not df.empty:
        num_processed = len(df)
        print(f"  测试路径:      {input_path}")
        print(f"  成功处理图片:  {num_processed} / {num_images_total} 张")
        
        if num_processed > 1:
            avg_timings = df.mean()
            total_timings_ms = df.sum()
            
            print("\n--- 各阶段总耗时 (毫秒/ms) ---")
            print(f"  ┣━ 🖼️ 1. IO与预处理总耗时:   {total_timings_ms['io_preprocess_ms']:.2f} ms")
            print(f"  ┣━ 🚚 2. 数据传输总耗时:     {total_timings_ms['transfer_ms']:.2f} ms")
            print(f"  ┣━ 🧠 3. 纯模型推理总耗时:   {total_timings_ms['pure_inference_ms']:.2f} ms")
            print(f"  ┗━ ⚙️ 4. 决策逻辑总耗时:     {total_timings_ms['decision_logic_ms']:.2f} ms")
            print(f"  ┣━━━ ⏱️ 批次处理总耗时:       {total_timings_ms['total_ms']:.2f} ms")

            print("\n--- 平均耗时分解 (毫秒/ms) ---")
            print(f"  ┣━ 🖼️ 1. IO与预处理:       {avg_timings['io_preprocess_ms']:.2f} ms")
            print(f"  ┣━ 🚚 2. 数据传输:         {avg_timings['transfer_ms']:.2f} ms")
            print(f"  ┣━ 🧠 3. 纯模型推理:       {avg_timings['pure_inference_ms']:.2f} ms")
            print(f"  ┗━ ⚙️ 4. 决策逻辑:         {avg_timings['decision_logic_ms']:.2f} ms")
            print(f"  ┣━━━ ✅ 总计平均耗时:       {avg_timings['total_ms']:.2f} ms")
        else: 
            single_timing = df.iloc[0]
            print("\n--- 单次耗时分解 (毫秒/ms) ---")
            print(f"  ┣━ 🖼️ 1. IO与预处理:       {single_timing['io_preprocess_ms']:.2f} ms")
            print(f"  ┣━ 🚚 2. 数据传输:         {single_timing['transfer_ms']:.2f} ms")
            print(f"  ┣━ 🧠 3. 纯模型推理:       {single_timing['pure_inference_ms']:.2f} ms")
            print(f"  ┗━ ⚙️ 4. 决策逻辑:         {single_timing['decision_logic_ms']:.2f} ms")
            print(f"  ┣━━━ ✅ 总计耗时:           {single_timing['total_ms']:.2f} ms")
    else:
        print("  所有图片都处理失败，无法生成报告。")
    print("=" * 65)

# ==============================================================================
# 🚀 主程序入口
# ==============================================================================
if __name__ == '__main__':
    # --- ⚙️ 1. 配置区域 ---
    INPUT_PATH = './data/example-images'
    ENSEMBLE_CONFIG_PATH = 'modelEnsemble/model_ensemble_config.json'
    CUSTOM_MAPPINGS_PATH = 'custom_mapping.json'
    DATASET_NAME = 'medicine_99'
    VOTING_THRESHOLD = 0.7
    GPU_ID = '0'
    IMG_SIZE = 640

    # --- 2. 智能判断输入路径类型 ---
    image_paths = []
    if not os.path.exists(INPUT_PATH): print(f"🚨 错误：路径不存在 '{INPUT_PATH}'"); sys.exit(1)
    if os.path.isfile(INPUT_PATH):
        image_paths.append(INPUT_PATH)
    elif os.path.isdir(INPUT_PATH):
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.webp']
        for ext in image_extensions:
            image_paths.extend(glob.glob(os.path.join(INPUT_PATH, ext)))
        if not image_paths: print(f"在文件夹 '{INPUT_PATH}' 中没有找到任何图片文件。"); sys.exit(0)
    else: print(f"🚨 错误：路径 '{INPUT_PATH}' 既不是文件也不是文件夹。"); sys.exit(1)

    # --- 3. 初始化环境和加载模型 ---
    configs.run_mode = 'test'; configs.path_init(); os.environ['CUDA_VISIBLE_DEVICES'] = GPU_ID
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"当前运行设备: {device}")
    with open(ENSEMBLE_CONFIG_PATH, 'r', encoding='utf-8') as f: model_configs = json.load(f)
    with open(CUSTOM_MAPPINGS_PATH, 'r', encoding='utf-8') as f: class_to_idx = json.load(f)[DATASET_NAME]['class_to_idx']
    print("正在加载集成模型...")
    all_models_list = load_ensemble_models(model_configs, class_to_idx, configs.ckpts_dir, device)
    for model in all_models_list: model.eval()
    transform = transforms.Compose([transforms.Resize((IMG_SIZE, IMG_SIZE)), transforms.ToTensor(), transforms.Normalize(configs.mean, configs.std)])
    print("模型加载完毕。\n")
    
    # --- 4. 运行测试 ---
    # 首先，测试完整的集成模型
    print("--- 开始测试集成模型性能 ---")
    df_ensemble = run_batch_test(all_models_list, image_paths, "集成模型测试", transform, device, VOTING_THRESHOLD)

    # 然后，遍历并测试每一个单一模型
    print("\n--- 开始逐一测试单个模型性能 ---")
    individual_results = []
    for i, model_config in enumerate(model_configs):
        model_name = model_config['model_name']
        current_model = all_models_list[i]
        
        # 为当前循环的单一模型执行批量测试
        desc = f"测试: {model_name}"
        df_single = run_batch_test([current_model], image_paths, desc, transform, device, VOTING_THRESHOLD)
        
        # 将结果（DataFrame）和模型名字一起保存，便于后续报告
        individual_results.append({'name': model_name, 'df': df_single})

    # --- 5. 生成并显示所有报告 ---
    print("\n\n" + "#" * 30 + "  测试结果总结  " + "#" * 30)
    
    # 报告1: 集成模型
    generate_report(df_ensemble, f"集成模型 ({len(all_models_list)}个) 性能报告", INPUT_PATH, len(image_paths))
    
    # 报告2, 3, 4...: 循环打印每个单一模型的报告
    for result in individual_results:
        model_name = result['name']
        df_result = result['df']
        generate_report(df_result, f"单一模型 ({model_name}) 性能报告", INPUT_PATH, len(image_paths))