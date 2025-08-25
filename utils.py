# utils.py: 유틸리티 함수 (거리 계산, 주차 계산 등)

import numpy as np
from typing import List, Dict, Tuple, Optional
from config import SETBACK, BUILDING_SPACING  # config에서 import
from shapely.geometry import Polygon, box  # 추가 import

def is_building_inside_polygon(building_x: float, building_y: float, building_w: float, building_h: float, site_polygon: Polygon) -> bool:
    """건물 직사각형이 부지 폴리곤 내부에 완전히 포함되는지 검사"""
    building_rect = box(building_x, building_y, building_x + building_w, building_y + building_h)
    return site_polygon.contains(building_rect)  # 건물 전체가 내부에 있음

def calculate_parking_area(parking_count: int) -> Tuple[float, Dict[str, int]]:
    """주차댓수를 기준으로 주차장 면적을 계산"""
    general_count = int(parking_count * 0.61)
    extended_count = int(parking_count * 0.30)
    disabled_count = int(parking_count * 0.04)
    eco_count = int(parking_count * 0.05)
    
    total_assigned = general_count + extended_count + disabled_count + eco_count
    if total_assigned != parking_count:
        general_count += (parking_count - total_assigned)
    
    total_vehicle_area = (
        general_count * 20.0 + extended_count * 20.8 + 
        disabled_count * 26.4 + eco_count * 20.0
    )
    
    landscape_area = total_vehicle_area * 0.10
    total_parking_area = total_vehicle_area + landscape_area
    
    breakdown = {
        'general': general_count, 'extended': extended_count,
        'disabled': disabled_count, 'eco': eco_count,
        'total_vehicle_area': total_vehicle_area,
        'landscape_area': landscape_area, 'total_area': total_parking_area
    }
    
    return total_parking_area, breakdown

def calculate_parking_dimensions(total_area: float) -> Tuple[float, float]:
    """주차장을 2개의 동일한 직사각형으로 나누어 각각의 크기 계산"""
    each_area = total_area / 2
    short_side = 35.2
    long_side = each_area / short_side
    return short_side, long_side

def get_production_areas(prod_x: float, prod_y: float, prod_w: float, prod_h: float, orientation: str) -> Dict:
    """생산동을 3등분하여 Electrode, Assembly, Formation 영역의 중심점을 반환"""
    if orientation == "horizontal":
        section_width = prod_w / 3
        return {
            'electrode': (prod_x + section_width/2, prod_y + prod_h/2),
            'assembly': (prod_x + section_width + section_width/2, prod_y + prod_h/2),
            'formation': (prod_x + 2*section_width + section_width/2, prod_y + prod_h/2)
        }
    else:
        section_height = prod_h / 3
        return {
            'electrode': (prod_x + prod_w/2, prod_y + section_height/2),
            'assembly': (prod_x + prod_w/2, prod_y + section_height + section_height/2),
            'formation': (prod_x + prod_w/2, prod_y + 2*section_height + section_height/2)
        }

def get_main_gate(gates: List[Tuple[float, float]]) -> Tuple[float, float]:
    """y좌표가 가장 작은 출입구를 Main 출입구로 반환"""
    return min(gates, key=lambda gate: gate[1])

def manhattan_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """맨해튼 거리 계산"""
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def check_setback_distance(x1: float, y1: float, w1: float, h1: float,
                           x2: float, y2: float, w2: float, h2: float,
                           min_distance: float = SETBACK) -> bool:
    return (x1 + w1 + min_distance <= x2 or x2 + w2 + min_distance <= x1 or
            y1 + h1 + min_distance <= y2 or y2 + h2 + min_distance <= y1)

def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def get_production_short_edge_centers(prod_x: float, prod_y: float, 
                                      prod_w: float, prod_h: float) -> List[Tuple[float, float]]:
    if prod_w > prod_h:
        return [(prod_x, prod_y + prod_h / 2), (prod_x + prod_w, prod_y + prod_h / 2)]
    else:
        return [(prod_x + prod_w / 2, prod_y), (prod_x + prod_w / 2, prod_y + prod_h)]

def get_sides_without_gates(gates: List[Tuple[float, float]], site_w: float, site_h: float) -> List[str]:
    """출입구가 없는 변을 찾는 함수"""
    gate_tolerance = 50
    has_gate = {'top': False, 'bottom': False, 'left': False, 'right': False}
    
    for gate_x, gate_y in gates:
        if abs(gate_y - site_h) <= gate_tolerance:
            has_gate['top'] = True
        elif abs(gate_y) <= gate_tolerance:
            has_gate['bottom'] = True
        elif abs(gate_x) <= gate_tolerance:
            has_gate['left'] = True
        elif abs(gate_x - site_w) <= gate_tolerance:
            has_gate['right'] = True
    
    return [side for side, has in has_gate.items() if not has]

def get_annex_group_center(annex_positions: Dict, annex_buildings: List) -> Tuple[float, float]:
    """부속동 그룹의 중심점을 계산하는 함수"""
    if not annex_positions or not annex_buildings:
        return (0, 0)
    
    centers = []
    for building in annex_buildings:
        if building.name in annex_positions:
            pos = annex_positions[building.name]
            centers.append((pos[0] + building.width / 2, pos[1] + building.height / 2))
    
    if not centers:
        return (0, 0)
    
    avg_x = sum(center[0] for center in centers) / len(centers)
    avg_y = sum(center[1] for center in centers) / len(centers)
    return (avg_x, avg_y)

def is_valid_substation_position(sub_x: float, sub_y: float, substation,
                                 prod_x: float, prod_y: float, prod_w: float, prod_h: float,
                                 annex_positions: Dict, annex_buildings: List,
                                 guide_positions: Dict, guide_buildings: List,
                                 parking_positions: Dict, parking_buildings: List) -> bool:
    """변전소 위치의 유효성을 검사하는 헬퍼 함수"""
    # 생산동과의 이격거리 검사
    if not check_setback_distance(sub_x, sub_y, substation.width, substation.height,
                                  prod_x, prod_y, prod_w, prod_h):
        return False
    
    # 다른 건물들과의 이격거리 검사
    all_buildings = [(annex_positions, annex_buildings), (guide_positions, guide_buildings), (parking_positions, parking_buildings)]
    
    for positions, buildings in all_buildings:
        for building in buildings:
            if building.name in positions:
                pos = positions[building.name]
                if not check_setback_distance(sub_x, sub_y, substation.width, substation.height,
                                              pos[0], pos[1], building.width, building.height):
                    return False
    
    return True
