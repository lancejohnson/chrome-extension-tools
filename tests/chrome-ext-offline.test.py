#!/usr/bin/env python3
"""Offline installer safety/unit tests; integration also tested on Chrome 155 on macOS."""
import copy
import hashlib
import hmac
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('installer', str(Path(__file__).resolve().parents[1] / 'bin/chrome-ext-offline'))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


class InstallerTests(unittest.TestCase):
    def test_pruning_matches_chromium(self):
        self.assertEqual(m.prune({'a': {}, 'b': [{}, [], {'x': []}], 'c': False, 'd': ''}), {'c': False, 'd': ''})
        self.assertEqual(m.canonical({'b': '<', 'a': 'é'}), '{"a":"é","b":"\\u003C"}')

    def test_seed_discovery_absent_preference(self):
        with tempfile.TemporaryDirectory() as d:
            seed = b'seed'
            sig = hmac.new(seed, b'devicehomepage', hashlib.sha256).hexdigest().upper()
            p = Path(d) / 'resources.pak'
            p.write_bytes(struct.pack('<IBxxxHH', 5, 1, 1, 0) + struct.pack('<HIHI', 238, 24, 0, 28) + seed)
            data = {'protection': {'macs': {'homepage': sig}}}
            self.assertEqual(m.discover_seed(data, 'device', [p]), seed)

    def test_plan_backup_apply_and_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            profile = root / 'Default'
            profile.mkdir()
            folder = root / 'extension'
            folder.mkdir()
            (folder / 'manifest.json').write_text(json.dumps({'manifest_version': 3, 'name': 'Test', 'version': '1.0', 'permissions': ['storage']}))
            hashes = {'extensions': {'settings': {}}}
            data = {'protection': {'macs': hashes, 'super_mac': m.mac(b'seed', 'device', '', hashes), 'super_encrypted_hash': 'preserve-me'}}
            target = profile / 'Secure Preferences'
            target.write_text(json.dumps(data))
            original = target.read_bytes()
            argv = ['installer', str(folder), '--profile', str(profile)]
            with patch.object(sys, 'argv', argv), patch.object(m, 'discover_seed', return_value=b'seed'), patch.object(m.subprocess, 'check_output', return_value='"IOPlatformUUID" = "device"'), patch.object(m, 'chrome_running', return_value=False), patch('builtins.print'):
                m.main()
                self.assertEqual(target.read_bytes(), original)
                sys.argv = argv + ['--apply']
                m.main()
                updated = json.loads(target.read_bytes())
                self.assertEqual(updated['protection']['super_encrypted_hash'], 'preserve-me')
                eid = next(iter(updated['extensions']['settings']))
                self.assertEqual(updated['protection']['macs']['extensions']['settings'][eid], m.mac(b'seed', 'device', 'extensions.settings.' + eid, updated['extensions']['settings'][eid]))
                backups = list(profile.glob('Secure Preferences.chrome-ext-backup-*'))
                self.assertEqual(len(backups), 1)
                self.assertEqual(backups[0].read_bytes(), original)
                before = target.read_bytes()
                m.main()
                self.assertEqual(target.read_bytes(), before)
                with patch.object(m, 'chrome_running', return_value=True):
                    with self.assertRaisesRegex(ValueError, 'Chrome is running'):
                        m.main()
                updated['protection']['super_mac'] = 'invalid'
                target.write_text(json.dumps(updated))
                with self.assertRaisesRegex(ValueError, 'signature failed'):
                    m.main()


if __name__ == '__main__':
    unittest.main()
