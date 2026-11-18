"""Fabryki danych testowych i drobne narzędzia współdzielone przez testy."""

import io
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

PROJECT = {
    'name': 'Osiedle Zielone', 'address': 'ul. Polna 1, Warszawa', 'investor': 'Inwestor SA',
    'contractor': 'Budex', 'inspection_date': '2026-11-17', 'author': 'Jan Kowalski',
}
PASSWORD = 'Dobre-haslo-123'


def image_file(fmt='JPEG', size=(400, 300), name=None, content_type=None):
    buf = io.BytesIO()
    Image.new('RGB', size, 'white').save(buf, fmt)
    ext = fmt.lower().replace('jpeg', 'jpg')
    return SimpleUploadedFile(name or f'plik.{ext}', buf.getvalue(), content_type=content_type or f'image/{fmt.lower()}')


def jpeg(w=400, h=300):
    return image_file('JPEG', (w, h))


def pdf_file(body=b'%PDF-1.4 test'):
    return SimpleUploadedFile('r.pdf', body, content_type='application/pdf')


def post_json(client, url, body=None, **kw):
    return client.post(url, json.dumps(body or {}), content_type='application/json', **kw)


def patch_json(client, url, body):
    return client.patch(url, json.dumps(body), content_type='application/json')


def make_project(api, **overrides):
    r = post_json(api, '/api/projects/', {**PROJECT, **overrides})
    assert r.status_code == 201, r.content
    return r.json()


def make_plan(api, project_id, name='Parter'):
    r = api.post(f'/api/projects/{project_id}/plans', {'name': name, 'image': jpeg()})
    assert r.status_code == 201, r.content
    return r.json()


def defect_body(plan_id, **kw):
    return {'plan_id': plan_id, 'x': .5, 'y': .5, 'type': 'Budowlana', 'description': 'Rysa na ścianie',
            'due_mode': 'umowa', **kw}


def make_defect(api, project_id, plan_id, **kw):
    return post_json(api, f'/api/projects/{project_id}/defects', defect_body(plan_id, **kw))


def add_photo(api, defect_id, kind='before'):
    return api.post(f'/api/defects/{defect_id}/photos', {'kind': kind, 'file': jpeg()})
