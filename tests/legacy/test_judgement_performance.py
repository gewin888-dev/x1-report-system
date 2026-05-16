#!/usr/bin/env python3
import json
import statistics
import time
from copy import deepcopy

from judgement_engine import judge_room


def room_operating_room():
    return {
        'type_id': 'operating_room',
        'room_name': '手术室01',
        'level_name': 'Ⅰ级',
        'clean_class': 'Ⅰ级',
        'context': {'room_type': 'main-room', 'clean_class_code': 'level1'},
        'params': [
            {'key': 'temperature', 'value': '23', 'result': '23℃'},
            {'key': 'humidity', 'value': '55', 'result': '55%'},
            {'key': 'pressure', 'value': '12', 'result': '12Pa'},
            {'key': 'wind_speed', 'value': '0.27', 'result': '0.27m/s'},
            {'key': 'illumination', 'value': '350', 'result': '350lx'},
            {'key': 'bacteria', 'value': '1', 'result': '1CFU/皿'}
        ],
        'summary': {'result_state': '合格'}
    }


def room_negative_pressure():
    return {
        'type_id': 'negative_pressure',
        'room_name': '负压病房01',
        'level_name': '负压病房',
        'clean_class': '负压病房',
        'context': {'negative_pressure_mode': 'ward-pressure-driven'},
        'params': {
            'humidity': {'values': ['50']},
            'pressure': {'values': ['-8']},
            'airchange': {'values': ['12']},
            'temperature': {'values': ['23']},
            'noise': {'values': ['50']}
        },
        'summary': {'result_state': '合格'}
    }


def room_clean_function_room():
    return {
        'type_id': 'clean_function_room',
        'room_name': 'ICU病房01',
        'level_name': 'Ⅲ级（万级）',
        'clean_class': 'Ⅲ级（万级）',
        'context': {'clean_function_subroom': 'ICU病房'},
        'params': {
            'temperature': {'values': ['23']},
            'humidity': {'values': ['55']},
            'pressure': {'values': ['10']},
            'airchange': {'values': ['18']},
            'noise': {'values': ['48']}
        },
        'summary': {'result_state': '合格'}
    }


def room_gmp_workshop():
    return {
        'type_id': 'gmp_workshop',
        'room_name': 'GMP车间01',
        'level_name': 'C级',
        'clean_class': 'C级',
        'params': {
            'temperature': {'values': ['22']},
            'humidity': {'values': ['55']},
            'pressure': {'values': ['12']},
            'particle': {'values': ['100000']},
            'settling': {'values': ['2']}
        },
        'summary': {'result_state': '合格'}
    }


def room_veterinary_gmp_workshop():
    return {
        'type_id': 'veterinary_gmp_workshop',
        'room_name': '兽药车间01',
        'level_name': 'C级',
        'clean_class': 'C级',
        'params': {
            'temperature': {'values': ['22']},
            'humidity': {'values': ['55']},
            'pressure': {'values': ['12']},
            'particle': {'values': ['100000']},
            'settling': {'values': ['2']}
        },
        'summary': {'result_state': '合格'}
    }


def room_electronics_workshop():
    return {
        'type_id': 'electronics_workshop',
        'room_name': '电子车间01',
        'level_name': 'ISO 7',
        'clean_class': 'ISO 7',
        'context': {'iso_level': 'ISO 7'},
        'params': {
            'temperature': {'values': ['23']},
            'humidity': {'values': ['50']},
            'pressure': {'values': ['10']},
            'particle': {'values': ['10000']},
            'airchange': {'values': ['20']}
        },
        'summary': {'result_state': '合格'}
    }


def room_food_workshop():
    return {
        'type_id': 'food_workshop',
        'room_name': '食品车间01',
        'level_name': 'Ⅲ级',
        'clean_class': 'Ⅲ级',
        'params': {
            'temperature': {'values': ['22']},
            'humidity': {'values': ['60']},
            'pressure': {'values': ['10']},
            'particle': {'values': ['100000']},
            'airchange': {'values': ['18']}
        },
        'summary': {'result_state': '合格'}
    }


def room_animal_room():
    return {
        'type_id': 'animal_room',
        'room_name': '动物房01',
        'level_name': '普通环境',
        'clean_class': '普通环境',
        'context': {'animal_environment': '普通环境'},
        'params': {
            'temperature': {'values': ['22']},
            'humidity': {'values': ['50']},
            'noise': {'values': ['55']},
            'illumination': {'values': ['200']},
            'airchange': {'values': ['12']}
        },
        'summary': {'result_state': '合格'}
    }


def room_bsc():
    return {
        'type_id': 'bsc',
        'room_name': '生物安全柜01',
        'params': {
            'downflow_speed': {'values': ['0.35']},
            'noise': {'values': ['60']},
            'illumination': {'values': ['700']},
            'hepa_integrity': {'values': ['100']}
        },
        'summary': {'result_state': '合格'}
    }


def room_clean_bench():
    return {
        'type_id': 'clean_bench',
        'room_name': '洁净工作台01',
        'params': {
            'avg_speed': {'values': ['0.4']},
            'noise': {'values': ['58']},
            'illumination': {'values': ['320']},
            'settling': {'values': ['1']}
        },
        'summary': {'result_state': '合格'}
    }


def room_ivc():
    return {
        'type_id': 'ivc',
        'room_name': 'IVC笼具01',
        'params': {
            'airflow_speed': {'values': ['0.2']},
            'airchange': {'values': ['55']},
            'airtightness': {'values': ['0']},
            'hepa_integrity': {'values': ['100']}
        },
        'summary': {'result_state': '合格'}
    }


def room_pass_box():
    return {
        'type_id': 'pass_box',
        'room_name': '传递窗01',
        'context': {'pass_box_mode': '_default'},
        'params': {
            'airchange': {'values': ['20']},
            'door_interlock': {'values': ['1']},
            'noise': {'values': ['58']},
            'particle': {'values': ['100000']}
        },
        'summary': {'result_state': '合格'}
    }


def room_bsl():
    return {
        'type_id': 'bsl',
        'room_name': 'BSL01',
        'level_name': 'BSL-2（P2）',
        'clean_class': 'BSL-2（P2）',
        'context': {'bsl_level': 'BSL-2（P2）'},
        'params': {
            'airchange': {'values': ['20']},
            'pressure': {'values': ['-10']},
            'temperature': {'values': ['23']},
            'humidity': {'values': ['50']},
            'noise': {'values': ['55']}
        },
        'summary': {'result_state': '合格'}
    }


CASES = [
    ('operating_room', room_operating_room),
    ('negative_pressure', room_negative_pressure),
    ('clean_function_room', room_clean_function_room),
    ('gmp_workshop', room_gmp_workshop),
    ('veterinary_gmp_workshop', room_veterinary_gmp_workshop),
    ('electronics_workshop', room_electronics_workshop),
    ('food_workshop', room_food_workshop),
    ('animal_room', room_animal_room),
    ('bsc', room_bsc),
    ('clean_bench', room_clean_bench),
    ('ivc', room_ivc),
    ('pass_box', room_pass_box),
    ('bsl', room_bsl),
]

PROJECT = {'project_name': 'judgement_performance_benchmark'}


def bench_case(name, factory, rounds=3000, warmup=200):
    for _ in range(warmup):
        result = judge_room(PROJECT, deepcopy(factory()))
        if result is None:
            raise RuntimeError(f'{name} warmup returned None')

    samples = []
    for _ in range(rounds):
        room = deepcopy(factory())
        t0 = time.perf_counter()
        result = judge_room(PROJECT, room)
        dt = (time.perf_counter() - t0) * 1000
        if result is None:
            raise RuntimeError(f'{name} benchmark returned None')
        samples.append(dt)

    samples_sorted = sorted(samples)
    return {
        'type_id': name,
        'rounds': rounds,
        'avg_ms': statistics.mean(samples),
        'median_ms': statistics.median(samples),
        'min_ms': samples_sorted[0],
        'p95_ms': samples_sorted[int(rounds * 0.95) - 1],
        'max_ms': samples_sorted[-1],
    }


def bench_batch(batch_size=50, rounds=300):
    batch = [factory() for _, factory in CASES]
    batch = (batch * ((batch_size + len(batch) - 1) // len(batch)))[:batch_size]

    for _ in range(30):
        for room in batch:
            judge_room(PROJECT, deepcopy(room))

    samples = []
    for _ in range(rounds):
        rooms = deepcopy(batch)
        t0 = time.perf_counter()
        for room in rooms:
            result = judge_room(PROJECT, room)
            if result is None:
                raise RuntimeError('batch benchmark returned None')
        dt = (time.perf_counter() - t0) * 1000
        samples.append(dt)

    samples_sorted = sorted(samples)
    return {
        'batch_size': batch_size,
        'rounds': rounds,
        'avg_ms': statistics.mean(samples),
        'median_ms': statistics.median(samples),
        'min_ms': samples_sorted[0],
        'p95_ms': samples_sorted[int(rounds * 0.95) - 1],
        'max_ms': samples_sorted[-1],
        'per_room_avg_ms': statistics.mean(samples) / batch_size,
    }


if __name__ == '__main__':
    case_results = [bench_case(name, factory) for name, factory in CASES]
    batch_result = bench_batch()
    summary = {
        'case_results': case_results,
        'batch_result': batch_result,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
