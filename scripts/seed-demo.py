"""Dane demonstracyjne do screenshotów: python scripts/seed-demo.py (backend musi działać)."""
import io, random
import requests
from PIL import Image, ImageDraw

API = 'http://127.0.0.1:8000/api'
tok = requests.post(f'{API}/auth/dev-login', json={'email': 'anna.kowalska@budimex-demo.pl', 'name': 'Anna Kowalska'}).json()['token']
H = {'Authorization': f'Bearer {tok}'}
def post(path, **kw): r = requests.post(API + path, headers=H, **kw); r.raise_for_status(); return r.json()

def floorplan(w=1600, h=1100):
    im = Image.new('RGB', (w, h), 'white'); d = ImageDraw.Draw(im)
    d.rectangle([60, 60, w-60, h-60], outline='#222', width=10)
    for x in (520, 1040): d.line([x, 60, x, 700], fill='#222', width=6)
    d.line([60, 700, w-60, 700], fill='#222', width=6)
    for x in (300, 800, 1300): d.line([x, 700, x, h-60], fill='#222', width=6)
    for x, y in ((470, 700), (990, 700), (1500, 700)): d.rectangle([x, y-6, x+70, y+6], fill='white')
    d.text((260, 360), 'POKOJ 1', fill='#666'); d.text((760, 360), 'SALON', fill='#666'); d.text((1280, 360), 'KUCHNIA', fill='#666')
    d.text((700, 850), 'KORYTARZ', fill='#666')
    return im

def photo(color):
    im = Image.new('RGB', (900, 675), color); d = ImageDraw.Draw(im)
    random.seed(color)
    for _ in range(40): x, y = random.randint(0, 800), random.randint(0, 600); d.ellipse([x, y, x+90, y+60], fill=tuple(max(0, c-25) for c in im.getpixel((10, 10))))
    return im
def png(im, fmt='JPEG'):
    b = io.BytesIO(); im.save(b, fmt); return b.getvalue()

p = post('/projects/', json={'name': 'Osiedle Zielone Tarasy, budynek B', 'address': 'ul. Słoneczna 14, 02-495 Warszawa',
    'investor': 'Zielone Tarasy Sp. z o.o.', 'contractor': 'Budimex Wnętrza S.A.', 'inspection_date': '2026-11-12', 'author': 'Anna Kowalska'})
plan = post(f"/projects/{p['id']}/plans", data={'name': 'Parter – lokal 12', 'source_filename': 'parter.pdf'},
            files={'image': ('plan.png', png(floorplan(), 'PNG'), 'image/png')})
items = [(0.22, 0.30, 'Budowlana', 'Pęknięcie tynku na ścianie północnej, ok. 40 cm.'),
         (0.50, 0.28, 'Elektryczna', 'Brak osłony gniazda 230 V przy oknie.'),
         (0.80, 0.30, 'Sanitarna', 'Nieszczelny syfon pod zlewem, ślady wilgoci.'),
         (0.18, 0.85, 'Budowlana', 'Zarysowana posadzka przy wejściu do pokoju.'),
         (0.62, 0.88, 'Meble/wyposażenie', 'Drzwi szafy nie domykają się, wymagają regulacji zawiasów.'),
         (0.90, 0.85, 'Instalacje budynkowe', 'Kratka wentylacyjna bez zamocowania.')]
ds = []
for i, (x, y, t, desc) in enumerate(items):
    ds.append(post(f"/projects/{p['id']}/defects", json={'plan_id': plan['id'], 'x': x, 'y': y, 'type': t, 'description': desc,
                   'due_mode': 'data' if i % 2 else 'umowa', 'due_date': '2026-12-05' if i % 2 else None, 'zoom': 0.3}))
for d, c in zip(ds[:4], ('#8d8579', '#7d8a93', '#8a7d7d', '#7d8a7f')):
    post(f"/defects/{d['id']}/photos", data={'kind': 'before'}, files={'file': ('b.jpg', png(photo(c)), 'image/jpeg')})
for d in ds[:2]:
    post(f"/defects/{d['id']}/photos", data={'kind': 'after'}, files={'file': ('a.jpg', png(photo('#a9b8a3')), 'image/jpeg')})
post('/projects/', json={'name': 'Biurowiec Nowa Stacja, piętra 3–5', 'address': 'al. Jerozolimskie 181, Warszawa', 'investor': 'Nowa Stacja REIT', 'contractor': 'Skanska', 'inspection_date': '2026-10-28', 'author': 'Anna Kowalska'})
print('OK', p['id'], plan['id'])
