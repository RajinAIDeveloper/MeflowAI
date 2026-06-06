"""
Management command: ingest_docs
Ingest knowledge documents (hospital policies, medical FAQs, department info,
symptom guides) into the pgvector knowledge base so AI triage can use them.

Long documents are chunked automatically (see apps/rag/chunking.py).

Usage:
    # one file, explicit type + title
    python manage.py ingest_docs docs/er_policy.md --type hospital_policy --title "ER Policy"

    # a whole folder (each .txt/.md/.pdf becomes a document; title = filename)
    python manage.py ingest_docs docs/faqs/ --type medical_faq

Supported types: hospital_policy | medical_faq | department_info | doctor_profile
Supported files: .txt, .md  (.pdf requires `pip install pypdf`)
"""
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.rag.ingest import ingest_text
from apps.rag.models import KnowledgeDocument

VALID_TYPES = [c[0] for c in KnowledgeDocument.DocType.choices]
TEXT_SUFFIXES = {'.txt', '.md', '.markdown'}


class Command(BaseCommand):
    help = 'Ingest document files into the pgvector knowledge base (chunked).'

    def add_arguments(self, parser):
        parser.add_argument('path', help='A file or a directory of documents.')
        parser.add_argument('--type', dest='doc_type', default='medical_faq',
                            help=f'Document type. One of: {", ".join(VALID_TYPES)}')
        parser.add_argument('--title', default=None,
                            help='Title (single file only; defaults to the filename).')

    def handle(self, *args, **options):
        doc_type = options['doc_type']
        if doc_type not in VALID_TYPES:
            raise CommandError(f'--type must be one of: {", ".join(VALID_TYPES)}')

        path = Path(options['path']).expanduser()
        if not path.exists():
            raise CommandError(f'Path not found: {path}')

        files = [path] if path.is_file() else sorted(
            p for p in path.rglob('*')
            if p.suffix.lower() in TEXT_SUFFIXES | {'.pdf'}
        )
        if not files:
            raise CommandError(f'No .txt/.md/.pdf files found under {path}')

        total_chunks = 0
        for f in files:
            try:
                content = self._read(f)
            except Exception as exc:
                self.stderr.write(self.style.WARNING(f'Skipped {f.name}: {exc}'))
                continue
            if not content.strip():
                self.stderr.write(self.style.WARNING(f'Skipped {f.name}: empty'))
                continue

            title = options['title'] if (path.is_file() and options['title']) else f.stem.replace('_', ' ').title()
            source_id = _slug(f.stem)
            docs = ingest_text(title=title, content=content, doc_type=doc_type,
                               source_id=source_id, metadata={'filename': f.name})
            total_chunks += len(docs)
            self.stdout.write(f'  {f.name:40} -> {len(docs):3} chunk(s)  [{doc_type}]')

        self.stdout.write(self.style.SUCCESS(
            f'Done: {len(files)} file(s), {total_chunks} chunk(s) indexed.'))

    def _read(self, f: Path) -> str:
        if f.suffix.lower() == '.pdf':
            try:
                from pypdf import PdfReader
            except ImportError:
                raise RuntimeError('PDF support needs pypdf: pip install pypdf')
            reader = PdfReader(str(f))
            return '\n\n'.join((page.extract_text() or '') for page in reader.pages)
        return f.read_text(encoding='utf-8', errors='ignore')


def _slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or 'doc'
