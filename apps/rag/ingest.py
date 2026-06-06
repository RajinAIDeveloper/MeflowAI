"""
Document ingestion pipeline: text → embedding → KnowledgeDocument.

Usage:
    from apps.rag.ingest import ingest_document, ingest_text, ingest_doctor_profiles

    ingest_document(title="...", content="...", doc_type="medical_faq")  # 1 short doc -> 1 vector
    ingest_text(title="ER Policy", content=long_text, doc_type="hospital_policy",
                source_id="er-policy")                                   # long doc -> many chunks
    ingest_doctor_profiles()                                             # bulk-index Doctors
"""
import logging

from .chunking import chunk_text
from .embeddings import embed_text
from .models import KnowledgeDocument

logger = logging.getLogger(__name__)


def ingest_document(
    title: str,
    content: str,
    doc_type: str,
    source_id: str = '',
    metadata: dict | None = None,
) -> KnowledgeDocument:
    """Embed a single short text as one KnowledgeDocument (one vector).

    For long documents (policies, guides) use ingest_text(), which chunks first.
    """
    embedding = embed_text(content)
    doc, created = KnowledgeDocument.objects.update_or_create(
        doc_type=doc_type,
        source_id=source_id,
        defaults={
            'title': title,
            'content': content,
            'embedding': embedding,
            'metadata': metadata or {},
        },
    )
    action = 'created' if created else 'updated'
    logger.info("KnowledgeDocument %s (pk=%s)", action, doc.pk)
    return doc


def ingest_text(
    title: str,
    content: str,
    doc_type: str,
    source_id: str,
    metadata: dict | None = None,
) -> list[KnowledgeDocument]:
    """Chunk a long document and embed each chunk as its own KnowledgeDocument.

    Each chunk row has source_id "<source_id>::chunk-<i>" and metadata carrying
    the parent source_id + chunk index. Idempotent: prior chunks for this parent
    are deleted first, so re-ingesting an edited document never leaves orphans.
    """
    if not source_id:
        raise ValueError('ingest_text requires a stable source_id (used to group/refresh chunks).')

    # Clear any previous chunks for this parent so edits don't leave stale rows.
    deleted, _ = (KnowledgeDocument.objects
                  .filter(doc_type=doc_type, source_id__startswith=f'{source_id}::')
                  .delete())
    if deleted:
        logger.info("Removed %d stale chunks for %s/%s", deleted, doc_type, source_id)

    chunks = chunk_text(content)
    docs: list[KnowledgeDocument] = []
    for i, chunk in enumerate(chunks):
        docs.append(ingest_document(
            title=f'{title} (part {i + 1}/{len(chunks)})' if len(chunks) > 1 else title,
            content=chunk,
            doc_type=doc_type,
            source_id=f'{source_id}::chunk-{i}',
            metadata={**(metadata or {}), 'parent': source_id, 'chunk_index': i,
                      'chunk_count': len(chunks)},
        ))
    logger.info("Ingested %s/%s as %d chunk(s)", doc_type, source_id, len(docs))
    return docs


def ingest_doctor(doctor) -> KnowledgeDocument:
    """Embed/index a single doctor profile into the knowledge base.

    Idempotent: re-running updates the existing row (matched on doc_type +
    source_id=doctor.pk), so call it whenever a doctor is created or edited.
    """
    specialty_name = doctor.specialty.name if doctor.specialty_id else 'General Practice'
    content = (
        f"Dr. {doctor.user.get_full_name()} is a {specialty_name} "
        f"at {doctor.hospital}. {doctor.bio} "
        f"Languages: {doctor.languages}. "
        f"Experience: {doctor.years_experience} years. "
        f"Consultation fee: ${doctor.consultation_fee}."
    )
    return ingest_document(
        title=f"Dr. {doctor.user.get_full_name()}",
        content=content,
        doc_type=KnowledgeDocument.DocType.DOCTOR_PROFILE,
        source_id=str(doctor.pk),
        metadata={
            'doctor_id': doctor.pk,
            'specialty': specialty_name,
            'hospital': doctor.hospital,
            'is_available': doctor.is_available,
        },
    )


def ingest_doctor_profiles():
    """Index all doctor profiles into the knowledge base for RAG search."""
    from apps.doctors.models import Doctor

    doctors = Doctor.objects.select_related('user', 'specialty').all()
    for doctor in doctors:
        ingest_doctor(doctor)
    logger.info("Indexed %d doctor profiles", doctors.count())


def remove_doctor(doctor_pk) -> int:
    """Remove a doctor's profile from the knowledge base. Returns rows deleted."""
    deleted, _ = KnowledgeDocument.objects.filter(
        doc_type=KnowledgeDocument.DocType.DOCTOR_PROFILE,
        source_id=str(doctor_pk),
    ).delete()
    logger.info("Removed doctor pk=%s from KB (%d row(s))", doctor_pk, deleted)
    return deleted


def embedded_doctor_ids() -> set[int]:
    """Return the set of Doctor pks currently embedded in the knowledge base."""
    ids = set()
    for s in (KnowledgeDocument.objects
              .filter(doc_type=KnowledgeDocument.DocType.DOCTOR_PROFILE)
              .values_list('source_id', flat=True)):
        try:
            ids.add(int(s))
        except (TypeError, ValueError):
            continue
    return ids


def remove_document(doc_type: str, parent_source_id: str) -> int:
    """Remove an ingested document (all its chunks) from the knowledge base.

    Matches both a single-row doc (source_id == parent) and chunked docs
    (source_id like "<parent>::chunk-N"). Returns rows deleted.
    """
    from django.db.models import Q
    deleted, _ = (KnowledgeDocument.objects
                  .filter(doc_type=doc_type)
                  .filter(Q(source_id=parent_source_id) |
                          Q(source_id__startswith=f'{parent_source_id}::'))
                  .delete())
    logger.info("Removed document %s/%s from KB (%d row(s))",
                doc_type, parent_source_id, deleted)
    return deleted


def semantic_search(query: str, doc_type: str | None = None, top_k: int = 5,
                    doc_types: list[str] | None = None):
    """Return top-k KnowledgeDocuments closest to the query embedding.

    Filter by a single `doc_type`, a list of `doc_types`, or neither (search all).
    """
    from pgvector.django import CosineDistance

    query_embedding = embed_text(query)
    qs = KnowledgeDocument.objects.filter(embedding__isnull=False)
    if doc_type:
        qs = qs.filter(doc_type=doc_type)
    elif doc_types:
        qs = qs.filter(doc_type__in=doc_types)
    return (
        qs.annotate(distance=CosineDistance('embedding', query_embedding))
        .order_by('distance')[:top_k]
    )
