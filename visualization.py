# visualization.py: 시각화 함수

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict
from utils import get_production_areas, get_main_gate
from layout import get_buildings_positions_sizes, find_max_square_area
from config import SETBACK
from shapely.geometry import Polygon  # 추가: 다각형 처리용

def visualize_layout(layout: Dict, buildings: Dict, layout_title: str = "") -> go.Figure:
    fig = go.Figure()
    site_size = buildings['site_size']
    site_shape = buildings.get('site_shape', '직사각형')  # site_shape 확인

    # site_polygon 생성 및 site_w, site_h 계산
    if site_shape == '직사각형':
        site_w, site_h = site_size
        site_polygon = None
        fig.add_trace(go.Scatter(
            x=[0, site_w, site_w, 0, 0], y=[0, 0, site_h, site_h, 0],
            mode='lines', line=dict(color='black', width=3),
            name='부지 경계', showlegend=True
        ))
    else:  # 다각형
        site_polygon = Polygon(site_size)
        min_x, min_y, max_x, max_y = site_polygon.bounds
        site_w = max_x - min_x
        site_h = max_y - min_y
        x_coords, y_coords = zip(*site_size)  # 좌표 분리
        x_coords = list(x_coords) + [x_coords[0]]  # 닫힌 형태
        y_coords = list(y_coords) + [y_coords[0]]
        fig.add_trace(go.Scatter(
            x=x_coords, y=y_coords,
            mode='lines', line=dict(color='black', width=3),
            name='부지 경계 (다각형)', showlegend=True
        ))
    
    # 생산동
    prod_info = layout['production']
    fig.add_shape(
        type="rect", x0=prod_info['x'], y0=prod_info['y'],
        x1=prod_info['x'] + prod_info['width'], y1=prod_info['y'] + prod_info['height'],
        fillcolor=buildings['prod_building'].color, opacity=0.7,
        line=dict(color="black", width=3)
    )
    
    # 생산동 내부 영역 표시
    areas = get_production_areas(prod_info['x'], prod_info['y'], 
                                 prod_info['width'], prod_info['height'], 
                                 prod_info['orientation'])
    
    area_colors = {'electrode': 'red', 'assembly': 'blue', 'formation': 'green'}
    area_names = {'electrode': 'Electrode', 'assembly': 'Assembly', 'formation': 'Formation'}
    
    for area_type, center in areas.items():
        fig.add_trace(go.Scatter(
            x=[center[0]], y=[center[1]], mode='markers+text',
            marker=dict(size=15, color=area_colors[area_type], symbol='circle'),
            text=[area_names[area_type]], textposition="bottom center",
            name=f'{area_names[area_type]} 영역', showlegend=True
        ))
    
    fig.add_annotation(
        x=prod_info['x'] + prod_info['width']/2, y=prod_info['y'] + prod_info['height']/2,
        text="생산동", showarrow=False, font=dict(size=12, color="white")
    )
    
    # 부속동들
    for building in buildings['annex_buildings']:
        pos = layout['annex_group']['positions'][building.name]
        fig.add_shape(
            type="rect", x0=pos[0], y0=pos[1],
            x1=pos[0] + building.width, y1=pos[1] + building.height,
            fillcolor=building.color, opacity=0.7, line=dict(color="black", width=1)
        )
        fig.add_annotation(
            x=pos[0] + building.width/2, y=pos[1] + building.height/2,
            text=building.name, showarrow=False, font=dict(size=8)
        )
    
    # 변전소
    sub_info = layout['substation']
    substation = buildings['substation']
    fig.add_shape(
        type="rect", x0=sub_info['x'], y0=sub_info['y'],
        x1=sub_info['x'] + substation.width, y1=sub_info['y'] + substation.height,
        fillcolor=substation.color, opacity=0.7, line=dict(color="black", width=2)
    )
    fig.add_annotation(
        x=sub_info['x'] + substation.width/2, y=sub_info['y'] + substation.height/2,
        text="변전소", showarrow=False, font=dict(size=10)
    )
    
    # 안내동들
    for building in buildings['guide_buildings']:
        pos = layout['guides'][building.name]
        fig.add_shape(
            type="rect", x0=pos[0], y0=pos[1],
            x1=pos[0] + building.width, y1=pos[1] + building.height,
            fillcolor=building.color, opacity=0.7, line=dict(color="black", width=1)
        )
        fig.add_annotation(
            x=pos[0] + building.width/2, y=pos[1] + building.height/2,
            text=building.name, showarrow=False, font=dict(size=8)
        )
    
    # 주차장들
    for i, building in enumerate(buildings['parking_buildings']):
        pos = layout['parking'][building.name]
        fig.add_shape(
            type="rect", x0=pos[0], y0=pos[1],
            x1=pos[0] + building.width, y1=pos[1] + building.height,
            fillcolor=building.color, opacity=0.7, line=dict(color="black", width=2)
        )
        fig.add_annotation(
            x=pos[0] + building.width/2, y=pos[1] + building.height/2,
            text=f"주차장{i+1}", showarrow=False, font=dict(size=9, color="white")
        )
    
    # 출입구들
    main_gate = get_main_gate(layout['gates'])
    for i, (gate_x, gate_y) in enumerate(layout['gates']):
        is_main = (gate_x, gate_y) == main_gate
        color = 'darkred' if is_main else 'red'
        name = 'Main 출입구' if is_main else f'출입구 {i+1}'
        
        fig.add_trace(go.Scatter(
            x=[gate_x], y=[gate_y], mode='markers',
            marker=dict(size=20 if is_main else 15, color=color, symbol='diamond'),
            name=name, showlegend=True
        ))
    
    # 출입구에서 생산동까지의 맨해튼 거리
    for gate_dist in layout['gate_distances']:
        gate_pos = gate_dist['gate_pos']
        closest_center = gate_dist['closest_center']
        distance_val = gate_dist['distance']
        gate_id = gate_dist['gate_id']
        
        fig.add_trace(go.Scatter(
            x=[gate_pos[0], closest_center[0], closest_center[0]],
            y=[gate_pos[1], gate_pos[1], closest_center[1]],
            mode='lines', line=dict(color='purple', width=2, dash='dash'),
            name=f'출입구 {gate_id} 맨해튼거리: {distance_val:.1f}m', showlegend=True
        ))
        
        mid_x = (gate_pos[0] + closest_center[0]) / 2
        mid_y = (gate_pos[1] + closest_center[1]) / 2
        fig.add_annotation(
            x=mid_x, y=mid_y, text=f"{distance_val:.1f}m", showarrow=False,
            font=dict(size=10, color="purple"), bgcolor="white",
            bordercolor="purple", borderwidth=1
        )
    
    # Future Area
    positions, sizes = get_buildings_positions_sizes(layout, buildings)
    future_x, future_y, future_size = find_max_square_area(site_w, site_h, positions, sizes, site_polygon, SETBACK)
    
    if future_x is not None and future_size > 0:
        fig.add_shape(
            type="rect", x0=future_x, y0=future_y,
            x1=future_x + future_size, y1=future_y + future_size,
            line=dict(color="blue", width=2, dash='dot'),
            fillcolor='rgba(0,0,0,0)'
        )
        fig.add_annotation(
            x=future_x + future_size/2, y=future_y + future_size/2,
            text=f"Future Area\n{future_size*future_size:.0f} m²",
            showarrow=False, font=dict(size=12, color="blue"),
            bgcolor="rgba(255,255,255,0.8)", bordercolor="blue", borderwidth=1
        )
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='lines',
            line=dict(color='blue', width=2, dash='dot'),
            name=f'Future Area {future_size*future_size:.0f} m²', showlegend=True
        ))
    
    fig.update_layout(
        title=f"공장 단지 배치도 - {layout_title}",
        xaxis_title="X (m)", yaxis_title="Y (m)",
        width=1000, height=800, showlegend=True,
        xaxis=dict(scaleanchor="y", scaleratio=1, gridcolor='lightgray'),
        yaxis=dict(gridcolor='lightgray'),
        plot_bgcolor='lightgreen', font=dict(family="Arial", size=12)
    )
    
    return fig

def visualize_all_layouts(layouts: List[Dict], buildings: Dict, max_display: int = 12):
    if not layouts:
        print("생성된 레이아웃이 없습니다.")
        return
    
    site_size = buildings['site_size']
    site_shape = buildings.get('site_shape', '직사각형')  # site_shape 추가 (inputs에서 전달됨)

    if site_shape == '직사각형':
        site_w, site_h = site_size
        site_polygon = None
    else:  # 다각형
        site_polygon = Polygon(site_size)
        min_x, min_y, max_x, max_y = site_polygon.bounds
        site_w = max_x - min_x
        site_h = max_y - min_y
        # 추가: 다각형 경계 그리기 로직은 visualize_layout에서도 업데이트 필요

    num_layouts = min(len(layouts), max_display)
    cols = 3
    rows = (num_layouts + cols - 1) // cols
    
    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[f"Layout {layout['id']+1} (변전소: {layout['substation'].get('side', '?')}변)" 
                        for layout in layouts[:num_layouts]],
        specs=[[{"secondary_y": False} for _ in range(cols)] for _ in range(rows)],
        horizontal_spacing=0.05, vertical_spacing=0.1
    )
    
    for idx, layout in enumerate(layouts[:num_layouts]):
        row = idx // cols + 1
        col = idx % cols + 1
        
        # 부지 경계 (다각형 지원 추가)
        if site_shape == '직사각형':
            fig.add_trace(go.Scatter(
                x=[0, site_w, site_w, 0, 0], y=[0, 0, site_h, site_h, 0],
                mode='lines', line=dict(color='black', width=2), showlegend=False
            ), row=row, col=col)
        else:
            x_coords, y_coords = zip(*site_size)
            x_coords = list(x_coords) + [x_coords[0]]
            y_coords = list(y_coords) + [y_coords[0]]
            fig.add_trace(go.Scatter(
                x=x_coords, y=y_coords,
                mode='lines', line=dict(color='black', width=2), showlegend=False
            ), row=row, col=col)
        
        # 생산동
        prod_info = layout['production']
        fig.add_shape(
            type="rect", x0=prod_info['x'], y0=prod_info['y'],
            x1=prod_info['x'] + prod_info['width'], y1=prod_info['y'] + prod_info['height'],
            fillcolor='red', opacity=0.7, row=row, col=col
        )
        
        # 변전소
        sub_info = layout['substation']
        fig.add_shape(
            type="rect", x0=sub_info['x'], y0=sub_info['y'],
            x1=sub_info['x'] + buildings['substation'].width,
            y1=sub_info['y'] + buildings['substation'].height,
            fillcolor='orange', opacity=0.8, row=row, col=col
        )
        
        # 부속동들
        for building in buildings['annex_buildings']:
            pos = layout['annex_group']['positions'][building.name]
            fig.add_shape(
                type="rect", x0=pos[0], y0=pos[1],
                x1=pos[0] + building.width, y1=pos[1] + building.height,
                fillcolor='blue', opacity=0.5, row=row, col=col
            )
    
    fig.update_layout(
        title_text="공장 단지 배치 케이스",
        height=300*rows, showlegend=False
    )
    
    return fig
