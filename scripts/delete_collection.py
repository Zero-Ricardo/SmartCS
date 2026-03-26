# -*- coding: utf-8 -*-
"""
删除指定的 Qdrant 集合

用法：
    uv run python scripts/delete_collection.py <集合名称>
    uv run python scripts/delete_collection.py pxb_1
"""
import sys
import os

# Windows 控制台编码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.qdrant_service import qdrant_service


def list_collections():
    """列出所有集合"""
    try:
        collections = qdrant_service.qdrant_client.get_collections()
        print("\n当前所有集合：")
        print("-" * 40)
        if not collections.collections:
            print("  (无)")
        else:
            for c in collections.collections:
                info = qdrant_service.qdrant_client.get_collection(c.name)
                print(f"  - {c.name} ({info.points_count} 向量)")
        print()
    except Exception as e:
        print(f"获取集合列表失败: {e}")


def delete_collection(name: str):
    """删除指定集合"""
    if not qdrant_service.collection_exists(name):
        print(f"集合 '{name}' 不存在")
        return False

    try:
        # 先显示集合信息
        info = qdrant_service.qdrant_client.get_collection(name)
        print(f"\n即将删除集合: {name}")
        print(f"  向量数: {info.points_count}")

        # 确认删除
        confirm = input("\n确认删除？(y/n): ").strip().lower()
        if confirm != "y":
            print("��取消")
            return False

        # 删除
        qdrant_service.delete_collection(name)
        print(f"✓ 集合 '{name}' 已删除")
        return True
    except Exception as e:
        print(f"删除失败: {e}")
        return False


def main():
    print("=" * 40)
    print("Qdrant 集合管理工具")
    print("=" * 40)

    # 列出所有集合
    list_collections()

    # 获取要删除的集合名称
    if len(sys.argv) > 1:
        collection_name = sys.argv[1]
    else:
        collection_name = input("请输入要删除的集合名称: ").strip()

    if not collection_name:
        print("未输入集合名称，退出")
        return

    # 删除
    delete_collection(collection_name)

    # 再次列出集合
    list_collections()


if __name__ == "__main__":
    main()
