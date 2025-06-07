import json
import random
import tkinter as tk
from copy import deepcopy
import os
from collections import defaultdict

# 시간 문자열 파서
class ScheduleParser:
    DAYS = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}

    @staticmethod
    def parse(schedule_str):
        day_char = schedule_str[0]
        rest = schedule_str[1:]
        if "-" in rest:
            start, end = map(int, rest.split("-"))
            return [(ScheduleParser.DAYS[day_char], p) for p in range(start, end + 1)]
        else:
            return [(ScheduleParser.DAYS[day_char], int(rest))]

# 시간표 평가
class ScheduleEvaluator:
    @staticmethod
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

# 과목 선택
class CourseSelector:
    @staticmethod
    def select(courses, user_grade, max_credits, must_take_codes, already_taken_codes):
        course_groups = defaultdict(list)
        for course in courses:
            course_groups[course["course_code"]].append(course)

        selected = []
        total_credits = 0

        for code in must_take_codes:
            if code in course_groups:
                selected_course = random.choice(course_groups[code])
                selected.append(selected_course)
                total_credits += selected_course['credits']

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

# 유전 알고리즘
class GeneticScheduler:
    def __init__(self, course_pool, preference):
        self.course_pool = course_pool
        self.preference = preference

    def initialize_population(self, size):
        return [
            {
                name: sum([ScheduleParser.parse(s) for s in random.choice(times)], [])
                for name, times in self.course_pool.items()
            } for _ in range(size)
        ]

    def crossover(self, parent1, parent2):
        return {
            key: random.choice([parent1[key], parent2[key]])
            for key in parent1
        }

    def mutate(self, individual, mutation_rate=0.1):
        new_ind = deepcopy(individual)
        for key in new_ind:
            if random.random() < mutation_rate:
                new_ind[key] = sum([ScheduleParser.parse(s) for s in random.choice(self.course_pool[key])], [])
        return new_ind

    def run(self, generations=100, pop_size=20):
        population = self.initialize_population(pop_size)
        best = None
        best_score = float('inf')

        for _ in range(generations):
            scored = [(ScheduleEvaluator.evaluate(ind, self.preference), ind) for ind in population]
            scored.sort(key=lambda x: x[0])
            parent1, parent2 = scored[0][1], scored[1][1]
            children = [self.mutate(self.crossover(parent1, parent2)) for _ in range(pop_size)]
            population = children
            for ind in population:
                score = ScheduleEvaluator.evaluate(ind, self.preference)
                if score < best_score:
                    best = ind
                    best_score = score

        return best, best_score

# 시각화
class ScheduleVisualizer:
    @staticmethod
    def draw(schedule):
        root = tk.Tk()
        root.title("최상 시간표")
        root.geometry("750x700")

        canvas = tk.Canvas(root, width=750, height=700, bg="white")
        canvas.pack()

        days = ["월", "화", "수", "목", "금"]
        day_width = 120
        hour_height = 45
        top_margin = 50
        left_margin = 60

        for i, day in enumerate(days):
            x = left_margin + i * day_width
            canvas.create_text(x + day_width // 2, 25, text=day, font=("림아", 12, "bold"))

        for hour in range(1, 13):
            y = top_margin + (hour - 1) * hour_height
            canvas.create_text(30, y + hour_height // 2, text=f"{hour}", font=("림아", 10))
            canvas.create_line(left_margin, y, left_margin + day_width * len(days), y, fill="#ddd")

        for subject, times in schedule.items():
            day_slots = defaultdict(list)
            for day, period in times:
                if day < 5:
                    day_slots[day].append(period)
            for day, periods in day_slots.items():
                periods.sort()
                start = periods[0]
                end = periods[0]
                for i in range(1, len(periods)):
                    if periods[i] == end + 1:
                        end = periods[i]
                    else:
                        ScheduleVisualizer._draw_block(canvas, subject, day, start, end, left_margin, day_width, top_margin, hour_height)
                        start = periods[i]
                        end = periods[i]
                ScheduleVisualizer._draw_block(canvas, subject, day, start, end, left_margin, day_width, top_margin, hour_height)

        root.mainloop()

    @staticmethod
    def _draw_block(canvas, subject, day, start, end, left_margin, day_width, top_margin, hour_height):
        x1 = left_margin + day * day_width + 5
        y1 = top_margin + (start - 1) * hour_height + 2
        x2 = x1 + day_width - 10
        y2 = top_margin + end * hour_height - 2
        canvas.create_rectangle(x1, y1, x2, y2, fill="#ccddff", outline="#444")
        canvas.create_text((x1 + x2)//2, (y1 + y2)//2, text=subject, font=("림아", 10), width=day_width - 20)

# 메인 앱
class SchedulerApp:
    def __init__(self, course_file, filter_file):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_dir, course_file), "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            self.raw_courses = raw_data.get("courses", raw_data)

        with open(os.path.join(base_dir, filter_file), "r", encoding="utf-8") as f:
            filters = json.load(f)
            self.must_take = filters.get("must_take", [])
            self.already_taken = filters.get("already_taken", [])

    def run(self):
        pref = input("선호 유형 (공강최대형 / 몰빵형 / 아침회피형): ").strip()
        grade = int(input("학년 입력 (1-4): "))
        credit = int(input("희망 학점: "))

        selected = CourseSelector.select(self.raw_courses, grade, credit, self.must_take, self.already_taken)

        course_pool = {}
        for course in selected:
            name = f"{course['course_name']} ({course['course_code']}-{course['section']})"
            course_pool.setdefault(name, []).append([course["schedule"]])

        scheduler = GeneticScheduler(course_pool, pref)
        best, score = scheduler.run()

        print("\n학점 최적 시간표:")
        for name, times in best.items():
            print(f"{name}: {times}")
        print(f"\n총 충돌 점수: {score}")

        ScheduleVisualizer.draw(best)


if __name__ == "__main__":
    app = SchedulerApp("courses.json", "filter.json")
    app.run()
