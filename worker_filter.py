"""Q열의 최종 혈압 결과로 재측정 대상자를 구분합니다."""

import re

import pandas as pd


def parse_blood_pressure(value):
    if pd.isna(value):
        return None
    text = str(value).replace('／', '/')
    # 날짜(2026/10/16)를 혈압으로 읽지 않도록 연속된 슬래시는 제외합니다.
    pairs = re.findall(r'(?<![\d/])(\d{2,3})\s*/\s*(\d{2,3})(?![\d/])', text)
    if len(pairs) == 1:
        return tuple(map(int, pairs[0]))
    if len(pairs) > 1:
        return None  # 어느 값이 최종 결과인지 알 수 없는 셀은 자동 분류하지 않습니다.
    systolic = re.search(r'(?:수축기|최고)\s*[:：]?\s*(\d{2,3})(?!\d)', text)
    diastolic = re.search(r'(?:이완기|최저)\s*[:：]?\s*(\d{2,3})(?!\d)', text)
    if systolic and diastolic:
        return int(systolic[1]), int(diastolic[1])
    return None


def select_high_pressure_workers(workers):
    readings = workers['최종혈압결과'].apply(parse_blood_pressure)
    high = readings.apply(lambda bp: bp is not None and (bp[0] >= 150 or bp[1] >= 100))
    # 나이를 확인하지 못한 근로자는 고령자 제외 여부를 판단할 수 없습니다.
    eligible_age = workers['만_나이'].between(0, 62)
    selected = workers.loc[eligible_age & high]
    return selected.sort_values(['협력회사명', '성명']).reset_index(drop=True), readings
