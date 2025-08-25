# config.py: 상수와 기본값 정의

SETBACK = 20
GRID_SIZE = 100
BUILDING_SPACING = 10

DEFAULT_VALUES = {
    'site_size': (800, 600),
    'prod_size': (300, 150),
    'annex_sizes': {
        'Admin': (50, 50),
        'UT': (40, 40),
        '폐기물보관장': (20, 20),
        '신뢰성시험동': (30, 30),
        '위험물보관장': (10, 10),
        '오/폐수처리장': (20, 20),
        'CESS Control': (10, 10),
        'SRP Control': (5, 5)
    },
    'main_guide_size': (37, 22),
    'other_guide_size': (10, 10),
    'gate_count': 2,
    'gates': [(200, 600), (0, 200)],
    'substation_size': (50, 50),
    'parking_count': 150
}
 