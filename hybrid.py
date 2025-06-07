import json
import random
import math
from copy import deepcopy
import os
from collections import defaultdict

# 요일 매핑
DAYS = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}

# 시간 문자열을 튜플로 변환
def parse_time_slot_str(time_str):
    day_char = time_str[0]
    period = int(time_str[1:])
    return (DAYS[day_char], period)

# 적합도 평가 함수 (낮을수록 좋음)
def evaluate(schedule, preference="공강최대형"):
    occupied = set()
    daily_slots = {i: [] for i in range(7)}
    penalty = 0
    for times in schedule.values():
        for day, period in times:
            if (day, period) in occupied:
                penalty += 10  # 시간 충돌
            else:
                occupied.add((day, period))
                daily_slots[day].append(period)

    if preference == "공강최대형":
        for periods in daily_slots.values():
            if len(periods) >= 2:
                periods.sort()
                for i in range(1, len(periods)):
                    if periods[i] - periods[i - 1] > 1:
                        penalty -= 5  # 공강 보너스
    elif preference == "몰빵형":
        for periods in daily_slots.values():
            if len(periods) > 0 and (max(periods) - min(periods)) <= len(periods):
                penalty -= 5  # 연강 보너스
    elif preference == "아침회피형":
        for periods in daily_slots.values():
            for p in periods:
                if p <= 2:
                    penalty += 3  # 아침 페널티

    return penalty

# 초기 개체 생성
def initialize_population(course_pool, size):
    population = []
    for _ in range(size):
        individual = {
            name: [parse_time_slot_str(t) for t in random.choice(times)]
            for name, times in course_pool.items()
        }
        population.append(individual)
    return population

# 부모 선택
def select_parents(population, preference):
    scored = [(evaluate(ind, preference), ind) for ind in population]
    scored.sort(key=lambda x: x[0])
    return [scored[0][1], scored[1][1]]

# 교차 연산
def crossover(parent1, parent2):
    child = {}
    for key in parent1:
        child[key] = random.choice([parent1[key], parent2[key]])
    return child

# SA 기반 돌연변이
def mutate_with_sa(individual, course_pool, preference, mutation_rate=0.3, temperature=1.0):
    current = deepcopy(individual)
    current_score = evaluate(current, preference)

    for key in current:
        if random.random() < mutation_rate:
            candidate = deepcopy(current)
            candidate[key] = [parse_time_slot_str(t) for t in random.choice(course_pool[key])]
            candidate_score = evaluate(candidate, preference)

            delta = candidate_score - current_score
            acceptance_prob = math.exp(-delta / temperature) if delta > 0 else 1.0

            if random.random() < acceptance_prob:
                current = candidate
                current_score = candidate_score

    return current

# 하이브리드 GA + SA
def hybrid_genetic_sa(course_pool, preference, generations=100, pop_size=20):
    population = initialize_population(course_pool, pop_size)
    best = None
    best_score = float('inf')

    for gen in range(generations):
        parent1, parent2 = select_parents(population, preference)
        temperature = max(0.01, 1 - gen / generations)  # 점점 냉각
        children = [
            mutate_with_sa(crossover(parent1, parent2), course_pool, preference, temperature=temperature)
            for _ in range(pop_size)
        ]
        population = children

        for ind in population:
            score = evaluate(ind, preference)
            if score < best_score:
                best = ind
                best_score = score

    return best, best_score

# 메인 실행부
if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    json_path = os.path.join(base_dir, "combined_courses_final.json")
    with open(json_path, "r", encoding="utf-8") as f:
        raw_courses = json.load(f)

    user_preference = input("선호 유형을 입력하세요 (공강최대형 / 몰빵형 / 아침회피형): ").strip()
    user_grade = int(input("본인의 학년을 입력하세요 (예: 1, 2, 3, 4): "))

    filtered_courses = [c for c in raw_courses if c.get("grade") == user_grade]
    backup_courses = [c for c in raw_courses if c.get("grade") != user_grade]
    random.shuffle(filtered_courses)
    random.shuffle(backup_courses)
    final_courses = filtered_courses[:4] + backup_courses[:2]

    # --- 분반 그룹핑 처리 ---
    course_groups = defaultdict(list)
    for course in final_courses:
        base_code = course["code"].split("-")[0]
        course_groups[base_code].append(course)

    selected_courses = [random.choice(group) for group in course_groups.values()]

    # course_pool 생성
    course_pool = {}
    for course in selected_courses:
        name = f"{course['name']} ({course['code']})"
        if name not in course_pool:
            course_pool[name] = []
        course_pool[name].append(course["times"])

    best_schedule, cost = hybrid_genetic_sa(course_pool, user_preference)

    # 출력 함수
    def readable_time(times):
        day_map = ["월", "화", "수", "목", "금", "토", "일"]
        return [f"{day_map[day]}{period}교시" for day, period in times]

    print("\n✅ 추천 시간표:")
    for name, times in best_schedule.items():
        readable = ', '.join(readable_time(times))
        print(f"{name}: {readable}")

    print(f"\n총 충돌 점수: {cost}")
