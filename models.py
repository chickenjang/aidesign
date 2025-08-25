# models.py: Building 클래스 정의

from typing import Tuple

class Building:
    def __init__(self, name: str, width: float, height: float):
        self.name = name
        self.width = width
        self.height = height
        self.x = None
        self.y = None
        self.color = self._get_building_color()
    
    def _get_building_color(self):
        color_map = {
            'Production': '#FF6B6B',
            'Admin': '#4ECDC4', 'UT': '#45B7D1',
            '신뢰성시험동': '#96CEB4', '폐기물보관장': '#FFEAA7',
            '위험물보관장': '#DDA0DD', '오/폐수처리장': '#98D8C8',
            'CESS Control': '#F7DC6F', 'SRP Control': '#BB8FCE',
            'Substation': '#F39C12', 'Guide': '#E74C3C',
            'Parking': '#A9CCE3'
        }
        for key in color_map:
            if key in self.name:
                return color_map[key]
        return '#BDC3C7'
    
    def get_coords(self) -> Tuple[float, float, float, float]:
        return self.x, self.y, self.x + self.width, self.y + self.height
