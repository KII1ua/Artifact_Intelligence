import json
import random
import math
from copy import deepcopy
import os

# 요일 매핑
DAYS = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}

# 시간 문자열을 튜플로 변환
def parse_time_slot_str(time_str):
    day_char = time_str[0]
    period = int(time_str[1:])
    return (DAYS[day_char], period)

# 적합도 평가 함수 (사용자 선호 반영)
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
                if day in daily_slots:
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

# 유전 알고리즘 구성 요소
def initialize_population(course_pool, size):
    population = []
    for _ in range(size):
        individual = {
            name: [parse_time_slot_str(t) for t in random.choice(times)]
            for name, times in course_pool.items()
        }
        population.append(individual)
    return population

def select_parents(population, preference):
    scored = [(evaluate(ind, preference), ind) for ind in population]
    scored.sort(key=lambda x: x[0])  # 낮을수록 좋음
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
            new_ind[key] = [parse_time_slot_str(t) for t in random.choice(course_pool[key])]
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

# 메인 실행부
if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    json_path = os.path.join(base_dir, "combined_courses_final.json")
    with open(json_path, "r", encoding="utf-8") as f:
        raw_courses = json.load(f)

    user_preference = input("선호 유형을 입력하세요 (공강최대형 / 몰빵형 / 아침회피형): ")
    user_grade = int(input("본인의 학년을 입력하세요 (예: 1, 2, 3, 4): "))

    filtered_courses = [c for c in raw_courses if c.get("grade") == user_grade]
    backup_courses = [c for c in raw_courses if c.get("grade") != user_grade]
    random.shuffle(filtered_courses)
    random.shuffle(backup_courses)
    final_courses = filtered_courses[:4] + backup_courses[:2]

    course_pool = {}
    for course in final_courses:
        name = f"{course['name']} ({course['code']})"
        if name not in course_pool:
            course_pool[name] = []
        course_pool[name].append(course["times"])

    best_schedule, cost = genetic_algorithm(course_pool, user_preference)

    def readable_time(times):
        day_map = ["월", "화", "수", "목", "금", "토", "일"]
        return [f"{day_map[day]}{period}교시" for day, period in times]

    for name, times in best_schedule.items():
        readable = ', '.join(readable_time(times))
        print(f"{name}: {readable}")

    print(f"총 충돌 점수: {cost}")