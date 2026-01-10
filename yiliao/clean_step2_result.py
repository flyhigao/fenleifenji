import json
import re
import os

# ================= 配置区 =================
# 你的 Step 2 输出文件
INPUT_FILE = 'step2_predicted_desc.jsonl'
# 清洗后的输出文件
OUTPUT_FILE = 'step2_predicted_desc_cleaned.jsonl'

def clean_text(text):
    if not text:
        return ""
    
    # 1. 使用正则去除 <think>...</think> 及其包含的所有内容
    # flags=re.DOTALL 让 . 可以匹配换行符
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # 2. 去除首尾的空白字符 (换行、空格)
    cleaned = cleaned.strip()
    
    return cleaned

def process_cleaning():
    if not os.path.exists(INPUT_FILE):
        print(f"错误: 找不到文件 {INPUT_FILE}")
        return

    print(f"正在清洗文件: {INPUT_FILE} ...")
    
    cleaned_count = 0
    results = []

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            
            try:
                record = json.loads(line)
                
                # 获取原始预测结果
                raw_desc = record.get('predicted_desc', '')
                
                # 执行清洗
                final_desc = clean_text(raw_desc)
                
                # 更新记录
                record['predicted_desc'] = final_desc
                results.append(record)
                
                cleaned_count += 1
                
                # 打印前几个看看效果
                if cleaned_count <= 3:
                    print(f"\n[示例 {cleaned_count}]")
                    print(f"原始: {repr(raw_desc)}")
                    print(f"清洗: {repr(final_desc)}")
                    
            except Exception as e:
                print(f"解析错误: {e}")
                continue

    # 写入新文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print("-" * 50)
    print(f"清洗完成！")
    print(f"共处理: {cleaned_count} 条")
    print(f"输出文件: {OUTPUT_FILE}")
    print("请在 Step 3 数据生成时使用这个 cleaned 文件！")

if __name__ == "__main__":
    process_cleaning()
