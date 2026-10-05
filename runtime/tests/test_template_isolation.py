import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import template_packs as packs

class TemplateIsolation(unittest.TestCase):
    def test_custom_install_and_shadow_preserve_bundled_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            with patch.object(packs, 'PACK_ROOT', root / 'custom'):
                draft = root / 'draft'
                packs.scaffold('custom-test', 'custom-test@1.0', draft)
                self.assertTrue(packs.install(draft, '1.2.5')['ok'])
                self.assertEqual(packs.select('custom-test').root.parent, (root / 'custom').resolve())
                original = packs.select('search-market-snapshot')
                incoming = root / 'incoming'
                import shutil
                shutil.copytree(original.root, incoming)
                manifest = json.loads((incoming / 'manifest.json').read_text(encoding='utf-8'))
                manifest['version'] = '9.0.0'
                (incoming / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
                result = packs.update(incoming, '1.2.5')
                self.assertTrue(result['ok'])
                self.assertEqual(packs.select(original.pack_id).version, '9.0.0')
                self.assertEqual(packs.load_manifest(original.root).version, original.version)

    def test_different_id_cannot_duplicate_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            with patch.object(packs, 'PACK_ROOT', root):
                draft = root / 'collision'
                packs.scaffold('collision', 'compact-workbench@1.0', draft)
                with self.assertRaises(ValueError):
                    packs.discover()
