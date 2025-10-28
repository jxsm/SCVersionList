import json

def replace_github_with_gitee(json_file_path, output_file_path):
    """
    将JSON文件中所有path的github域名替换为gitee域名
    
    参数:
        json_file_path: 原始JSON文件路径
        output_file_path: 处理后的JSON文件输出路径
    """
    # 读取原始JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 递归处理所有包含path的字段
    def process_dict(d):
        if isinstance(d, dict):
            # 如果字典包含path字段，替换域名
            if 'path' in d:
                # 将github.com/jxsm替换为gitee.com/jxsmjxee
                d['path'] = d['path'].replace(
                    'github.com/jxsm', 
                    'gitee.com/jxsmjxee'
                ).replace(
                    'refs/heads/main',  # 替换GitHub的main分支路径
                    'main'  # Gitee对应的main分支路径
                )
            # 递归处理字典中的其他字段
            for key, value in d.items():
                process_dict(value)
        elif isinstance(d, list):
            # 递归处理列表中的每个元素
            for item in d:
                process_dict(item)
    
    # 处理数据
    process_dict(data)
    
    # 保存处理后的JSON文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"处理完成，结果已保存到 {output_file_path}")

if __name__ == "__main__":
    # 输入文件路径（原始manifest.json的路径）
    input_path = "manifest.json"
    # 输出文件路径（处理后的JSON文件路径）
    output_path = "manifest_gitee.json"
    
    replace_github_with_gitee(input_path, output_path)