"""
API 接口测试脚本
使用 requests 同步客户端测试
"""
import requests
import os

# 禁用代理
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

BASE_URL = "http://127.0.0.1:8000"
INTERNAL_SECRET = "your-internal-secret-key"

HEADERS = {
    "X-Internal-Secret": INTERNAL_SECRET,
    "Content-Type": "application/json",
}

# 设置 session 不使用代理
session = requests.Session()
session.trust_env = False  # 忽略环境变量中的代理设置


def test_health():
    """测试健康检查"""
    print("\n[1] 测试健康检查 GET /health")
    resp = session.get(f"{BASE_URL}/health")
    print(f"    状态码: {resp.status_code}")
    print(f"    响应: {resp.json()}")
    return resp.status_code == 200


def test_sessions_empty():
    """测试查询空会话列表"""
    print("\n[2] 测试查询会话 GET /internal/chat/sessions (空)")
    resp = session.get(
        f"{BASE_URL}/internal/chat/sessions",
        params={"guest_id": "test-guest-001"},
        headers=HEADERS,
    )
    print(f"    状态码: {resp.status_code}")
    print(f"    响应: {resp.json()}")
    return resp.status_code == 200


def test_sessions_no_auth():
    """测试无鉴权访问"""
    print("\n[3] 测试无鉴权访问 GET /internal/chat/sessions (应返回 401)")
    resp = session.get(
        f"{BASE_URL}/internal/chat/sessions",
        params={"guest_id": "test-guest-001"},
    )
    print(f"    状态码: {resp.status_code}")
    print(f"    响应: {resp.json()}")
    return resp.status_code == 401


def test_bind():
    """测试访客数据过户"""
    print("\n[4] 测试访客数据过户 POST /internal/chat/bind")
    resp = session.post(
        f"{BASE_URL}/internal/chat/bind",
        headers=HEADERS,
        json={
            "guest_id": "test-guest-001",
            "user_id": "user-12345",
        },
    )
    print(f"    状态码: {resp.status_code}")
    print(f"    响应: {resp.json()}")
    return resp.status_code == 200


def test_sessions_by_user():
    """测试按用户 ID 查询会话"""
    print("\n[5] 测试按用户 ID 查询 GET /internal/chat/sessions?user_id=xxx")
    resp = session.get(
        f"{BASE_URL}/internal/chat/sessions",
        params={"user_id": "user-12345"},
        headers=HEADERS,
    )
    print(f"    状态码: {resp.status_code}")
    print(f"    响应: {resp.json()}")
    return resp.status_code == 200


def main():
    print("=" * 50)
    print("SmartCS API 接口测试")
    print("=" * 50)

    tests = [
        ("健康检查", test_health),
        ("查询空会话", test_sessions_empty),
        ("无鉴权访问", test_sessions_no_auth),
        ("访客数据过户", test_bind),
        ("按用户查询", test_sessions_by_user),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✅ 通过" if success else "❌ 失败"))
        except Exception as e:
            results.append((name, f"❌ 异常: {e}"))

    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    for name, result in results:
        print(f"  {name}: {result}")


if __name__ == "__main__":
    main()
