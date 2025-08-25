# main.py: 메인 실행 스크립트

import random
import traceback
from inputs import get_user_inputs, create_buildings
from layout import generate_all_layouts
from visualization import visualize_all_layouts, visualize_layout

def main():
    try:
        inputs = get_user_inputs()
        buildings = create_buildings(inputs)
        layouts, failure_reasons = generate_all_layouts(buildings)
        
        print(f"\n총 {len(layouts)}개의 가능한 배치 케이스를 찾았습니다.")
        
        if layouts:
            print("\n모든 배치 케이스 요약 차트를 생성합니다...")
            fig_all = visualize_all_layouts(layouts, buildings)
            fig_all.show()
            
            num_to_show = min(10, len(layouts))
            selected_layouts = random.sample(layouts, num_to_show)
            
            print(f"\n랜덤하게 선택된 {num_to_show}개의 상세 배치도를 생성합니다...")
            
            for i, layout in enumerate(selected_layouts):
                orientation = layout['production']['orientation']
                orientation_text = "가로형" if orientation == "horizontal" else "세로형"
                case_id = layout['id'] + 1
                
                fig = visualize_layout(layout, buildings, f"Case {case_id} ({orientation_text})")
                fig.show()
        else:
            print("주어진 조건으로는 배치할 수 있는 케이스가 없습니다.")
            # 실패 이유 분석 및 출력
            if all(count == 0 for count in failure_reasons.values()):
                print("상세 이유를 파악할 수 없음. 입력 값을 확인하세요.")
            else:
                max_reason = max(failure_reasons, key=failure_reasons.get)
                print("주요 실패 이유:")
                if max_reason == 'insufficient_space':
                    print("- 부지 공간이 부족합니다. 건물 크기나 setback을 조정하세요.")
                elif max_reason == 'collision':
                    print("- 건물 간 충돌(이격 거리 미달)이 발생합니다. 위치나 크기를 조정하세요.")
                elif max_reason == 'outside_polygon':
                    print("- 건물이 다각형 부지 경계를 벗어났습니다. 입력 좌표를 확인하세요.")
                elif max_reason == 'no_substation_position':
                    print("- 변전소 배치 가능한 위치가 없습니다. 출입구나 다른 건물 위치를 조정하세요.")
                print(f"(상세 통계: {failure_reasons})")
        
        input("\n프로그램을 종료하려면 Enter 키를 누르세요...")
            
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        traceback.print_exc()
        input("\n프로그램을 종료하려면 Enter 키를 누르세요...")

if __name__ == "__main__":
    main()
