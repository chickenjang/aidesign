# inputs.py: 사용자 입력과 건물 생성 함수 (PyQt GUI 버전 - 다각형 입력 지원 강화)

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QGroupBox, QFormLayout, QMessageBox
from typing import Dict, List, Tuple
from config import DEFAULT_VALUES
from models import Building
from utils import calculate_parking_area, calculate_parking_dimensions, get_main_gate
from shapely.geometry import Polygon  # 다각형 검사용

class InputWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("공장 단지 배치도 생성 프로그램")
        self.setGeometry(300, 300, 600, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.use_default_checkbox = QCheckBox("기본값 사용")
        self.use_default_checkbox.setChecked(True)
        self.use_default_checkbox.stateChanged.connect(self.toggle_inputs)
        self.layout.addWidget(self.use_default_checkbox)

        # Site group (다각형 지원)
        site_group = QGroupBox("단지 크기 (다각형 지원)")
        site_layout = QVBoxLayout()
        self.site_shape_combo = QComboBox()
        self.site_shape_combo.addItems(["직사각형", "오각형", "육각형"])
        self.site_shape_combo.currentIndexChanged.connect(self.update_site_inputs)
        site_layout.addWidget(QLabel("부지 형태:"))
        site_layout.addWidget(self.site_shape_combo)

        self.site_inputs_layout = QVBoxLayout()  # 동적 레이아웃으로 변경
        site_layout.addLayout(self.site_inputs_layout)
        site_group.setLayout(site_layout)
        self.layout.addWidget(site_group)

        self.site_polygon_edits = []  # 다각형 좌표 리스트

        # Production group
        prod_group = QGroupBox("생산동 크기")
        prod_layout = QFormLayout()
        self.prod_width_edit = QLineEdit()
        self.prod_height_edit = QLineEdit()
        prod_layout.addRow("너비 (m):", self.prod_width_edit)
        prod_layout.addRow("높이 (m):", self.prod_height_edit)
        prod_group.setLayout(prod_layout)
        self.layout.addWidget(prod_group)

        # Annex group
        annex_group = QGroupBox("부속동 크기")
        annex_layout = QFormLayout()
        self.annex_names = ['Admin', 'UT', '신뢰성시험동', '폐기물보관장', '위험물보관장', '오/폐수처리장', 'CESS Control', 'SRP Control']
        self.annex_width_edits = {}
        self.annex_height_edits = {}
        for name in self.annex_names:
            width_edit = QLineEdit()
            height_edit = QLineEdit()
            hbox = QHBoxLayout()
            hbox.addWidget(width_edit)
            hbox.addWidget(height_edit)
            annex_layout.addRow(f"{name} (너비/높이 m):", hbox)
            self.annex_width_edits[name] = width_edit
            self.annex_height_edits[name] = height_edit
        annex_group.setLayout(annex_layout)
        self.layout.addWidget(annex_group)

        # Gate group
        gate_group = QGroupBox("출입구 설정")
        gate_layout = QVBoxLayout()
        self.gate_count_combo = QComboBox()
        self.gate_count_combo.addItems([str(i) for i in range(1, 6)])  # 1~5개 제한
        self.gate_count_combo.setCurrentText("2")
        self.gate_count_combo.currentIndexChanged.connect(self.update_gate_coords)
        gate_layout.addWidget(QLabel("출입구 개수:"))
        gate_layout.addWidget(self.gate_count_combo)

        self.gate_coords_layout = QFormLayout()
        self.gate_coord_edits = []
        self.update_gate_coords()  # 초기 2개
        gate_layout.addLayout(self.gate_coords_layout)
        gate_group.setLayout(gate_layout)
        self.layout.addWidget(gate_group)

        # Guide group
        guide_group = QGroupBox("안내동 크기")
        guide_layout = QFormLayout()
        self.main_guide_width_edit = QLineEdit()
        self.main_guide_height_edit = QLineEdit()
        self.other_guide_width_edit = QLineEdit()
        self.other_guide_height_edit = QLineEdit()
        guide_layout.addRow("Main 너비 (m):", self.main_guide_width_edit)
        guide_layout.addRow("Main 높이 (m):", self.main_guide_height_edit)
        guide_layout.addRow("기타 너비 (m):", self.other_guide_width_edit)
        guide_layout.addRow("기타 높이 (m):", self.other_guide_height_edit)
        guide_group.setLayout(guide_layout)
        self.layout.addWidget(guide_group)

        # Substation and Parking
        sub_parking_group = QGroupBox("변전소 및 주차장")
        sub_parking_layout = QFormLayout()
        self.substation_width_edit = QLineEdit()
        self.substation_height_edit = QLineEdit()
        self.parking_count_edit = QLineEdit()
        sub_parking_layout.addRow("변전소 너비 (m):", self.substation_width_edit)
        sub_parking_layout.addRow("변전소 높이 (m):", self.substation_height_edit)
        sub_parking_layout.addRow("주차댓수:", self.parking_count_edit)
        sub_parking_group.setLayout(sub_parking_layout)
        self.layout.addWidget(sub_parking_group)

        # Submit button
        submit_btn = QPushButton("확인")
        submit_btn.clicked.connect(self.submit)
        self.layout.addWidget(submit_btn)

        self.fill_default_values()
        self.toggle_inputs()
        self.update_site_inputs(0)  # 초기 직사각형 입력

    def update_site_inputs(self, index):
        shape = self.site_shape_combo.currentText()
        # 기존 입력 청소
        while self.site_inputs_layout.count():
            child = self.site_inputs_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                sub_layout = child.layout()
                while sub_layout.count():
                    sub_child = sub_layout.takeAt(0)
                    if sub_child.widget():
                        sub_child.widget().deleteLater()
        self.site_polygon_edits.clear()

        if shape == "직사각형":
            form_layout = QFormLayout()
            self.site_width_edit = QLineEdit()
            self.site_height_edit = QLineEdit()
            form_layout.addRow("너비 (m):", self.site_width_edit)
            form_layout.addRow("높이 (m):", self.site_height_edit)
            self.site_inputs_layout.addLayout(form_layout)
        else:
            vertex_count = 5 if shape == "오각형" else 6
            form_layout = QFormLayout()
            for i in range(vertex_count):
                x_edit = QLineEdit()
                y_edit = QLineEdit()
                hbox = QHBoxLayout()
                hbox.addWidget(x_edit)
                hbox.addWidget(y_edit)
                form_layout.addRow(f"꼭짓점 {i+1} (X/Y):", hbox)
                self.site_polygon_edits.append((x_edit, y_edit))
            self.site_inputs_layout.addLayout(form_layout)

    def toggle_inputs(self):
        enabled = not self.use_default_checkbox.isChecked()
        for widget in self.central_widget.findChildren((QLineEdit, QComboBox)):
            widget.setEnabled(enabled)

    def update_gate_coords(self):
        count = int(self.gate_count_combo.currentText())
        # 기존 레이아웃 청소
        while self.gate_coords_layout.count():
            child = self.gate_coords_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.gate_coord_edits.clear()

        for i in range(count):
            x_edit = QLineEdit()
            y_edit = QLineEdit()
            hbox = QHBoxLayout()
            hbox.addWidget(x_edit)
            hbox.addWidget(y_edit)
            self.gate_coords_layout.addRow(f"출입구 {i+1} (X/Y):", hbox)
            self.gate_coord_edits.append((x_edit, y_edit))

    def fill_default_values(self):
        self.site_shape_combo.setCurrentText("직사각형")
        self.update_site_inputs(0)
        self.site_width_edit.setText(str(DEFAULT_VALUES['site_size'][0]))
        self.site_height_edit.setText(str(DEFAULT_VALUES['site_size'][1]))

        self.prod_width_edit.setText(str(DEFAULT_VALUES['prod_size'][0]))
        self.prod_height_edit.setText(str(DEFAULT_VALUES['prod_size'][1]))

        for name in self.annex_names:
            self.annex_width_edits[name].setText(str(DEFAULT_VALUES['annex_sizes'][name][0]))
            self.annex_height_edits[name].setText(str(DEFAULT_VALUES['annex_sizes'][name][1]))

        self.gate_count_combo.setCurrentText(str(DEFAULT_VALUES['gate_count']))
        self.update_gate_coords()

        for i, (x, y) in enumerate(DEFAULT_VALUES['gates']):
            if i < len(self.gate_coord_edits):
                self.gate_coord_edits[i][0].setText(str(x))
                self.gate_coord_edits[i][1].setText(str(y))

        self.main_guide_width_edit.setText(str(DEFAULT_VALUES['main_guide_size'][0]))
        self.main_guide_height_edit.setText(str(DEFAULT_VALUES['main_guide_size'][1]))
        self.other_guide_width_edit.setText(str(DEFAULT_VALUES['other_guide_size'][0]))
        self.other_guide_height_edit.setText(str(DEFAULT_VALUES['other_guide_size'][1]))

        self.substation_width_edit.setText(str(DEFAULT_VALUES['substation_size'][0]))
        self.substation_height_edit.setText(str(DEFAULT_VALUES['substation_size'][1]))
        self.parking_count_edit.setText(str(DEFAULT_VALUES['parking_count']))

    def validate(self):
        try:
            if self.use_default_checkbox.isChecked():
                return True

            shape = self.site_shape_combo.currentText()
            if shape == "직사각형":
                float(self.site_width_edit.text())
                float(self.site_height_edit.text())
            else:
                vertices = []
                for x_edit, y_edit in self.site_polygon_edits:
                    x = float(x_edit.text())
                    y = float(y_edit.text())
                    vertices.append((x, y))
                Polygon(vertices)  # 유효성 검사

            float(self.prod_width_edit.text())
            float(self.prod_height_edit.text())

            for name in self.annex_names:
                float(self.annex_width_edits[name].text())
                float(self.annex_height_edits[name].text())

            gate_count = int(self.gate_count_combo.currentText())
            for x_edit, y_edit in self.gate_coord_edits:
                float(x_edit.text())
                float(y_edit.text())

            float(self.main_guide_width_edit.text())
            float(self.main_guide_height_edit.text())
            float(self.other_guide_width_edit.text())
            float(self.other_guide_height_edit.text())
            float(self.substation_width_edit.text())
            float(self.substation_height_edit.text())
            int(self.parking_count_edit.text())

            return True
        except ValueError as e:
            QMessageBox.warning(self, "입력 오류", f"잘못된 입력: {e}")
            return False

    def submit(self):
        if not self.validate():
            return

        if self.use_default_checkbox.isChecked():
            self.result = DEFAULT_VALUES
        else:
            shape = self.site_shape_combo.currentText()
            if shape == "직사각형":
                site_size = (float(self.site_width_edit.text()), float(self.site_height_edit.text()))
            else:
                site_size = [(float(x_edit.text()), float(y_edit.text())) for x_edit, y_edit in self.site_polygon_edits]

            prod_width = float(self.prod_width_edit.text())
            prod_height = float(self.prod_height_edit.text())

            annex_sizes = {}
            for name in self.annex_names:
                w = float(self.annex_width_edits[name].text())
                h = float(self.annex_height_edits[name].text())
                annex_sizes[name] = (w, h)

            gate_count = int(self.gate_count_combo.currentText())
            gates = []
            for x_edit, y_edit in self.gate_coord_edits:
                x = float(x_edit.text())
                y = float(y_edit.text())
                gates.append((x, y))

            main_guide_width = float(self.main_guide_width_edit.text())
            main_guide_height = float(self.main_guide_height_edit.text())
            other_guide_width = float(self.other_guide_width_edit.text())
            other_guide_height = float(self.other_guide_height_edit.text())
            substation_width = float(self.substation_width_edit.text())
            substation_height = float(self.substation_height_edit.text())
            parking_count = int(self.parking_count_edit.text())

            self.result = {
                'site_size': site_size,
                'site_shape': shape,
                'prod_size': (prod_width, prod_height),
                'annex_sizes': annex_sizes,
                'main_guide_size': (main_guide_width, main_guide_height),
                'other_guide_size': (other_guide_width, other_guide_height),
                'gate_count': gate_count, 'gates': gates,
                'substation_size': (substation_width, substation_height),
                'parking_count': parking_count
            }
        self.close()

def get_user_inputs() -> Dict:
    app = QApplication(sys.argv)
    window = InputWindow()
    window.show()
    app.exec_()
    if hasattr(window, 'result') and window.result:
        return window.result
    else:
        print("입력 취소됨. 기본값 사용.")
        return DEFAULT_VALUES

def create_buildings(inputs: Dict) -> Dict:
    site_size = inputs['site_size']
    if isinstance(site_size, list):  # 다각형
        site_polygon = Polygon(site_size)
        site_w = site_polygon.bounds[2] - site_polygon.bounds[0]  # 대략적 너비
        site_h = site_polygon.bounds[3] - site_polygon.bounds[1]  # 대략적 높이
    else:  # 직사각형
        site_w, site_h = site_size

    prod_w, prod_h = inputs['prod_size']
    
    prod_building = Building('Production', prod_w, prod_h)
    
    annex_buildings = [Building(name, width, height) 
                       for name, (width, height) in inputs['annex_sizes'].items()]
    
    main_gate = get_main_gate(inputs['gates'])
    guide_buildings = [Building('안내동1', inputs['main_guide_size'][0], inputs['main_guide_size'][1])]
    
    guide_counter = 2
    for gate_pos in inputs['gates']:
        if gate_pos != main_gate:
            guide_buildings.append(Building(f'안내동{guide_counter}',
                                            inputs['other_guide_size'][0], 
                                            inputs['other_guide_size'][1]))
            guide_counter += 1
    
    substation = Building('Substation', inputs['substation_size'][0], inputs['substation_size'][1])
    
    total_area, breakdown = calculate_parking_area(inputs['parking_count'])
    parking_width, parking_length = calculate_parking_dimensions(total_area)
    parking_buildings = [Building(f'Parking_{i+1}', parking_width, parking_length) for i in range(2)]
    
    return {
        'site_size': site_size,  # 다각형 지원
        'site_shape': inputs.get('site_shape', '직사각형'),
        'prod_building': prod_building,
        'annex_buildings': annex_buildings,
        'guide_buildings': guide_buildings,
        'gates': inputs['gates'], 'substation': substation,
        'parking_buildings': parking_buildings, 'parking_info': breakdown
    }
