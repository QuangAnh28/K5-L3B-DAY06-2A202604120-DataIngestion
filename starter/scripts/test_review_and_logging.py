"""Regression checks for audit preservation and safe failures; no API requests."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
from urllib.error import HTTPError, URLError

STARTER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STARTER))
from src.ingestion import load_pdf
from src.embeddings import MyEmbedder
from src.store import VectorStore
from src.audit_io import load_audits
from src.event_log import record_event


class ReviewAndLogging(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.log = self.folder/'events.jsonl'
        self.secret = 'sk-or-v1-' + 'x' * 32
        self.env = patch.dict(os.environ, {'LAB_LOG_PATH': str(self.log), 'OPENROUTER_API_KEY': self.secret})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def events(self):
        return [json.loads(line) for line in self.log.read_text(encoding='utf-8').splitlines()]

    def test_pdf_errors_include_page_and_rethrow(self):
        with self.assertRaises(FileNotFoundError):
            load_pdf(self.folder/'missing.pdf', 'fixture', 'fixture-source')
        fake_page = type('Page', (), {'extract_text': lambda _self: (_ for _ in ()).throw(ValueError('bad page'))})()
        with patch('src.ingestion.PdfReader', return_value=type('Reader', (), {'pages': [fake_page]})()):
            with self.assertRaisesRegex(ValueError, 'bad page'):
                load_pdf(Path('fixture.pdf'), 'fixture', 'fixture-source')
        rows = self.events()
        self.assertTrue(any(r['event'] == 'failed' and r['stage'] == 'ingestion.load_pdf' for r in rows))
        self.assertTrue(any(r['event'] == 'failed' and r['context'].get('page') == 1 for r in rows))

    def test_provider_failure_is_logged_without_payload_or_key(self):
        error = HTTPError('https://fixture.invalid', 401, 'Unauthorized', None, io.BytesIO(self.secret.encode()))
        with patch('src.embeddings.urlopen', side_effect=error) as request:
            with self.assertRaisesRegex(RuntimeError, 'HTTP 401'):
                MyEmbedder('openai/text-embedding-3-small').embed_query('private fixture document text')
        request.assert_called_once()
        self.assertTrue(any(r['event'] == 'http_error' and r['context']['status'] == 401 for r in self.events()))
        text = self.log.read_text(encoding='utf-8')
        self.assertNotIn(self.secret, text)
        self.assertNotIn('private fixture document text', text)

    def test_storage_failure_is_logged(self):
        with patch('src.store.QdrantClient', side_effect=RuntimeError('storage unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'storage unavailable'):
                VectorStore(self.folder/'db')
        self.assertTrue(any(r['stage'] == 'vector_store.open' and r['event'] == 'failed' for r in self.events()))

    def test_secret_redaction(self):
        record_event('test', 'fixture', error=RuntimeError('Bearer ' + self.secret), url='postgresql://user:privatepassword@localhost/db', nested={'api_key':'hidden fixture value'})
        text = self.log.read_text(encoding='utf-8')
        self.assertNotIn(self.secret, text)
        self.assertNotIn('privatepassword', text)
        self.assertNotIn('hidden fixture value', text)
        self.assertIn('[REDACTED]', text)

    def test_network_retries_are_logged(self):
        with patch('src.embeddings.urlopen', side_effect=URLError('network unavailable')) as request, patch('src.embeddings.time.sleep'):
            with self.assertRaisesRegex(RuntimeError, 'Embedding request failed'):
                MyEmbedder('openai/text-embedding-3-small').embed_query('fixture input')
        self.assertEqual(request.call_count, 3)
        self.assertEqual([r['context']['attempt'] for r in self.events() if r['event']=='attempt_failed'], [1,2,3])

    def test_store_write_validation_and_search_backend_errors(self):
        store = VectorStore.__new__(VectorStore)
        store.dimensions = 3
        store.client = Mock()
        with self.assertRaisesRegex(ValueError, 'count mismatch'):
            store.upsert('A', [], [[1,0,0]])
        store.client.query_points.side_effect = RuntimeError('query backend failed')
        with self.assertRaisesRegex(RuntimeError, 'query backend failed'):
            store.search('A', [1,0,0])
        stages = {r['stage'] for r in self.events() if r['event']=='failed'}
        self.assertEqual(stages, {'vector_store.upsert','vector_store.search'})

    def copy_results(self):
        folder = self.folder/'results'
        folder.mkdir()
        for source in (STARTER/'results').glob('*.json'):
            if source.name != 'embedding_cache.json':
                shutil.copy2(source, folder/source.name)
        return folder

    def test_finalization_preserves_reviewer_edits_byte_for_byte(self):
        folder = self.copy_results()
        path = folder/'coherence_audit.json'
        rows = json.loads(path.read_text(encoding='utf-8'))
        rows[0].update(score=0, reason='Regression fixture: reviewer correction', student_confirmed=True,
                       confirmed_by='Regression fixture reviewer', custom_note='Preserve arbitrary review fields')
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
        names = ['coherence_audit.json','grounding_audit.json','metadata_audit.json']
        before = {name: (folder/name).read_bytes() for name in names}
        for _ in range(2):
            subprocess.run([sys.executable, str(STARTER/'scripts/finalize_artifacts.py'),
                            '--results-dir', str(folder), '--experiment-log', str(self.folder/'experiments.csv')],
                           check=True, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(before, {name: (folder/name).read_bytes() for name in names})

    def test_modified_input_requires_new_review(self):
        folder = self.copy_results()
        with (folder/'traces_test.json').open('a', encoding='utf-8') as stream:
            stream.write('\n')
        with self.assertRaisesRegex(ValueError, 're-review required'):
            load_audits(folder)

    def test_incomplete_audit_is_rejected(self):
        folder = self.copy_results()
        path = folder/'grounding_audit.json'
        path.write_text(json.dumps(json.loads(path.read_text(encoding='utf-8'))[:-1]), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            load_audits(folder)

if __name__ == '__main__':
    unittest.main()
