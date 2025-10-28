import os
import json
import hashlib
import re
from pathlib import Path

def calculate_sha256(file_path):
    """计算文件的 SHA256 值"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def parse_file_info(file_path, folder_type):
    """解析单个文件信息"""
    file_name = file_path.name
    file_size = file_path.stat().st_size
    file_format = file_path.suffix.lstrip(".")

    # 提取主版本
    main_version_match = re.search(r"SCx(\d+\.\d+)", file_name)
    main_version = main_version_match.group(1) if main_version_match else "unknown"

    # 提取子版本
    sub_version = "unknown"
    if folder_type == "API":
        sub_match = re.search(r"API(\d+\.\d+(?:\.\d+)*)", file_name)
        if sub_match:
            sub_version = f"API{sub_match.group(1)}"
        if "NotOpenGLES" in file_name:
            sub_version += "NotOpenGLES"
    elif folder_type == "NET":
        sub_match = re.search(r"SCx(\d+\.\d+\.\d+\.\d+[a-z]?)", file_name)
        if sub_match:
            sub_version = f"NET{sub_match.group(1)}"
    elif folder_type == "Original":
        sub_match = re.search(r"SCx(\d+\.\d+(?:\.\d+)?)", file_name)
        if sub_match:
            sub_version = f"Original{sub_match.group(1)}"

    # 生成URL路径
    url_safe_name = file_name.replace(" ", "%20")
    github_path = f"https://github.com/jxsm/SCVersionList/raw/main/{folder_type}%2F{main_version}%20{sub_version}.{file_format}"

    # 自动计算SHA256
    sha256 = calculate_sha256(file_path)
    return {
        "main_version": main_version,
        "file_info": {
            "sub_version": sub_version,
            "size": file_size,
            "path": github_path,
            "file_format": file_format,
            "illustrate": "",
            "sha256": sha256
        }
    }

def generate_json_manifest(root_dir):
    """生成JSON清单"""
    target_folders = [
        {"name": "API", "key": "api"},
        {"name": "NET", "key": "net"},
        {"name": "Original", "key": "original"}
    ]

    manifest = {}
    for folder in target_folders:
        folder_name = folder["name"]
        json_key = folder["key"]
        folder_path = Path(root_dir) / folder_name

        if not folder_path.exists() or not folder_path.is_dir():
            print(f"警告：{folder_path} 文件夹不存在，跳过")
            manifest[json_key] = None
            continue

        version_group = {}
        # 关键修改：将生成器转换为列表后再拼接
        zip_files = list(folder_path.glob("*.[zZ][iI][pP]"))  # 所有zip文件（不区分大小写）
        sevenz_files = list(folder_path.glob("*.[7zZ]"))      # 所有7z文件（不区分大小写）
        all_files = zip_files + sevenz_files                  # 拼接文件列表

        for file in all_files:
            if file.is_file():
                file_info = parse_file_info(file, folder_name)
                main_version = file_info["main_version"]
                file_detail = file_info["file_info"]

                if main_version not in version_group:
                    version_group[main_version] = []
                version_group[main_version].append(file_detail)

        # 子版本排序（从大到小）
        for main_ver in version_group:
            def version_cmp(v):
                ver_match = re.findall(r"\d+", v["sub_version"])
                return [int(num) for num in ver_match] if ver_match else [0]
            # 已修改为降序排列
            version_group[main_ver].sort(key=version_cmp, reverse=True)

        # 大版本排序（从大到小）
        def main_version_cmp(version):
            if version == "unknown":
                return [-1]  # 未知版本放最后
            parts = version.split('.')
            return [int(part) for part in parts]
        
        # 对主版本进行排序并重建字典
        sorted_main_versions = sorted(version_group.keys(), key=main_version_cmp, reverse=True)
        sorted_version_group = {ver: version_group[ver] for ver in sorted_main_versions}
        version_group = sorted_version_group

        manifest[json_key] = version_group

    return json.dumps(manifest, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    root_directory = "E:\\下载\\生存战争各个版本2\\电脑\\"  # 你的根目录
    json_manifest = generate_json_manifest(root_directory)
    
    output_path = Path("manifest_github.json")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json_manifest)
    
    print(f"JSON清单已生成：{output_path.resolve()}")