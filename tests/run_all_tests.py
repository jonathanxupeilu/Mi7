#!/usr/bin/env python3
"""运行所有测试"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest

# 导入测试模块
from tests import test_config

# 创建测试套件
loader = unittest.TestLoader()
suite = unittest.TestSuite()

# 添加测试
suite.addTests(loader.loadTestsFromModule(test_config))

# 运行测试
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# 输出结果
print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
print(f"Tests run: {result.testsRun}")
print(f"Failures: {len(result.failures)}")
print(f"Errors: {len(result.errors)}")
print(f"Success: {result.wasSuccessful()}")

# 返回状态码
sys.exit(0 if result.wasSuccessful() else 1)
