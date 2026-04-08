"""测试配置加载"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml


class TestConfig(unittest.TestCase):
    """测试配置文件"""
    
    def setUp(self):
        self.config_dir = Path(__file__).parent.parent / "config"
        
    def test_sources_yaml_exists(self):
        """测试sources.yaml存在"""
        config_file = self.config_dir / "sources.yaml"
        self.assertTrue(config_file.exists(), "sources.yaml不存在")
        
    def test_rss_native_config(self):
        """测试RSS native配置"""
        config_file = self.config_dir / "sources.yaml"
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        rss_native = config['sources'].get('rss', {}).get('native', {})
        self.assertTrue(rss_native.get('enabled', False), "RSS native未启用")


if __name__ == '__main__':
    unittest.main()
