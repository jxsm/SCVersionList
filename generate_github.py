import os
import json
import hashlib
import re
from pathlib import Path
from urllib.parse import quote  # 用于标准URL编码（处理中文、括号等特殊字符）

def calculate_sha256(file_path):
    """计算文件的 SHA256 值（分块读取，支持大文件）"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # 4KB分块读取，避免占用过多内存
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"计算 {file_path.name} 的SHA256失败：{str(e)}")
        return "计算失败"

def parse_file_info(file_path, folder_type):
    """解析单个文件信息：提取主版本、子版本，生成标准GitHub URL"""
    file_name = file_path.name  # 原始文件名（如 "[电脑][插件]SCx2.1API1.2.zip"）
    file_size = file_path.stat().st_size  # 文件大小（字节）
    file_format = file_path.suffix.lstrip(".")  # 文件格式（zip/7z）

    # 1. 提取主版本（如从 "SCx2.1" 提取 "2.1"，用于后续排序）
    main_version_match = re.search(r"SCx(\d+\.\d+)", file_name)
    main_version = main_version_match.group(1) if main_version_match else "unknown"

    # 2. 提取子版本（如从 "API1.2" 提取 "API1.2"，用于排序和JSON字段）
    sub_version = "unknown"
    if folder_type == "API":
        # 匹配 "API" 后的版本号（支持多段，如 API1.8.1.0、API1.33）
        sub_match = re.search(r"API(\d+\.\d+(?:\.\d+)*)", file_name)
        if sub_match:
            sub_version = f"API{sub_match.group(1)}"
        # 特殊处理带 "NotOpenGLES" 的子版本（如 API1.8.1.0NotOpenGLES）
        if "NotOpenGLES" in file_name:
            sub_version += "NotOpenGLES"
    elif folder_type == "NET":
        # 匹配 "NET" 相关文件名中的版本（如从 "SCx2.3.01.12" 提取 "NET2.3.01.12"）
        sub_match = re.search(r"SCx(\d+\.\d+\.\d+\.\d+[a-z]?)", file_name)
        if sub_match:
            sub_version = f"NET{sub_match.group(1)}"
    elif folder_type == "Original":
        # 匹配 "Original" 相关文件名中的版本（如从 "SCx2.4.40" 提取 "Original2.4.40"）
        sub_match = re.search(r"SCx(\d+\.\d+(?:\.\d+)?)", file_name)
        if sub_match:
            sub_version = f"Original{sub_match.group(1)}"

    # 3. 生成标准GitHub URL（关键修复：使用原始文件名+URL编码，路径匹配目标格式）
    # GitHub路径规则：raw/refs/heads/main/[文件夹名]/[编码后的原始文件名]
    encoded_file_name = quote(file_name, safe="")  # 编码所有特殊字符（中文、括号、空格等）
    github_path = f"https://github.com/jxsm/SCVersionList/raw/refs/heads/main/{folder_type}/{encoded_file_name}"

    # 4. 自动计算SHA256
    sha256 = calculate_sha256(file_path)

    return {
        "main_version": main_version,  # 用于主版本排序
        "file_info": {
            "sub_version": sub_version,  # JSON中的子版本字段
            "size": file_size,
            "path": github_path,  # 修复后的正确GitHub链接
            "file_format": file_format,
            "illustrate": "",
            "sha256": sha256
        }
    }

def generate_json_manifest(root_dir):
    """生成JSON清单：大版本/子版本均按从大到小排序"""
    # 目标文件夹配置（名称对应本地文件夹，key对应JSON中的键）
    target_folders = [
        {"name": "API", "key": "api"},
        {"name": "NET", "key": "net"},
        {"name": "Original", "key": "original"}
    ]

    manifest = {}
    for folder in target_folders:
        folder_name = folder["name"]
        json_key = folder["key"]
        folder_path = Path(root_dir) / folder_name  # 本地文件夹路径

        # 检查文件夹是否存在
        if not folder_path.exists() or not folder_path.is_dir():
            print(f"警告：{folder_path} 文件夹不存在，跳过该分类")
            manifest[json_key] = None
            continue

        # 存储按主版本分组的文件信息
        version_group = {}
        # 获取所有zip/7z文件（不区分大小写）
        zip_files = list(folder_path.glob("*.[zZ][iI][pP]"))
        sevenz_files = list(folder_path.glob("*.[7zZ]"))
        all_files = zip_files + sevenz_files  # 合并文件列表

        # 遍历文件并解析信息
        for file in all_files:
            if file.is_file():  # 确保是文件（排除子文件夹）
                file_info = parse_file_info(file, folder_name)
                main_version = file_info["main_version"]
                file_detail = file_info["file_info"]

                # 按主版本分组（如2.4、2.3、2.2）
                if main_version not in version_group:
                    version_group[main_version] = []
                version_group[main_version].append(file_detail)

        # 1. 子版本排序：每个主版本下的子版本从大到小（如API1.8.1.0 > API1.8）
        for main_ver in version_group:
            def sub_version_cmp(sub_info):
                # 提取子版本中的数字（如API1.8.1.0 → [1,8,1,0]），用于排序
                ver_nums = re.findall(r"\d+", sub_info["sub_version"])
                return [int(num) for num in ver_nums] if ver_nums else [0]
            # 降序排序
            version_group[main_ver].sort(key=sub_version_cmp, reverse=True)

        # 2. 主版本排序：按主版本从大到小（如2.5 → 2.4 → 2.3 → 2.2）
        def main_version_cmp(ver):
            # 排除未知版本，已知版本按数字排序（如2.4 → [2,4]，2.3 → [2,3]）
            if ver == "unknown":
                return [-1]  # 未知版本放最后
            return [int(part) for part in ver.split(".")]
        # 对主版本键进行排序，重建有序字典
        sorted_main_vers = sorted(version_group.keys(), key=main_version_cmp, reverse=True)
        sorted_version_group = {ver: version_group[ver] for ver in sorted_main_vers}

        # 将排序后的结果存入manifest
        manifest[json_key] = sorted_version_group

    # 返回格式化的JSON字符串（缩进4格，支持中文）
    return json.dumps(manifest, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    # 本地根目录（请确认该路径下存在API、NET、Original三个文件夹）
    root_directory = "E:\\下载\\生存战争各个版本2\\电脑\\"
    # 生成JSON清单
    json_manifest = generate_json_manifest(root_directory)
    
    # 保存到本地文件（默认保存在程序运行目录下的 manifest.json）
    output_path = Path("manifest.json")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_manifest)
        print(f"✅ JSON清单已成功生成：{output_path.resolve()}")
        print("\n📌 示例链接格式（确保与目标一致）：")
        print("https://github.com/jxsm/SCVersionList/raw/refs/heads/main/API/%5B%E7%94%B5%E8%84%91%5D%5B%E6%8F%92%E4%BB%B6%5DSCx2.1API1.2.zip")
    except Exception as e:
        print(f"❌ 写入文件失败：{str(e)}")