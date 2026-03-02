"""
测试运行脚本
提供便捷的测试执行方式
"""
import subprocess
import sys
import os

def run_unit_tests():
    """运行单元测试"""
    print("=" * 60)
    print("运行单元测试...")
    print("=" * 60)
    result = subprocess.run(
        ["pytest", "tests/", "-v", "-m", "unit", "--cov=app", "--cov-report=term-missing"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    return result.returncode


def run_integration_tests():
    """运行集成测试"""
    print("=" * 60)
    print("运行集成测试...")
    print("=" * 60)
    result = subprocess.run(
        ["pytest", "tests/", "-v", "-m", "integration", "--cov=app", "--cov-report=term-missing"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    return result.returncode


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("运行所有测试...")
    print("=" * 60)
    result = subprocess.run(
        ["pytest", "tests/", "-v", "--cov=app", "--cov-report=term-missing", "--cov-report=html"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    return result.returncode


def run_quick_tests():
    """快速测试（跳过慢速测试）"""
    print("=" * 60)
    print("运行快速测试...")
    print("=" * 60)
    result = subprocess.run(
        ["pytest", "tests/", "-v", "-m", "not slow", "--cov=app", "--cov-report=term-missing"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    return result.returncode


def generate_coverage_report():
    """生成覆盖率报告"""
    print("=" * 60)
    print("生成覆盖率报告...")
    print("=" * 60)
    result = subprocess.run(
        ["pytest", "tests/", "--cov=app", "--cov-report=html", "--cov-report=xml"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    if result.returncode == 0:
        print("\n覆盖率报告已生成:")
        print("  HTML: htmlcov/index.html")
        print("  XML: coverage.xml")
    
    return result.returncode


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python run_tests.py unit        # 运行单元测试")
        print("  python run_tests.py integration  # 运行集成测试")
        print("  python run_tests.py all         # 运行所有测试")
        print("  python run_tests.py quick       # 快速测试")
        print("  python run_tests.py coverage    # 生成覆盖率报告")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "unit":
        sys.exit(run_unit_tests())
    elif command == "integration":
        sys.exit(run_integration_tests())
    elif command == "all":
        sys.exit(run_all_tests())
    elif command == "quick":
        sys.exit(run_quick_tests())
    elif command == "coverage":
        sys.exit(generate_coverage_report())
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
