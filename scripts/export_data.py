"""Export the thesis GPR backend to static JSON for the front end.

Usage:
    python scripts/export_data.py /path/to/dev2/gpr_index public/data

Always writes (kinetic pillar):
    index.json   small, eager  — dates, totals, all-9 index, per-theme counts
    combos.json  lazy          — 511 kinetic OR-combination counts

Additionally writes IF the matching backend parquet exists (produced by
scripts/04_build_pillars_and_cube.py):
    combos_hybrid.json   hybrid pillar OR-combinations (63)
    combos_geo.json      geoeconomic pillar OR-combinations (127)
    country_cube.json    per-country daily total + kinetic-union counts
"""
import sys, os, json
import pandas as pd
import pyarrow.parquet as pq

THEME_ORDER = ['DRONES','KIDNAP','TERROR','BORDER','ARMEDCONFLICT',
               'PEACEKEEPING','WEAPON','UNREST_BELLIGERENT','WAR']  # bitmask order
LIFTS = {'DRONES':113,'KIDNAP':113,'TERROR':81,'BORDER':60,'ARMEDCONFLICT':44,
         'PEACEKEEPING':40,'WEAPON':39,'UNREST_BELLIGERENT':39,'WAR':28}
HYBRID_ORDER = ['CYBER_ATTACK','PROPAGANDA','ELECTION_FRAUD','INTERNET_BLACKOUT','HACKING','DISINFORMATION']
GEO_ORDER = ['SANCTIONS','ECON_BOYCOTT','ECON_TARIFFS','TRADE_DISPUTE','EMBARGO','EXPORT_CONTROL','ASSET_FREEZE']


def _write(out, name, obj):
    with open(os.path.join(out, name), 'w') as f:
        json.dump(obj, f, separators=(',', ':'))
    print(f'wrote {name}: {os.path.getsize(os.path.join(out, name))/1e6:.2f} MB')


def _aligned(df, dates, col):
    """Return df[col] reindexed onto the canonical date axis (missing -> 0)."""
    s = df.set_index(df['date'].dt.strftime('%Y-%m-%d'))[col]
    return s.reindex(dates).fillna(0).astype(int).tolist()


def export_pillar(proc, out, fname, order, n_themes, outname, dates):
    path = os.path.join(proc, fname)
    if not os.path.exists(path):
        print(f'skip {outname}: {fname} not found (run 04_build_pillars_and_cube.py)')
        return
    m = pd.read_parquet(path); m['date'] = pd.to_datetime(m['date'])
    obj = {
        'meta': {'themeOrder': order, 'n': n_themes},
        'total': _aligned(m, dates, 'total_articles'),
        'or': {str(mask): _aligned(m, dates, f'or_{mask}') for mask in range(1, 1 << n_themes)},
    }
    _write(out, outname, obj)


def export_source_cube(proc, out, dates):
    path = os.path.join(proc, 'source_cube.parquet')
    if not os.path.exists(path):
        print('skip source_cube.json: source_cube.parquet not found')
        return
    c = pd.read_parquet(path); c['date'] = pd.to_datetime(c['date'])
    sources = sorted(c['source'].unique())
    total, kin_or = {}, {}
    for s in sources:
        sub = c[c['source'] == s]
        total[s] = _aligned(sub, dates, 'total_articles')
        kin_or[s] = _aligned(sub, dates, 'kin_or')
    obj = {'sources': sources, 'total': total, 'kinOr': kin_or}
    _write(out, 'source_cube.json', obj)


def main(backend, out):
    proc = os.path.join(backend, 'data', 'processed')
    os.makedirs(out, exist_ok=True)
    fi = pd.read_parquet(os.path.join(proc, 'full_index.parquet')); fi['date'] = pd.to_datetime(fi['date'])
    dates = fi['date'].dt.strftime('%Y-%m-%d').tolist()
    mat = pq.read_table(os.path.join(proc, 'per_theme_matrix.parquet')).to_pandas()
    mat['date'] = pd.to_datetime(mat['date']); mat = mat.sort_values('date').reset_index(drop=True)
    pti = pd.read_parquet(os.path.join(proc, 'per_theme_index.parquet'))
    assert mat['date'].dt.strftime('%Y-%m-%d').tolist() == dates, 'date misalignment'

    index = {
        'meta': {'themeOrder': THEME_ORDER, 'lifts': LIFTS, 'start': dates[0], 'end': dates[-1],
                 'n': len(dates), 'source': 'GDELT GKG - G20 outlets - kinetic-curated pillar',
                 'builtFrom': 'full_index.parquet + per_theme_matrix.parquet',
                 'hybridOrder': HYBRID_ORDER, 'geoOrder': GEO_ORDER},
        'dates': dates,
        'total': mat['total_articles'].astype(int).tolist(),
        'or511': mat['or_511'].astype(int).tolist(),
        'singles': {t: pti[f'{t}_articles'].astype(int).tolist() for t in THEME_ORDER},
        'avgNegative': [round(x, 4) for x in fi['avg_negative_score'].tolist()],
    }
    combos = {str(m): mat[f'or_{m}'].astype(int).tolist() for m in range(1, 512)}
    _write(out, 'index.json', index)
    _write(out, 'combos.json', combos)

    # optional pillars + country cube (only if the backend produced them)
    export_pillar(proc, out, 'pillar_hybrid_matrix.parquet', HYBRID_ORDER, 6, 'combos_hybrid.json', dates)
    export_pillar(proc, out, 'pillar_geo_matrix.parquet', GEO_ORDER, 7, 'combos_geo.json', dates)
    export_source_cube(proc, out, dates)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('usage: python export_data.py <backend dir> <out dir>')
    main(sys.argv[1], sys.argv[2])
