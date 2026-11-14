"""Meaningful storage and chunking invariants; no provider calls."""
import sys, tempfile, unittest, os
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.store import VectorStore
from src.models import Chunk, DocumentPage
from src.chunking import fixed_size

class Contracts(unittest.TestCase):
    def setUp(self):
        self.logs = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'LAB_LOG_PATH': str(Path(self.logs.name)/'test_events.jsonl')})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.logs.cleanup()

    def test_snapshot_filter_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            store=VectorStore(folder,3)
            c=lambda id,ch: Chunk(id,'doc','source',1,'text',{'chapter':ch})
            store.upsert('A',[c('old','I'),c('keep','II')],[[1,0,0],[0,1,0]])
            self.assertEqual(store.search('A',[1,0,0],filters={'chapter':'II'})[0]['chunk_id'],'keep')
            store.upsert('A',[c('keep','II')],[[0,1,0]])
            store.close()
            store=VectorStore(folder,3)
            self.assertEqual(store.count('A'),1)
            self.assertEqual(store.search('A',[0,1,0])[0]['chunk_id'],'keep')
            with self.assertRaises(ValueError): store.search('A',[1,0,0],filters={'text':'x'})
            store.close()

    def test_overlap_and_stability(self):
        page=DocumentPage('d','s',1,'abcdefghijk',{})
        a=fixed_size(page,5,2)
        self.assertEqual([c.text for c in a],['abcde','defgh','ghijk'])
        self.assertEqual([c.chunk_id for c in a],[c.chunk_id for c in fixed_size(page,5,2)])
        with self.assertRaises(ValueError): fixed_size(page,5,5)

if __name__=='__main__': unittest.main()
