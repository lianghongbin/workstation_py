import os
from loguru import logger

# ========== 全局配置 ==========
WATCH_ROOT = r"C:\watch_folder"

def find_photos_by_barcode(barcode: str, root_dir: str = WATCH_ROOT) -> list[str]:
    """
    根据 barcode 查找对应目录下的所有 JPG/JPEG 文件，返回完整路径数组。

    参数:
        barcode (str): 文件夹名（即条码）
        root_dir (str): 根目录路径，默认为 WATCH_ROOT

    返回:
        list[str]: 文件的完整路径列表，如果文件夹不存在或没有图片则返回空列表
    """
    if not barcode:
        return []

    folder_path = os.path.join(root_dir, barcode)

    # 检查是否存在该 barcode 文件夹
    if not os.path.isdir(folder_path):
        logger.info(f"没有找到 {barcode} 关联的图片.")
        return []

    # 收集 jpg/jpeg 文件
    photo_files = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename.lower().endswith((".jpg", ".jpeg")):
            photo_files.append(file_path)

    if not photo_files:
        logger.info(f"[{barcode}] 目录存在，但未找到 JPG/JPEG 文件。")
    else:
        logger.info(f"[{barcode}] 找到 {len(photo_files)} 个图片文件。")

    return photo_files