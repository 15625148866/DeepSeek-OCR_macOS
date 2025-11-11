import os
import sys
import requests, json, sys
import pandas as pd
API = "http://localhost:11434/api/chat"

def chat_stream(prompt: str,
                model = "deepseek-r1:70b"):
    body = {
        "model": model,
        "messages": [
            {
                "role":"user",
                "content":prompt
            },
        ],
        "stream": True
    }
    s = requests.post(API, json=body, stream=True)
    for line in s.iter_lines():
        if line:
            yield json.loads(line)["message"]["content"]

def chat_complete(prompt: str,
                  model = "deepseek-r1:70b"):
    body = {
        "model": model,
        "messages": [
            {
                "role":"user",
                "content":prompt
            },
        ],
        "stream": False  # 关闭流式输出
    }
    response = requests.post(API, json=body)
    if response.status_code == 200:
        data = response.json()
        return data["message"]["content"]
    else:
        return f"Error: {response.status_code} - {response.text}"
    
def parse_doctor_info_to_dataframe(result_text):
    """
    解析AI返回的医生信息文本，构建pandas DataFrame
    期望格式：每行一个字段，使用冒号分隔
    例如：
    姓名: 张三
    学历: 博士
    职称: 主任医师
    """
    # 定义需要的字段
    fields = ["姓名", "学历", "科室","职称", "职位", "开诊时间", "个人学术任职", "擅长的临床领域"]
    
    # 初始化字典来存储解析结果
    doctor_data = {field: "" for field in fields}
    
    # 按行分割文本
    lines = result_text.strip().split('\n')
    
    for line in lines:
        # 检查是否包含冒号分隔符
        if ':' in line:
            parts = line.split(':', 1)  # 只分割第一个冒号
            if len(parts) == 2:
                field_name = parts[0].strip()
                field_value = parts[1].strip()
                
                # 检查字段名是否在预定义字段中
                for field in fields:
                    if field in field_name:
                        doctor_data[field] = field_value
                        break
    
    # 创建DataFrame
    df = pd.DataFrame([doctor_data])
    return df

def batch_process_images(directory_path):
    """
    批量处理目录下的所有jpg图片
    """
    all_doctors_data = []
    processed_count = 0
    error_count = 0
    
    print(f"开始遍历目录: {directory_path}")
    
    # 使用os.walk递归遍历目录
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            # 检查是否为jpg文件（不区分大小写）
            if file.lower().endswith(('.jpg', '.jpeg')):
                img_path = os.path.join(root, file)
                print(f"\n处理第 {processed_count + 1} 张图片: {img_path}")
                
                try:
                    # OCR识别
                    result_text = ENGINE.infer(image_path=img_path, prompt="<image>\nFree OCR.")
                    
                    # AI解析医生信息
                    ai_result = chat_complete(
                        prompt="请严格按照以下格式汇总这位临床医生的信息，每项占一行，使用冒号分隔，格式为：字段名:值。如果某项信息不存在，请填写'未提及'。\n" +
                                "需要的字段：\n" +
                                "姓名: [医生姓名]\n" +
                                "学历: [学历信息]\n" +
                                "科室: [科室信息]\n" +
                                "职称: [职称信息]\n" +
                                "职位: [职位信息]\n" +
                                "开诊时间: [开诊时间]\n" +
                                "个人学术任职: [学术任职]\n" +
                                "擅长的临床领域: [擅长领域]\n\n" +
                                "以下是这位临床医生的介绍: " + result_text
                    )
                    
                    # 解析为DataFrame格式
                    doctor_df = parse_doctor_info_to_dataframe(ai_result)
                    
                    # 添加图片路径信息
                    doctor_df['图片路径'] = img_path
                    doctor_df['文件名'] = file
                    doctor_df['目录路径'] = root
                    
                    # 添加到总数据列表
                    all_doctors_data.append(doctor_df)
                    processed_count += 1
                    
                    print(f"✓ 成功处理: {file}")
                    print(f"AI解析结果: {ai_result[:100]}...")  # 显示前100个字符
                    
                except Exception as e:
                    error_count += 1
                    print(f"✗ 处理失败: {file}, 错误: {str(e)}")
    
    # 合并所有数据
    if all_doctors_data:
        final_df = pd.concat(all_doctors_data, ignore_index=True)
        print(f"\n批量处理完成!")
        print(f"成功处理: {processed_count} 张图片")
        print(f"处理失败: {error_count} 张图片")
        print(f"最终表格形状: {final_df.shape}")
        return final_df
    else:
        print("未找到任何jpg图片或所有处理都失败")
        return pd.DataFrame()

_current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(_current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
# Import our workflow components
from macos_workflow.ocr_engine_macos import OCREngine
from macos_workflow import config_macos as config
from macos_workflow.utils import re_match, draw_bounding_boxes, pdf_to_images, save_images_to_pdf

ENGINE = OCREngine(project_root=project_root)

# 设置要遍历的目录路径
target_directory = r"/Users/zhaokaixuan/Downloads/海报"  # 修改为你需要遍历的目录

# 批量处理所有jpg图片
if os.path.exists(target_directory):
    doctors_dataframe = batch_process_images(target_directory)
    
    if not doctors_dataframe.empty:
        print("\n" + "="*80)
        print("最终汇总表格:")
        print(doctors_dataframe)
        
        # 保存到CSV文件
        output_file = "医生信息批量汇总.xlsx"
        doctors_dataframe.to_excel(os.path.join(target_directory, output_file), index=False)
        print(f"\n表格已保存到: {output_file}")
        
        # 显示统计信息
        print(f"\n统计信息:")
        print(f"总记录数: {len(doctors_dataframe)}")
        print(f"列名: {list(doctors_dataframe.columns)}")
        
        # 显示每列的非空值数量
        print("\n各字段填充情况:")
        for column in doctors_dataframe.columns:
            non_empty_count = doctors_dataframe[column].astype(str).str.strip().ne('').sum()
            print(f"{column}: {non_empty_count}/{len(doctors_dataframe)}")
else:
    print(f"目录不存在: {target_directory}")
    print("请修改target_directory变量为正确的目录路径")