"""Reproduce findings from LOCAL-LLM-REVIEW-2026-10-01.md without network calls.

Run from the repository root using:
    .venv/bin/python docs/reviews/local-runtime-repro-2026-10-01.py

Uses existing test fixtures and temporary workspaces; requires development dependencies.
No production workspace is opened. The JSON reports current behavior, including defects.
"""
import ast
from collections import Counter
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
from pathlib import Path
import re
import tempfile
import threading
import sys
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import httpx

from byeori.local.cli import main as cli_main, recorded_verdicts, review_markdown
from byeori.local.jobs import QuestionJobs
from byeori.local.llm import Generation, ModelError, OllamaBackend
from byeori.local.service import LocalService, parse_frontmatter
from byeori.local.store import LocalStore, digest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tests'))
spec = importlib.util.spec_from_file_location('review_fixtures', REPO / 'tests/test_local_integrity.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
results = {}


def service_at(root, *, xml=fixtures.TEI, model=None, lookup=None):
    root.mkdir(parents=True, exist_ok=True)
    pdf = root / 'input.pdf'
    pdf.write_bytes(b'%PDF-1.7\nreview fixture')
    store = LocalStore(root / 'data')
    paper = store.add(pdf, 'Review fixture')
    return LocalService(store, model or fixtures.Model(), fixtures.Extractor(xml), lookup=lookup), paper['paper_id']


with tempfile.TemporaryDirectory(prefix='byeori-review-') as directory:
    root = Path(directory)

    service, pid = service_at(root / 'batch')
    for index in range(100):
        pdf = root / 'batch' / f'{index}.pdf'
        pdf.write_bytes(f'%PDF-1.7\nfixture {index}'.encode())
        service.store.add(pdf)
    first = service.process_all()
    with service.store.db() as db:
        total = db.execute('SELECT count(*) FROM papers').fetchone()[0]
        notes = db.execute('SELECT count(*) FROM notes').fetchone()[0]
    second = service.process_all()
    results['batch_100_limit'] = {'registered': total, 'published': notes,
        'first_processed': first['processed'], 'second_processed': second['processed'],
        'pending_reported': len(service.pending())}

    service, pid = service_at(root / 'metadata', xml=fixtures.NO_YEAR_TEI,
                              lookup=fixtures.lookup_for([fixtures.WORK]))
    service.process(pid)
    before, _ = parse_frontmatter(service.store.note(pid)['text'])
    service.lookup = None
    refresh = service.refresh_metadata(pid)
    after, _ = parse_frontmatter(service.store.note(pid)['text'])
    with service.store.db() as db:
        indexed_year = db.execute('SELECT year FROM docs').fetchone()[0]
    results['metadata_regression'] = {'before_year': before['year'], 'after_year': after['year'],
        'before_work_ids': before['work_ids'], 'after_work_ids': after['work_ids'],
        'changed': refresh['changed'], 'stem': refresh['stem'], 'indexed_year': indexed_year}

    service, pid = service_at(root / 'receipt')
    with patch.object(service.store, '_record_success', side_effect=RuntimeError('injected publish failure')):
        try:
            service.process(pid)
        except RuntimeError:
            pass
    job = service.store.jobs()[0]
    receipt = json.loads(service.store.path(f"runs/{job['job_id']}/receipt.json").read_text())
    results['receipt_contradiction'] = {'job_status': job['status'], 'receipt_outcome': receipt['outcome'],
                                      'active_notes': len(service.store.papers_with_notes())}

    service, pid = service_at(root / 'hash')
    service.process(pid)
    note = service.store.note(pid)
    note_path = service.store.path(note['path'])
    note_path.write_text(note['text'].replace('28.4 BLEU', '99.9 BLEU'))
    try:
        service.store.note(pid)
        read_blocked = False
    except ValueError:
        read_blocked = True
    results['hash_integrity'] = {'check_problems': service.store.integrity_problems(),
        'read_blocked': read_blocked,
        'recorded_hash_matches_actual': note['note_sha256'] == digest(note_path.read_bytes())}

    service, pid = service_at(root / 'citation')
    service.process(pid)
    service.backend.answer = 'Claim without a citation. A second claim cites an unshown paragraph. [E1-P0002]'
    answer = service.ask('What does it report?', pid)
    results['answer_coverage'] = {'answer_status': answer['answer_status'],
        'note_cites_P0002': '[P0002]' in service.store.note(pid)['text'],
        'returned_block_ids': answer['citations'][0]['block_ids'] if answer['citations'] else [],
        'reason': answer.get('reason')}

    class SkipModel(fixtures.PartsModel):
        def generate(self, system, prompt, *, think=None):
            shown = re.findall(r'\[(P\d+)\]', prompt)
            if system.startswith('Digest one part'):
                if 'P0007' in shown:
                    raise ModelError('Model did not finish normally; incomplete output was not published')
                return Generation('- a reported value ' + ' '.join(f'[{i}]' for i in shown),
                                  self.model, 100, 50, 'stop')
            return Generation(fixtures.note_text('P0007'), self.model, 100, 200, 'stop')

    service, pid = service_at(root / 'skip', xml=fixtures.long_tei(20), model=SkipModel())
    try:
        processed = service.process(pid)
    except RuntimeError:
        job = service.store.jobs()[0]
        processed = {'status': job['status'], 'coverage': json.loads(
            service.store.path(f"runs/{job['job_id']}/receipt.json").read_text())['coverage']}
    results['skipped_block_citation'] = {'status': processed['status'],
        'blocks_skipped': processed['coverage']['blocks_skipped'],
        'published_note_cites_skipped': pid in service.store.papers_with_notes()}

    store = LocalStore(root / 'queue-race')
    class ImmediateService:
        def __init__(self, store):
            self.store = store
        def ask(self, question, paper_id=None):
            return {'answer_status': 'answered', 'answer': question}
    manager = QuestionJobs(ImmediateService(store))
    original_claim = store.claim_question
    no_job_read = threading.Event()
    allow_exit = threading.Event()
    def delayed_empty_claim(owner_token=None):
        job = original_claim(owner_token)
        if job is None:
            no_job_read.set()
            allow_exit.wait(5)
        return job
    with patch.object(store, 'claim_question', side_effect=delayed_empty_claim):
        manager._ensure_worker()
        assert no_job_read.wait(5)
        with ThreadPoolExecutor() as executor:
            incoming = executor.submit(manager.submit, 'Arrives while the worker exits')
            allow_exit.set()
            job = incoming.result(5)
        manager.wait(job['job_id'], 5)
    results['queue_worker_exit_race'] = {'job_status': store.job(job['job_id'])['status'],
                                       'worker_alive': bool(manager._worker and manager._worker.is_alive())}

    store = LocalStore(root / 'two-workers')
    entered = [threading.Event(), threading.Event()]
    release = threading.Event()
    class BlockingService(ImmediateService):
        def __init__(self, store, index):
            super().__init__(store)
            self.index = index
        def ask(self, question, paper_id=None):
            entered[self.index].set()
            release.wait(5)
            return super().ask(question, paper_id)
    first_manager = QuestionJobs(BlockingService(store, 0))
    second_manager = QuestionJobs(BlockingService(store, 1))
    j1 = first_manager.submit('First')
    assert entered[0].wait(5)
    j2 = second_manager.submit('Second')
    concurrent = entered[1].wait(1)
    results['workspace_question_concurrency'] = {'both_running': concurrent,
        'statuses': [store.job(j['job_id'])['status'] for j in (j1, j2)]}
    release.set()
    first_manager.wait(j1['job_id'], 5)
    second_manager.wait(j2['job_id'], 5)

    sheet = {'stem': 'example', 'paper_id': 'example-paper', 'revision_id': 'old', 'note_sha256': 'a'*64,
             'fields': {}, 'blocks_total': 2,
             'claims': [{'heading': '4. Key Results and Benchmarks', 'claim': 'The score is 28.4.',
                         'cited': ['P0001'], 'sources': []}]}
    path = root / 'review.md'
    path.write_text(review_markdown(sheet).replace('- 판정:', '- 판정: 인용틀림'))
    saved = recorded_verdicts(path)
    sheet['revision_id'] = 'new'
    sheet['claims'][0]['cited'] = ['P0002']
    results['verdict_survives_changed_evidence'] = '- 판정: 인용틀림' in review_markdown(sheet, saved)

    service, pid = service_at(root / 'review-table')
    service.backend.answer = fixtures.note_text()
    service.backend.answer = service.backend.answer.replace('## 4. Key Results and Benchmarks\n\n',
        '## 4. Key Results and Benchmarks\n\n| Metric | Value |\n| --- | --- |\n| Accuracy | 999% [P0001] |\n\n')
    service.process(pid)
    sheet = service.review_sheet(pid)
    results['table_claim_review'] = {'table_published': '999%' in service.store.note(pid)['text'],
                                    'table_claim_in_review': any('999%' in c['claim'] for c in sheet['claims'])}

    service, pid = service_at(root / 'cli-failure')
    output = StringIO()
    with patch('byeori.local.cli.build_service', return_value=service), \
            patch.object(service, 'ask', side_effect=ModelError('injected model failure')), \
            redirect_stdout(output):
        exit_code = cli_main(['ask', 'A failing question', '--paper', pid])
    results['cli_failed_question_exit'] = {'exit_code': exit_code,
                                          'job_status': json.loads(output.getvalue())['status']}

    calls = []
    def cloud_handler(request):
        calls.append(request.url.path)
        if request.method == 'GET':
            return httpx.Response(200, json={'models': [{'name': 'example:cloud', 'digest': 'fixture',
                'remote_model': 'example', 'remote_host': 'https://ollama.com:443'}]})
        return httpx.Response(200, json={'done': True, 'done_reason': 'stop',
            'message': {'content': 'Mock cloud answer'}, 'prompt_eval_count': 10, 'eval_count': 3})
    backend = OllamaBackend('example:cloud', transport=httpx.MockTransport(cloud_handler))
    doctor = backend.doctor()
    try:
        backend.generate('Answer briefly', 'Hello')
        blocked = False
    except ModelError:
        blocked = True
    results['cloud_model_guard'] = {'model_available': doctor['model_available'],
        'model_locality': doctor['model_locality'], 'blocked': blocked, 'requests': calls}

tree = ast.parse((REPO / 'src/byeori/local/service.py').read_text())
definitions = Counter(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)))
results['duplicate_top_level_definitions'] = {k:v for k,v in definitions.items() if v>1}

count = Counter()
for path in (REPO / 'docs/evaluation').glob('*.md'):
    if path.name == 'README.md':
        continue
    text = path.read_text()
    count['papers'] += 1
    count['claims'] += len(re.findall(r'^### \d+\.', text, re.M))
    for verdict in re.findall(r'^- 판정: (\S.*)$', text, re.M):
        count[verdict.strip()] += 1
    count['supported'] += len(re.findall(r'^- 1차 검사: \*\*supported\*\*', text, re.M))
results['evaluation_recount'] = dict(count)
print(json.dumps(results, ensure_ascii=False, indent=2))
