import os
import sys

def update_env_file(file_path: str, key: str, new_value: str):
    """
    更新 .env.local 文件中的指定键值对
    :param file_path: .env.local 文件路径
    :param key: 要更新的键
    :param new_value: 新值
    """
    try:
        if not os.path.exists(file_path):
            print(f"文件 {file_path} 不存在，无法更新。")
            return
        
        with open(file_path, "r") as file:
            lines = file.readlines()
        
        updated = False
        with open(file_path, "w") as file:
            for line in lines:
                # 如果是目标键，替换值
                if line.startswith(f"{key}="):
                    file.write(f"{key}={new_value}\n")
                    updated = True
                else:
                    file.write(line)
            
            # 如果键不存在，追加到文件末尾
            if not updated:
                file.write(f"{key}={new_value}\n")
        
        print(f"成功更新 {key} 的值为 {new_value}")
    except Exception as e:
        print(f"更新 .env.local 文件时出错: {e}")

if __name__ == "__main__":
    # 检查是否提供了命令行参数
    if len(sys.argv) != 3:
        print("用法: python update_env_file.py <key> <new_value>")
        sys.exit(1)

    # 从命令行获取键和值
    key = sys.argv[1]
    new_value = sys.argv[2]

    # 更新 .env.local 文件
    env_file = ".env.local"  # 根据实际路径调整
    update_env_file(env_file, key, new_value)
