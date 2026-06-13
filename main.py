"""Jubeat 音乐魔方 B60"""
import os, sys, subprocess, ctypes

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)  # exe 所在目录
    DATA_DIR = sys._MEIPASS                      # 打包资源 (_internal)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = BASE_DIR

os.chdir(BASE_DIR)  # 输出文件写到 exe 目录

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    # 将 DATA_DIR 注入环境变量，子脚本通过它读取静态资源
    os.environ["DATA_DIR"] = DATA_DIR

    # 1. get_token
    print("=" * 50)
    print("  Step 1/3: 获取 Token")
    print("=" * 50)
    import get_token
    get_token.SCRIPT_DIR = BASE_DIR  # get_token 读写都在 exe 目录
    if get_token.main() != 0:
        print("\nToken 获取失败")
        return 1

    # 2. crawl_scores
    print("\n" + "=" * 50)
    print("  Step 2/3: 爬取成绩")
    print("=" * 50)
    import crawl_scores
    crawl_scores.SCRIPT_DIR = BASE_DIR
    try:
        crawl_scores.main()
    except Exception as e:
        print(f"\n爬取失败: {e}")
        return 1

    # 3. generate
    print("\n" + "=" * 50)
    print("  Step 3/3: 生成图片")
    print("=" * 50)
    import generate
    generate.SCRIPT_DIR = BASE_DIR
    return generate.main()

if __name__ == "__main__":
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
    sys.exit(main())
