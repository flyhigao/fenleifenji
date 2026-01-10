import os
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from swift import Swift

# ================= 配置区 =================
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

# 1. Checkpoint 路径 (请确认路径正确)
ckpt_dir = '/home/gao/my_swift_project/output/fenleifenji_step1/checkpoint-16560'

# 2. 输入/输出文件
input_file = '/home/gao/fenleifenji/yiliao/combined.csvdescnull.json'
output_file = 'step2_predicted_desc.jsonl'

# 3. System Prompt
SYSTEM_PROMPT = (
    "你是一个医疗数据治理领域的元数据解析专家。"
    "你的任务是根据数据库表名和字段名（可能是拼音首字母、英文缩写或混合编码），"
    "结合医疗业务上下文，精准推断并输出其对应的中文业务含义（字段注释）。"
    "直接输出中文含义即可，无需解释。"
)

def get_base_model_path(ckpt_dir):

    return '/root/.cache/modelscope/hub/models/Qwen/Qwen3-8B'

    """从 args.json 中读取底座模型路径"""
    args_path = os.path.join(ckpt_dir, 'sft_args.json')
    if not os.path.exists(args_path):
        # 兼容旧版文件名为 args.json
        args_path = os.path.join(ckpt_dir, 'args.json')
    
    if os.path.exists(args_path):
        with open(args_path, 'r') as f:
            args = json.load(f)
            # 优先尝试读取 model_id_or_path，如果没有则尝试 model
            return args.get('model_id_or_path', args.get('model', 'Qwen/Qwen3-8B'))
    return 'Qwen/Qwen3-8B' # 保底默认值

def predict():
    # 1. 自动获取底座模型名称
    base_model_path = get_base_model_path(ckpt_dir)
    print(f"检测到底座模型: {base_model_path}")
    print(f"正在加载 LoRA 权重: {ckpt_dir}")

    # 2. 加载分词器
    tokenizer = AutoTokenizer.from_pretrained(
        base_model_path, 
        trust_remote_code=True
    )

    # 3. 加载模型 (原生 Transformers)
    model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        device_map="auto",
        torch_dtype=torch.float16, # 显存不够可改为 bfloat16 或 load_in_8bit=True
        trust_remote_code=True
    )

    # 4. 加载 Swift LoRA 权重
    model = Swift.from_pretrained(model, ckpt_dir, inference_mode=True)
    
    print("模型加载成功！开始推理...")

    # 读取输入
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    f_out = open(output_file, 'w', encoding='utf-8')
    
    # 进度条
    total = len(lines)
    
    for i, line in enumerate(lines):
        if not line.strip(): continue
        
        try:
            entry = json.loads(line)
            # 兼容 query / raw_data
            if 'query' in entry:
                query = entry['query']
            elif 'raw_data' in entry:
                uri = entry['raw_data'].get('uri', '').strip()
                name = entry['raw_data'].get('name', '').strip()
                query = f"tablename:{uri}; colname:{name}"
            else:
                continue
            
            # --- 构造 Qwen3 格式的 Prompt ---
            # 手动拼接 ChatML 格式，确保与 Swift 内部模板一致
            # <|im_start|>system\n...<|im_end|>\n<|im_start|>user\n...<|im_end|>\n<|im_start|>assistant\n
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query}
            ]
            text = tokenizer.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
            
            # 编码
            model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
            
            # 生成
            generated_ids = model.generate(
                model_inputs.input_ids,
                max_new_tokens=128,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                temperature=0.1, # 低温，保证确定性
                top_p=0.9
            )
            
            # 解码 (只取生成的回复部分)
            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            # 保存
            new_record = entry.copy()
            new_record['predicted_desc'] = response.strip()
            new_record['query'] = query # 补全 query 方便后续使用
            
            f_out.write(json.dumps(new_record, ensure_ascii=False) + '\n')
            f_out.flush()
            
            if (i+1) % 10 == 0:
                print(f"[{i+1}/{total}] {response}")

        except Exception as e:
            print(f"Error line {i}: {e}")
            continue

    f_out.close()
    print(f"完成！结果已保存在 {output_file}")

if __name__ == "__main__":
    predict()
