# layout.py: 배치 생성 로직

import numpy as np
from typing import List, Dict, Optional, Tuple
from config import SETBACK, GRID_SIZE, BUILDING_SPACING
from models import Building
from utils import (get_annex_group_center, get_main_gate, get_sides_without_gates, is_valid_substation_position, manhattan_distance, check_setback_distance, 
                   get_production_short_edge_centers, distance, is_building_inside_polygon)
from shapely.geometry import Polygon, Point  # 추가: 다각형 처리용 및 Point

def arrange_annex_buildings_user_specified_order(annex_buildings: List[Building], side: str, 
                                                 prod_x: float, prod_y: float, prod_w: float, prod_h: float,
                                                 orientation: str, gates: List[Tuple[float, float]]) -> Tuple[Dict, float, float]:
    """사용자 지정: 고정 순서 배치 (electrode->formation 방향)"""
    main_gate = get_main_gate(gates)
    buildings_dict = {building.name: building for building in annex_buildings}
    
    # 사용자 지정 고정 순서
    user_specified_order = ['SRP Control', '위험물보관장', 'CESS Control', 'UT', '신뢰성시험동', '폐기물보관장']
    
    is_horizontal_layout = orientation == "horizontal"
    
    if is_horizontal_layout:
        total_length = sum(building.width for building in annex_buildings) + BUILDING_SPACING * (len(annex_buildings) - 1)
        max_depth = max(building.height for building in annex_buildings)
    else:
        total_length = sum(building.height for building in annex_buildings) + BUILDING_SPACING * (len(annex_buildings) - 1)
        max_depth = max(building.width for building in annex_buildings)
    
    # 가상 group_x, group_y 계산 (절대 좌표 기반 거리 비교용)
    if side == 'left':
        virtual_group_x = prod_x - total_length - SETBACK if is_horizontal_layout else prod_x - max_depth - SETBACK
        virtual_group_y = prod_y + prod_h/2 - max_depth/2 if is_horizontal_layout else prod_y + prod_h/2 - total_length/2
    elif side == 'right':
        virtual_group_x = prod_x + prod_w + SETBACK
        virtual_group_y = prod_y + prod_h/2 - max_depth/2 if is_horizontal_layout else prod_y + prod_h/2 - total_length/2
    elif side == 'top':
        virtual_group_x = prod_x + prod_w/2 - total_length/2 if is_horizontal_layout else prod_x + prod_w/2 - max_depth/2
        virtual_group_y = prod_y + prod_h + SETBACK
    else:  # bottom
        virtual_group_x = prod_x + prod_w/2 - total_length/2 if is_horizontal_layout else prod_x + prod_w/2 - max_depth/2
        virtual_group_y = prod_y - max_depth - SETBACK if is_horizontal_layout else prod_y - total_length - SETBACK
    
    # 사용자 지정 순서로 배치
    positions = {}
    cursor = 0
    
    for building_name in user_specified_order:
        if building_name in buildings_dict:
            building = buildings_dict[building_name]
            positions[building_name] = (cursor, 0) if is_horizontal_layout else (0, cursor)
            cursor += (building.width if is_horizontal_layout else building.height) + BUILDING_SPACING
    
    # Admin동과 오/폐수처리장 특별 배치
    for special_name in ['Admin', '오/폐수처리장']:
        if special_name in buildings_dict:
            building = buildings_dict[special_name]
            abs_start_pos = (virtual_group_x, virtual_group_y)
            abs_end_pos = (virtual_group_x + total_length, virtual_group_y) if is_horizontal_layout else (virtual_group_x, virtual_group_y + total_length)
            
            start_pos = (0, 0)
            end_pos = (cursor, 0) if is_horizontal_layout else (0, cursor)
            
            if special_name == 'Admin':
                # Main 출입구와의 거리 기준으로 배치
                if manhattan_distance(abs_start_pos, main_gate) <= manhattan_distance(abs_end_pos, main_gate):
                    # 시작 부분에 배치 - 다른 건물들을 뒤로 밀기
                    shift = (building.width if is_horizontal_layout else building.height) + BUILDING_SPACING
                    new_positions = {}
                    for name, pos in positions.items():
                        new_positions[name] = (pos[0] + shift, pos[1]) if is_horizontal_layout else (pos[0], pos[1] + shift)
                    positions = new_positions
                    positions[special_name] = start_pos
                    cursor += shift
                else:
                    positions[special_name] = end_pos
                    cursor += (building.width if is_horizontal_layout else building.height) + BUILDING_SPACING
            else:  # '오/폐수처리장'
                if 'Admin' in positions:
                    admin_pos = positions['Admin']
                    if admin_pos == (0, 0):
                        # Admin이 시작 부분에 있으면 오/폐수처리장은 맨 끝에
                        positions[special_name] = (cursor, 0) if is_horizontal_layout else (0, cursor)
                    else:
                        # Admin이 끝에 있으면 오/폐수처리장은 맨 시작에
                        shift = (building.width if is_horizontal_layout else building.height) + BUILDING_SPACING
                        new_positions = {}
                        for name, pos in positions.items():
                            new_positions[name] = (pos[0] + shift, pos[1]) if is_horizontal_layout else (pos[0], pos[1] + shift)
                        positions = new_positions
                        positions[special_name] = (0, 0)
                else:
                    positions[special_name] = (cursor, 0) if is_horizontal_layout else (0, cursor)
    
    return positions, total_length if is_horizontal_layout else max_depth, max_depth if is_horizontal_layout else total_length

def place_parking_lots(main_gate: Tuple[float, float], parking_buildings: List[Building], 
                       site_w: float, site_h: float) -> Dict[str, Tuple[float, float]]:
    """Main 출입구에서 대지를 바라봤을 때 앞쪽에 주차장 2개를 세로로 좌우 배치"""
    gate_x, gate_y = main_gate
    parking_1, parking_2 = parking_buildings
    
    parking_x = max(SETBACK, min(gate_x + SETBACK, site_w - SETBACK - max(parking_1.width, parking_2.width)))
    
    left_y = gate_y + SETBACK
    right_y = gate_y - SETBACK - parking_2.height
    
    if left_y < SETBACK:
        offset = SETBACK - left_y
        left_y += offset
        right_y += offset
    
    if right_y + parking_2.height > site_h - SETBACK:
        offset = (right_y + parking_2.height) - (site_h - SETBACK)
        left_y -= offset
        right_y -= offset
        
        if left_y < SETBACK:
            left_y = SETBACK
            right_y = left_y + parking_1.height + SETBACK
    
    return {'Parking_1': (parking_x, left_y), 'Parking_2': (parking_x, right_y)}

def get_buildings_positions_sizes(layout: Dict, buildings: Dict) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    positions = []
    sizes = []

    # 생산동
    prod = layout['production']
    positions.append((prod['x'], prod['y']))
    sizes.append((prod['width'], prod['height']))

    # 부속동들
    annex_positions = layout['annex_group']['positions']
    for building in buildings['annex_buildings']:
        pos = annex_positions[building.name]
        positions.append(pos)
        sizes.append((building.width, building.height))

    # 변전소
    sub = layout['substation']
    positions.append((sub['x'], sub['y']))
    sizes.append((buildings['substation'].width, buildings['substation'].height))

    # 안내동들
    for building in buildings['guide_buildings']:
        pos = layout['guides'][building.name]
        positions.append(pos)
        sizes.append((building.width, building.height))
    
    # 주차장들
    for building in buildings['parking_buildings']:
        pos = layout['parking'][building.name]
        positions.append(pos)
        sizes.append((building.width, building.height))

    return positions, sizes

def generate_all_layouts(buildings: Dict) -> Tuple[List[Dict], Dict[str, int]]:
    layouts = []
    failure_reasons = {
        'insufficient_space': 0,
        'collision': 0,
        'outside_polygon': 0,
        'no_substation_position': 0
    }
    site_shape = buildings['site_shape']
    if site_shape == '직사각형':
        site_w, site_h = buildings['site_size']
        site_polygon = None
    else:
        site_polygon = Polygon(buildings['site_size'])
        minx, miny, maxx, maxy = site_polygon.bounds
        site_w = maxx - minx
        site_h = maxy - miny
    
    prod = buildings['prod_building']
    annex_buildings = buildings['annex_buildings']
    guide_buildings = buildings['guide_buildings']
    gates = buildings['gates']
    substation = buildings['substation']
    parking_buildings = buildings['parking_buildings']
    
    main_gate = get_main_gate(gates)
    parking_positions = place_parking_lots(main_gate, parking_buildings, site_w, site_h)
    
    prod_orientations = [
        (prod.width, prod.height, False, "horizontal"),
        (prod.height, prod.width, True, "vertical")
    ]
    
    layout_id = 0
    
    for prod_w, prod_h, is_rotated, orientation in prod_orientations:
        max_prod_x = site_w - prod_w - SETBACK
        max_prod_y = site_h - prod_h - SETBACK
        
        if max_prod_x < SETBACK or max_prod_y < SETBACK:
            failure_reasons['insufficient_space'] += 1
            continue
        
        for prod_x in np.arange(SETBACK, max_prod_x + 1, GRID_SIZE):
            for prod_y in np.arange(SETBACK, max_prod_y + 1, GRID_SIZE):
                
                # 생산동이 주차장과 충돌하는지 확인
                valid_prod_position = True
                for building in parking_buildings:
                    parking_pos = parking_positions[building.name]
                    if not check_setback_distance(prod_x, prod_y, prod_w, prod_h,
                                                  parking_pos[0], parking_pos[1],
                                                  building.width, building.height):
                        valid_prod_position = False
                        failure_reasons['collision'] += 1
                        break
                
                if not valid_prod_position:
                    continue
                
                # 생산동이 부지 내부에 있는지 확인 (polygon 경우)
                if site_polygon and not is_building_inside_polygon(prod_x, prod_y, prod_w, prod_h, site_polygon):
                    failure_reasons['outside_polygon'] += 1
                    continue
                
                sides = ['top', 'bottom'] if orientation == "horizontal" else ['left', 'right']
                
                for side in sides:
                    # 부속동 배치
                    annex_positions, annex_width, annex_height = arrange_annex_buildings_user_specified_order(
                        annex_buildings, side, prod_x, prod_y, prod_w, prod_h, orientation, gates)
                    
                    # 부속동 그룹의 실제 배치 위치 계산
                    if side == 'left':
                        group_x = prod_x - annex_width - SETBACK
                        group_y = prod_y + prod_h/2 - annex_height/2
                    elif side == 'right':
                        group_x = prod_x + prod_w + SETBACK
                        group_y = prod_y + prod_h/2 - annex_height/2
                    elif side == 'top':
                        group_x = prod_x + prod_w/2 - annex_width/2
                        group_y = prod_y + prod_h + SETBACK
                    else:  # bottom
                        group_x = prod_x + prod_w/2 - annex_width/2
                        group_y = prod_y - annex_height - SETBACK
                    
                    # 부속동 그룹이 부지 경계를 벗어나는지 확인
                    if (group_x < SETBACK or group_y < SETBACK or 
                        group_x + annex_width > site_w - SETBACK or 
                        group_y + annex_height > site_h - SETBACK):
                        failure_reasons['insufficient_space'] += 1
                        continue
                    
                    # 상대 좌표를 실제 좌표로 변환
                    final_annex_positions = {name: (group_x + rel_x, group_y + rel_y) 
                                             for name, (rel_x, rel_y) in annex_positions.items()}
                    
                    # 부속동이 주차장과 충돌하는지 확인
                    valid_annex = True
                    for building in annex_buildings:
                        annex_pos = final_annex_positions[building.name]
                        if site_polygon and not is_building_inside_polygon(annex_pos[0], annex_pos[1], building.width, building.height, site_polygon):
                            valid_annex = False
                            failure_reasons['outside_polygon'] += 1
                            break
                        for parking_building in parking_buildings:
                            parking_pos = parking_positions[parking_building.name]
                            if not check_setback_distance(annex_pos[0], annex_pos[1],
                                                          building.width, building.height,
                                                          parking_pos[0], parking_pos[1],
                                                          parking_building.width, parking_building.height):
                                valid_annex = False
                                failure_reasons['collision'] += 1
                                break
                        if not valid_annex:
                            break
                    
                    if not valid_annex:
                        continue
                    
                    # 안내동 배치
                    guide_positions = {}
                    valid_guides = True
                    
                    for i, (gate_x, gate_y) in enumerate(gates):
                        if (gate_x, gate_y) == main_gate:
                            building = guide_buildings[0]
                            # 출입구 위치에 따른 건물 회전
                            if gate_x == 0 and building.width > building.height:
                                building.width, building.height = building.height, building.width
                            elif gate_y == 0 and building.width < building.height:
                                building.width, building.height = building.height, building.width
                        else:
                            other_gate_index = [g for g in gates if g != main_gate].index((gate_x, gate_y))
                            building = guide_buildings[1 + other_gate_index]
                        
                        # 안내동 위치 탐색
                        found_position = False
                        for x_offset in range(-80, 81, 10):
                            for y_offset in range(-80, 81, 10):
                                candidate_x = gate_x + x_offset
                                candidate_y = gate_y + y_offset
                                
                                # 경계 체크
                                if (candidate_x < SETBACK or candidate_y < SETBACK or
                                    candidate_x + building.width > site_w - SETBACK or
                                    candidate_y + building.height > site_h - SETBACK):
                                    failure_reasons['insufficient_space'] += 1
                                    continue
                                
                                # polygon 내부 체크
                                if site_polygon and not is_building_inside_polygon(candidate_x, candidate_y, building.width, building.height, site_polygon):
                                    failure_reasons['outside_polygon'] += 1
                                    continue
                                
                                # 모든 기존 건물들과의 충돌 체크
                                valid_position = True
                                
                                # 생산동과의 충돌 체크
                                if not check_setback_distance(candidate_x, candidate_y, building.width, building.height,
                                                              prod_x, prod_y, prod_w, prod_h):
                                    valid_position = False
                                    failure_reasons['collision'] += 1
                                
                                # 부속동들과의 충돌 체크
                                if valid_position:
                                    for annex_building in annex_buildings:
                                        annex_pos = final_annex_positions[annex_building.name]
                                        if not check_setback_distance(candidate_x, candidate_y, building.width, building.height,
                                                                      annex_pos[0], annex_pos[1], annex_building.width, annex_building.height):
                                            valid_position = False
                                            failure_reasons['collision'] += 1
                                            break
                                
                                # 주차장들과의 충돌 체크
                                if valid_position:
                                    for parking_building in parking_buildings:
                                        parking_pos = parking_positions[parking_building.name]
                                        if not check_setback_distance(candidate_x, candidate_y, building.width, building.height,
                                                                      parking_pos[0], parking_pos[1], parking_building.width, parking_building.height):
                                            valid_position = False
                                            failure_reasons['collision'] += 1
                                            break
                                
                                # 다른 안내동들과의 충돌 체크
                                if valid_position:
                                    for other_name, other_pos in guide_positions.items():
                                        other_building = next(b for b in guide_buildings if b.name == other_name)
                                        if not check_setback_distance(candidate_x, candidate_y, building.width, building.height,
                                                                      other_pos[0], other_pos[1], other_building.width, other_building.height):
                                            valid_position = False
                                            failure_reasons['collision'] += 1
                                            break
                                
                                if valid_position:
                                    guide_positions[building.name] = (candidate_x, candidate_y)
                                    found_position = True
                                    break
                            
                            if found_position:
                                break
                        
                        if not found_position:
                            valid_guides = False
                            break
                    
                    if not valid_guides:
                        continue
                    
                    # 변전소 배치
                    substation_positions = find_valid_substation_positions(
                        prod_x, prod_y, prod_w, prod_h,
                        final_annex_positions, annex_buildings,
                        guide_positions, guide_buildings,
                        parking_positions, parking_buildings,
                        substation, site_w, site_h, gates, site_polygon
                    )
                    
                    if not substation_positions:
                        failure_reasons['no_substation_position'] += 1
                        continue
                    
                    # 각 변전소 위치별로 별도 레이아웃 생성
                    for sub_x, sub_y, sub_side in substation_positions:
                        
                        # 출입구와 생산동까지의 맨해튼 거리 계산
                        short_edge_centers = get_production_short_edge_centers(prod_x, prod_y, prod_w, prod_h)
                        gate_distances = []
                        
                        for i, gate in enumerate(gates):
                            distances_to_edges = [distance(gate, center) for center in short_edge_centers]
                            min_distance = min(distances_to_edges)
                            closest_center = short_edge_centers[distances_to_edges.index(min_distance)]
                            gate_distances.append({
                                'gate_id': i + 1, 'gate_pos': gate,
                                'closest_center': closest_center, 'distance': min_distance
                            })
                        
                        # 레이아웃 정보 생성
                        layout = {
                            'id': layout_id,
                            'production': {'x': prod_x, 'y': prod_y, 'width': prod_w, 'height': prod_h,
                                           'rotated': is_rotated, 'orientation': orientation},
                            'annex_group': {'side': side, 'positions': final_annex_positions},
                            'substation': {'x': sub_x, 'y': sub_y, 'side': sub_side},
                            'guides': guide_positions, 'parking': parking_positions,
                            'gates': gates, 'gate_distances': gate_distances
                        }
                        
                        layouts.append(layout)
                        layout_id += 1
    
    return layouts, failure_reasons

def find_valid_substation_positions(prod_x: float, prod_y: float, prod_w: float, prod_h: float,
                                    annex_positions: Dict, annex_buildings: List,
                                    guide_positions: Dict, guide_buildings: List,
                                    parking_positions: Dict, parking_buildings: List,
                                    substation, site_w: float, site_h: float,
                                    gates: List[Tuple[float, float]],
                                    site_polygon: Optional[Polygon] = None) -> List[Tuple[float, float, str]]:
    """출입구가 없는 변에 부속동 그룹 중심과 정렬하여 변전소 배치"""
    valid_positions = []
    sides_without_gates = get_sides_without_gates(gates, site_w, site_h)
    
    if not sides_without_gates:
        return []
    
    annex_center_x, annex_center_y = get_annex_group_center(annex_positions, annex_buildings)
    
    for side in sides_without_gates:
        if side == 'top':
            substation_y = site_h - substation.height - SETBACK
            optimal_x = annex_center_x - substation.width / 2
        elif side == 'bottom':
            substation_y = SETBACK
            optimal_x = annex_center_x - substation.width / 2
        elif side == 'left':
            substation_x = SETBACK
            optimal_y = annex_center_y - substation.height / 2
            optimal_x, substation_y = substation_x, optimal_y
        else:  # right
            substation_x = site_w - substation.width - SETBACK
            optimal_y = annex_center_y - substation.height / 2
            optimal_x, substation_y = substation_x, optimal_y
        
        # 위치 탐색
        if side in ['top', 'bottom']:
            search_range = int(site_w - 2*SETBACK)
            for x_offset in range(0, search_range, 10):
                for x_candidate in [optimal_x + x_offset, optimal_x - x_offset]:
                    if (SETBACK <= x_candidate <= site_w - SETBACK - substation.width and
                        is_valid_substation_position(x_candidate, substation_y, substation,
                                                     prod_x, prod_y, prod_w, prod_h,
                                                     annex_positions, annex_buildings,
                                                     guide_positions, guide_buildings,
                                                     parking_positions, parking_buildings) and
                        (site_polygon is None or is_building_inside_polygon(x_candidate, substation_y, substation.width, substation.height, site_polygon))):
                        valid_positions.append((x_candidate, substation_y, side))
                        break
                else:
                    continue
                break
        else:
            search_range = int(site_h - 2*SETBACK)
            for y_offset in range(0, search_range, 10):
                for y_candidate in [optimal_y + y_offset, optimal_y - y_offset]:
                    if (SETBACK <= y_candidate <= site_h - SETBACK - substation.height and
                        is_valid_substation_position(optimal_x, y_candidate, substation,
                                                     prod_x, prod_y, prod_w, prod_h,
                                                     annex_positions, annex_buildings,
                                                     guide_positions, guide_buildings,
                                                     parking_positions, parking_buildings) and
                        (site_polygon is None or is_building_inside_polygon(optimal_x, y_candidate, substation.width, substation.height, site_polygon))):
                        valid_positions.append((optimal_x, y_candidate, side))
                        break
                else:
                    continue
                break
    
    return valid_positions

def find_max_square_area(site_w: float, site_h: float, 
                         buildings_positions: List[Tuple[float, float]], 
                         buildings_sizes: List[Tuple[float, float]], 
                         site_polygon: Optional[Polygon] = None,
                         setback: float = SETBACK) -> Tuple[Optional[float], Optional[float], float]:
    
    grid_size = 1
    max_side = 0
    max_pos = (None, None)

    grid_w = int(site_w / grid_size) + 1
    grid_h = int(site_h / grid_size) + 1
    grid = np.ones((grid_w, grid_h), dtype=bool)

    # 경계 setback 적용
    setback_grid = int(setback / grid_size)
    grid[:setback_grid, :] = False
    grid[-setback_grid:, :] = False
    grid[:, :setback_grid] = False
    grid[:, -setback_grid:] = False

    # 건물 영역 마킹
    for (x, y), (w, h) in zip(buildings_positions, buildings_sizes):
        start_x = max(0, int((x - setback) / grid_size))
        end_x = min(grid_w - 1, int(np.ceil((x + w + setback) / grid_size)))
        start_y = max(0, int((y - setback) / grid_size))
        end_y = min(grid_h - 1, int(np.ceil((y + h + setback) / grid_size)))
        grid[start_x:end_x + 1, start_y:end_y + 1] = False

    # polygon 마스킹 (polygon 내부만 True 유지)
    if site_polygon:
        for i in range(grid_w):
            for j in range(grid_h):
                point = Point(i * grid_size, j * grid_size)
                if not site_polygon.contains(point):
                    grid[i, j] = False

    # 최대 정사각형 찾기 (DP)
    dp = np.zeros_like(grid, dtype=int)
    for i in range(grid_w):
        for j in range(grid_h):
            if grid[i, j]:
                if i == 0 or j == 0:
                    dp[i, j] = 1
                else:
                    dp[i, j] = min(dp[i-1, j], dp[i, j-1], dp[i-1, j-1]) + 1
                
                if dp[i, j] > max_side:
                    max_side = dp[i, j]
                    max_pos = (i - max_side + 1, j - max_side + 1)

    if max_pos == (None, None) or max_side == 0:
        return None, None, 0
    
    x_pos = max_pos[0] * grid_size
    y_pos = max_pos[1] * grid_size
    actual_size = max_side * grid_size
    return x_pos, y_pos, actual_size
