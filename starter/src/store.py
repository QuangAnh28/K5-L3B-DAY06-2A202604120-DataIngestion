"""Persistent Qdrant local store, exact cosine search and payload filters."""
import uuid
import math
from qdrant_client import QdrantClient, models
from .event_log import logged

class VectorStore:
    @logged('vector_store.open')
    def __init__(self, path, dimensions=1536):
        self.client = QdrantClient(path=str(path))
        self.dimensions = dimensions

    @logged('vector_store.upsert')
    def upsert(self, strategy, chunks, vectors):
        if len(chunks) != len(vectors):
            raise ValueError('Chunk/vector count mismatch')
        if any(len(v) != self.dimensions or not all(math.isfinite(x) for x in v) for v in vectors):
            raise ValueError('Invalid vector dimensions or values')
        if self.client.collection_exists(strategy):
            config = self.client.get_collection(strategy).config.params.vectors
            if config.size != self.dimensions or config.distance != models.Distance.COSINE:
                raise ValueError('Existing collection configuration mismatch')
            self.client.delete(strategy, points_selector=models.FilterSelector(filter=models.Filter()), wait=True)
        else:
            self.client.create_collection(strategy, vectors_config=models.VectorParams(size=self.dimensions, distance=models.Distance.COSINE))
        points = [models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, c.chunk_id)), vector=v,
                  payload=dict(c.metadata, chunk_id=c.chunk_id, text=c.text, document_id=c.document_id,
                  source=c.source, page=c.page)) for c, v in zip(chunks, vectors)]
        for start in range(0, len(points), 128):
            self.client.upsert(strategy, points[start:start+128], wait=True)

    @logged('vector_store.search')
    def search(self, strategy, query_vector, top_k=3, filters=None):
        if len(query_vector) != self.dimensions:
            raise ValueError('Query dimension mismatch')
        if filters and set(filters) - {'chapter', 'year', 'section'}:
            raise ValueError('Unsupported filter')
        filt = models.Filter(must=[models.FieldCondition(key=k, match=models.MatchValue(value=v))
                 for k,v in filters.items()]) if filters else None
        # Qdrant local always uses exact search.
        rows = self.client.query_points(strategy, query=query_vector, query_filter=filt, limit=top_k).points
        return [dict(p.payload, score=p.score) for p in rows]

    @logged('vector_store.count')
    def count(self, strategy):
        return self.client.count(strategy, exact=True).count

    @logged('vector_store.close')
    def close(self):
        self.client.close()
