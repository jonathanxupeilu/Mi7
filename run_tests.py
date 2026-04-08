#!/usr/bin/env python3
"""MI7 测试运行器"""
import subprocess
import sys


def run_tests():
    """运行所有测试"""
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', 'tests/', '-v', '--tb=short'],
        capture_output=False
    )
    return result.returncode


def run_with_coverage():
    """运行测试并生成覆盖率报告"""
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', 'tests/', '-v', '--cov=.', '--cov-report=term-missing'],
        capture_output=False
    )
    return result.returncode


def run_specific_test(test_path):
    """运行特定测试"""
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', test_path, '-v'],
        capture_output=False
    )
    return result.returncode


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='MI7 Test Runner')
    parser.add_argument('--coverage', '-c', action='store_true', help='Run with coverage')
    parser.add_argument('--test', '-t', help='Run specific test file')
    args = parser.parse_args()

    if args.coverage:
        sys.exit(run_with_coverage())
    elif args.test:
        sys.exit(run_specific_test(args.test))
    else:
        sys.exit(run_tests())
