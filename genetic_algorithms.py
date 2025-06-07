import json
import random
import tkinter as tk        # 시각화를 위한 라이브러리 추가
from tkinter import ttk     # 시각화를 위한 라이브러리 추가
from copy import deepcopy
import os
from collections import defaultdict

# 요일 매핑
DAYS = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}

# 시간 문자열 → 튜플 리스트로 변환
def parse_schedule(schedule_str):
    day_char = schedule_str[0]
    rest = schedule_str[1:]
    if "-" in rest:
        start, end = map(int, rest.split("-"))
        return [(DAYS[day_char], p) for p in range(start, end + 1)]
    else:
        return [(DAYS[day_char], int(rest))]

# 사용자 선호 기반 평가 함수
def evaluate(schedule, preference="공강최대형"):
    occupied = set()
    daily_slots = {i: [] for i in range(7)}
    penalty = 0
    for times in schedule.values():
        for day, period in times:
            if (day, period) in occupied:
                penalty += 10
            else:
                occupied.add((day, period))
                daily_slots[day].append(period)

    if preference == "공강최대형":
        for periods in daily_slots.values():
            if len(periods) >= 2:
                periods.sort()
                for i in range(1, len(periods)):
                    if periods[i] - periods[i - 1] > 1:
                        penalty -= 5
    elif preference == "몰빵형":
        for periods in daily_slots.values():
            if len(periods) > 0 and (max(periods) - min(periods)) <= len(periods):
                penalty -= 5
    elif preference == "아침회피형":
        for periods in daily_slots.values():
            for p in periods:
                if p <= 2:
                    penalty += 3

    return penalty

# 유전 알고리즘 요소
def initialize_population(course_pool, size):
    population = []
    for _ in range(size):
        individual = {
            name: sum([parse_schedule(schedule) for schedule in random.choice(times)], [])
            for name, times in course_pool.items()
        }
        population.append(individual)
    return population

def select_parents(population, preference):
    scored = [(evaluate(ind, preference), ind) for ind in population]
    scored.sort(key=lambda x: x[0])
    return [scored[0][1], scored[1][1]]

def crossover(parent1, parent2):
    child = {}
    for key in parent1:
        child[key] = random.choice([parent1[key], parent2[key]])
    return child

def mutate(individual, course_pool, mutation_rate=0.1):
    new_ind = deepcopy(individual)
    for key in new_ind:
        if random.random() < mutation_rate:
            new_ind[key] = sum([parse_schedule(schedule) for schedule in random.choice(course_pool[key])], [])
    return new_ind

def genetic_algorithm(course_pool, preference, generations=100, pop_size=20):
    population = initialize_population(course_pool, pop_size)
    best = None
    best_score = float('inf')

    for _ in range(generations):
        parent1, parent2 = select_parents(population, preference)
        children = [mutate(crossover(parent1, parent2), course_pool) for _ in range(pop_size)]
        population = children
        for ind in population:
            score = evaluate(ind, preference)
            if score < best_score:
                best = ind
                best_score = score

    return best, best_score

# 학점 기반 과목 선택
def select_courses_by_credit_limit(courses, user_grade, max_credits, must_take_codes, already_taken_codes):
    course_groups = defaultdict(list)
    for course in courses:
        course_groups[course["course_code"]].append(course)

    selected = []
    total_credits = 0

    # 무조건 들어야 하는 과목 먼저 선택
    for code in must_take_codes:
        if code in course_groups:
            selected_course = random.choice(course_groups[code])
            selected.append(selected_course)
            total_credits += selected_course['credits']

    # 나머지 과목 중에서 선택
    sorted_groups = sorted(course_groups.items(), key=lambda g: abs(g[1][0]['year_level'] - user_grade))
    random.shuffle(sorted_groups)

    for code, group in sorted_groups:
        if code in must_take_codes or code in already_taken_codes:
            continue
        candidate = random.choice(group)
        if total_credits + candidate['credits'] <= max_credits:
            selected.append(candidate)
            total_credits += candidate['credits']
        if total_credits >= max_credits:
            break

    return selected

def draw_schedule_canvas(best_schedule):
    root = tk.Tk()
    root.title("추천 시간표 (카카오 스타일)")
    root.geometry("750x700")

    canvas = tk.Canvas(root, width=750, height=700, bg="white")
    canvas.pack()

    days = ["월", "화", "수", "목", "금"]
    day_width = 120
    hour_height = 45
    top_margin = 50
    left_margin = 60

    # 요일 헤더
    for i, day in enumerate(days):
        x = left_margin + i * day_width
        canvas.create_text(x + day_width // 2, 25, text=day, font=("맑은 고딕", 12, "bold"))

    # 교시 선 + 번호
    for hour in range(1, 13):
        y = top_margin + (hour - 1) * hour_height
        canvas.create_text(30, y + hour_height // 2, text=f"{hour}", font=("맑은 고딕", 10))
        canvas.create_line(left_margin, y, left_margin + day_width * len(days), y, fill="#ddd")

    # 시간표 블럭 그리기
    for subject, times in best_schedule.items():
        # (요일, 교시) 리스트를 group by
        day_slots = {}
        for day, period in times:
            if day not in day_slots:
                day_slots[day] = []
            day_slots[day].append(period)
        
        for day, periods in day_slots.items():
            periods.sort()
            # 연속된 교시 블럭만 하나로 묶어서 그림
            start = periods[0]
            end = periods[0]
            for i in range(1, len(periods)):
                if periods[i] == end + 1:
                    end = periods[i]
                else:
                    draw_block(canvas, subject, day, start, end, left_margin, day_width, top_margin, hour_height)
                    start = periods[i]
                    end = periods[i]
            draw_block(canvas, subject, day, start, end, left_margin, day_width, top_margin, hour_height)

    root.mainloop()

def draw_block(canvas, subject, day, start, end, left_margin, day_width, top_margin, hour_height):
    x1 = left_margin + day * day_width + 5
    y1 = top_margin + (start - 1) * hour_height + 2
    x2 = x1 + day_width - 10
    y2 = top_margin + end * hour_height - 2
    canvas.create_rectangle(x1, y1, x2, y2, fill="#ccddff", outline="#444")
    canvas.create_text((x1 + x2)//2, (y1 + y2)//2, text=subject, font=("맑은 고딕", 10), width=day_width - 20)

# 실행부
if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(base_dir, "courses.json"), "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        raw_courses = raw_data.get("courses", raw_data)

    with open(os.path.join(base_dir, "filter.json"), "r", encoding="utf-8") as f:
        filters = json.load(f)
        must_take_codes = filters.get("must_take", [])
        already_taken_codes = filters.get("already_taken", [])

    user_preference = input("선호 유형 (공강최대형 / 몰빵형 / 아침회피형): ").strip()
    user_grade = int(input("학년 입력 (예: 1, 2, 3, 4): "))
    user_credit_limit = int(input("희망 학점 (예: 18): "))

    selected_courses = select_courses_by_credit_limit(raw_courses, user_grade, user_credit_limit, must_take_codes, already_taken_codes)

    course_pool = {}
    for course in selected_courses:
        name = f"{course['course_name']} ({course['course_code']}-{course['section']})"
        if name not in course_pool:
            course_pool[name] = []
        course_pool[name].append([course["schedule"]])

    best_schedule, cost = genetic_algorithm(course_pool, user_preference)

    def readable_time(times):
        day_map = ["월", "화", "수", "목", "금", "토", "일"]
        return [f"{day_map[day]}{period}교시" for day, period in times]

    print("\n 추천 시간표:")
    for name, times in best_schedule.items():
        readable = ', '.join(readable_time(times))
        print(f"{name}: {readable}")
    print(f"\n총 충돌 점수: {cost}")

    draw_schedule_canvas(best_schedule)
