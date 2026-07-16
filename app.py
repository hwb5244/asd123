import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import os
from datetime import datetime
import json
import urllib.request
import urllib.error
import itertools

def init_follow_pool_dict():
    if 'follow_pool_dict' not in st.session_state:
        st.session_state.follow_pool_dict = {}
    
    follow_data_dir = 'follow_data'
    if os.path.exists(follow_data_dir):
        for filename in os.listdir(follow_data_dir):
            if filename.endswith('跟随号.json'):
                filepath = os.path.join(follow_data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        target_period = data.get('target_period', '')
                        if target_period:
                            st.session_state.follow_pool_dict[target_period] = {
                                'unique_follow_nums': data.get('unique_follow_nums', []),
                                'draw_numbers': data.get('draw_numbers', []),
                                'analysis_period': data.get('analysis_period', ''),
                                'source_period': data.get('draw_period', ''),
                                'save_time': data.get('save_time', '')
                            }
                except (json.JSONDecodeError, IOError):
                    pass

init_follow_pool_dict()

# ==================== 【模块0】GitHub Gist API 云端持久化配置 ====================
GIST_CONFIG_KEY = 'gist_config'

def get_gist_config():
    """获取 Gist 配置"""
    if GIST_CONFIG_KEY not in st.session_state:
        st.session_state[GIST_CONFIG_KEY] = {
            'token': '',
            'lottery_gist_id': '',
            'predictions_gist_id': '',
            'hitrates_gist_id': ''
        }
    return st.session_state[GIST_CONFIG_KEY]

def save_gist_config(config):
    """保存 Gist 配置"""
    st.session_state[GIST_CONFIG_KEY] = config

def github_api_request(url, data=None, token=None, method=None):
    """通用的 GitHub API 请求"""
    headers = {
        'Accept': 'application/vnd.github.v3+json'
    }
    if token:
        headers['Authorization'] = f'token {token}'
    if data:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(data).encode('utf-8')
        method = method or 'PATCH'
    else:
        method = method or 'GET'
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8')), response.status
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ''
        return {'error': error_body}, e.code
    except urllib.error.URLError as e:
        return {'error': str(e)}, -1

def get_or_create_gist(token, filename, content, description="快乐8预测系统数据"):
    """获取或创建 Gist（如果已存在则更新）"""
    if not token:
        return None, 'No token provided'
    
    url = f'https://api.github.com/gists'
    
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {token}',
        'Content-Type': 'application/json'
    }
    
    data = json.dumps({
        'description': description,
        'public': False,
        'files': {
            filename: {
                'content': content
            }
        }
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['id'], None
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return None, 'Invalid GitHub Token'
        elif e.code == 404:
            return None, 'Not found'
        else:
            return None, f'HTTP Error: {e.code}'
    except urllib.error.URLError as e:
        return None, f'Network Error: {str(e)}'

def update_gist_content(token, gist_id, filename, content):
    """更新 Gist 内容"""
    if not token or not gist_id:
        return False, 'Missing token or gist_id'
    
    url = f'https://api.github.com/gists/{gist_id}'
    
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {token}',
        'Content-Type': 'application/json'
    }
    
    data = json.dumps({
        'files': {
            filename: {
                'content': content
            }
        }
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method='PATCH')
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return True, None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, 'Gist not found'
        else:
            return False, f'HTTP Error: {e.code}'
    except urllib.error.URLError as e:
        return False, f'Network Error: {str(e)}'

def read_gist_content(token, gist_id, filename):
    """读取 Gist 内容"""
    if not token or not gist_id:
        return None, 'Missing token or gist_id'
    
    url = f'https://api.github.com/gists/{gist_id}'
    
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {token}'
    }
    
    req = urllib.request.Request(url, headers=headers, method='GET')
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            if filename in result['files']:
                return result['files'][filename]['content'], None
            else:
                return None, 'File not found in gist'
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, 'Gist not found'
        else:
            return None, f'HTTP Error: {e.code}'
    except urllib.error.URLError as e:
        return None, f'Network Error: {str(e)}'

def cloud_save_lottery_data(df, config):
    """云端保存基础号码库"""
    if not config['token']:
        return False, 'No token configured'
    
    csv_content = df.to_csv()
    
    if config['lottery_gist_id']:
        success, error = update_gist_content(
            config['token'],
            config['lottery_gist_id'],
            'lottery_data.csv',
            csv_content
        )
        if success:
            return True, None
        if 'not found' in str(error).lower():
            config['lottery_gist_id'] = ''
        else:
            return False, error
    
    gist_id, error = get_or_create_gist(
        config['token'],
        'lottery_data.csv',
        csv_content,
        '快乐8预测系统-基础号码库'
    )
    
    if gist_id:
        config['lottery_gist_id'] = gist_id
        return True, None
    else:
        return False, error

def cloud_load_lottery_data(config):
    """云端加载基础号码库"""
    if not config['token'] or not config['lottery_gist_id']:
        return None
    
    content, error = read_gist_content(
        config['token'],
        config['lottery_gist_id'],
        'lottery_data.csv'
    )
    
    if content:
        from io import StringIO
        df = pd.read_csv(StringIO(content), index_col='期号', dtype={'期号': str})
        return df
    return None

def cloud_save_predictions(predictions_data, config):
    """云端保存所有预测方案"""
    if not config['token']:
        return False, 'No token configured'
    
    content = json.dumps(predictions_data, ensure_ascii=False, indent=2)
    
    if config['predictions_gist_id']:
        success, error = update_gist_content(
            config['token'],
            config['predictions_gist_id'],
            'predictions.json',
            content
        )
        if success:
            return True, None
        if 'not found' in str(error).lower():
            config['predictions_gist_id'] = ''
        else:
            return False, error
    
    gist_id, error = get_or_create_gist(
        config['token'],
        'predictions.json',
        content,
        '快乐8预测系统-预测方案'
    )
    
    if gist_id:
        config['predictions_gist_id'] = gist_id
        return True, None
    else:
        return False, error

def cloud_load_predictions(config):
    """云端加载所有预测方案"""
    if not config['token'] or not config['predictions_gist_id']:
        return None
    
    content, error = read_gist_content(
        config['token'],
        config['predictions_gist_id'],
        'predictions.json'
    )
    
    if content:
        return json.loads(content)
    return None

def cloud_save_hit_rates(hit_rates_data, config):
    """云端保存所有命中率记录"""
    if not config['token']:
        return False, 'No token configured'
    
    content = json.dumps(hit_rates_data, ensure_ascii=False, indent=2)
    
    if config['hitrates_gist_id']:
        success, error = update_gist_content(
            config['token'],
            config['hitrates_gist_id'],
            'hit_rates.json',
            content
        )
        if success:
            return True, None
        if 'not found' in str(error).lower():
            config['hitrates_gist_id'] = ''
        else:
            return False, error
    
    gist_id, error = get_or_create_gist(
        config['token'],
        'hit_rates.json',
        content,
        '快乐8预测系统-命中率记录'
    )
    
    if gist_id:
        config['hitrates_gist_id'] = gist_id
        return True, None
    else:
        return False, error

def cloud_load_hit_rates(config):
    """云端加载所有命中率记录"""
    if not config['token'] or not config['hitrates_gist_id']:
        return None
    
    content, error = read_gist_content(
        config['token'],
        config['hitrates_gist_id'],
        'hit_rates.json'
    )
    
    if content:
        return json.loads(content)
    return None

# ==================== 【预测系统核心辅助函数】 ====================

def get_span(nums):
    """计算跨度（最大号 - 最小号）"""
    return max(nums) - min(nums)

def get_sum_value(nums):
    """计算和值"""
    return sum(nums)

def get_odd_count(nums):
    """计算奇数个数"""
    return sum(1 for n in nums if n % 2 == 1)

def get_even_count(nums):
    """计算偶数个数"""
    return sum(1 for n in nums if n % 2 == 0)

def get_road(n):
    """获取号码的012路（n % 3）"""
    return n % 3

def get_road_count(nums, road):
    """计算某路号码个数"""
    return sum(1 for n in nums if n % 3 == road)

def calculate_omission(data, num):
    """计算号码的遗漏期数（从最新期开始）"""
    for i, (_, row) in enumerate(data.iloc[::-1].iterrows()):
        if num in row.values:
            return i
    return len(data)

def calculate_hotness(data, num, periods=10):
    """计算号码热度（近N期出现次数，使用最新的N期）"""
    recent_data = data.tail(periods)
    count = 0
    for _, row in recent_data.iterrows():
        if num in row.values:
            count += 1
    return count

def get_segments():
    """获取5个分段的区间（彩侠原版位次分段的天然区间）"""
    return [
        (1, 20),
        (10, 40),
        (30, 60),
        (40, 70),
        (60, 80)
    ]

def get_segment(num):
    """获取号码所属分段"""
    segments = get_segments()
    for i, (start, end) in enumerate(segments):
        if start <= num <= end:
            return i
    return -1

def get_hot_level(hotness):
    """根据热度获取冷热等级"""
    if hotness >= 5:
        return '热号'
    elif hotness >= 3:
        return '温号'
    else:
        return '冷号'

def get_all_numbers():
    """获取所有号码1-80"""
    return list(range(1, 81))

def get_road_numbers(road):
    """获取某路的所有号码"""
    return [n for n in range(1, 81) if n % 3 == road]

def get_odd_numbers():
    """获取所有奇数"""
    return [n for n in range(1, 81) if n % 2 == 1]

def get_even_numbers():
    """获取所有偶数"""
    return [n for n in range(1, 81) if n % 2 == 0]

# ==================== 【第一层：宏观边界层】 ====================

def predict_span(data):
    """跨度预判（菲姐・振幅周期法）- 近10期，近5期权重70%，远5期权重30%"""
    if len(data) < 11:
        return None, None, None
    
    recent_10 = data.head(10)
    spans = []
    for _, row in recent_10.iterrows():
        nums = [int(n) for n in row.values if pd.notna(n)]
        spans.append(get_span(nums))
    
    amplitudes = [abs(spans[i] - spans[i-1]) for i in range(1, len(spans))]
    last_amplitude = amplitudes[-1]
    
    last_span = spans[-1]
    
    if last_amplitude <= 3:
        period_type = '收窄期'
        candidates = [last_span + i for i in range(-2, 3) if 1 <= last_span + i <= 79]
    elif last_amplitude <= 9:
        period_type = '正常期'
        candidates = [last_span + i for i in range(-3, 4) if 1 <= last_span + i <= 79]
    else:
        period_type = '放大期'
        candidates = [last_span + i for i in range(-5, 6) if 1 <= last_span + i <= 79]
    
    span_counter_recent = Counter(spans[-5:])
    span_counter_far = Counter(spans[:5])
    
    weighted_counter = {}
    for span in set(spans):
        weighted_counter[span] = span_counter_recent.get(span, 0) * 0.7 + span_counter_far.get(span, 0) * 0.3
    
    most_common_spans = sorted(weighted_counter.items(), key=lambda x: x[1], reverse=True)[:3]
    
    if candidates:
        main_prediction = max(candidates, key=lambda x: weighted_counter.get(x, 0))
        span_range = (main_prediction - 1, main_prediction + 1)
    else:
        main_prediction = last_span
        span_range = (last_span - 1, last_span + 1)
    
    return span_range, period_type, {'spans': spans, 'amplitudes': amplitudes, 'most_common': most_common_spans, 'weighted_counter': weighted_counter}

def predict_odd_even_ratio(data):
    """奇偶比预判（凡哥・冷热转换法）- 近7期+近3期，近3期权重60%，远4期权重40%"""
    if len(data) < 8:
        return None, None
    
    recent_7 = data.head(7)
    recent_3 = data.head(3)
    far_4 = data.iloc[3:7]
    
    s7 = sum(get_odd_count([int(n) for n in row.values if pd.notna(n)]) for _, row in recent_7.iterrows())
    e7 = 140 - s7
    d7 = abs(s7 - e7)
    
    s3 = sum(get_odd_count([int(n) for n in row.values if pd.notna(n)]) for _, row in recent_3.iterrows())
    e3 = 60 - s3
    d3 = abs(s3 - e3)
    
    s_far4 = sum(get_odd_count([int(n) for n in row.values if pd.notna(n)]) for _, row in far_4.iterrows())
    e_far4 = 80 - s_far4
    
    weighted_difference = d3 * 0.6 + abs(s_far4 - e_far4) * 0.4
    
    consecutive_count = 0
    last_odd_count = None
    for _, row in recent_3.iterrows():
        current_odd = get_odd_count([int(n) for n in row.values if pd.notna(n)])
        if last_odd_count is not None:
            if (current_odd >= 12 and last_odd_count >= 12) or (current_odd <= 8 and last_odd_count <= 8):
                consecutive_count += 1
        last_odd_count = current_odd
    
    if consecutive_count >= 1:
        odd_min, odd_max = 8, 10
    elif d7 >= 5 and d3 <= 3:
        if s7 > e7:
            odd_min, odd_max = 8, 10
        else:
            odd_min, odd_max = 11, 13
    else:
        odd_min, odd_max = 9, 11
    
    even_min = 20 - odd_max
    even_max = 20 - odd_min
    
    return (odd_min, odd_max), (even_min, even_max), {'d7': d7, 'd3': d3, 'weighted_diff': weighted_difference, 'consecutive_count': consecutive_count}

def predict_road_counts(data):
    """012路个数预判（菲姐・趋势均值法）- 近10期+近5期，近5期权重60%，远5期权重40%"""
    if len(data) < 11:
        return None, None
    
    recent_10 = data.head(10)
    recent_5 = data.head(5)
    far_5 = data.iloc[5:10]
    
    road_counts_10 = {0: [], 1: [], 2: []}
    for _, row in recent_10.iterrows():
        nums = [int(n) for n in row.values if pd.notna(n)]
        for r in [0, 1, 2]:
            road_counts_10[r].append(get_road_count(nums, r))
    
    road_means_recent5 = {r: sum(road_counts_10[r][-5:]) / 5 for r in [0, 1, 2]}
    road_means_far5 = {r: sum(road_counts_10[r][:5]) / 5 for r in [0, 1, 2]}
    
    road_means_weighted = {r: road_means_recent5[r] * 0.6 + road_means_far5[r] * 0.4 for r in [0, 1, 2]}
    
    road_trends = {}
    for r in [0, 1, 2]:
        counts = road_counts_10[r][-5:]
        if len(counts) >= 2:
            if counts[-1] > counts[0]:
                road_trends[r] = '上升'
            elif counts[-1] < counts[0]:
                road_trends[r] = '下降'
            else:
                road_trends[r] = '平稳'
        else:
            road_trends[r] = '平稳'
    
    n0 = int(round(road_means_weighted[0]))
    n1 = int(round(road_means_weighted[1]))
    n2 = int(round(road_means_weighted[2]))
    
    for r in [0, 1, 2]:
        if road_trends[r] == '上升':
            if r == 0: n0 += 1
            elif r == 1: n1 += 1
            else: n2 += 1
        elif road_trends[r] == '下降':
            if r == 0: n0 -= 1
            elif r == 1: n1 -= 1
            else: n2 -= 1
    
    total = n0 + n1 + n2
    diff = total - 20
    if diff != 0:
        for _ in range(abs(diff)):
            if diff > 0:
                if n0 > n1 and n0 > n2: n0 -= 1
                elif n1 > n2: n1 -= 1
                else: n2 -= 1
            else:
                if n0 < n1 and n0 < n2: n0 += 1
                elif n1 < n2: n1 += 1
                else: n2 += 1
    
    return (n0, n1, n2), {'means': road_means_weighted, 'trends': road_trends, 'means_recent5': road_means_recent5, 'means_far5': road_means_far5}

def predict_sum_range(data):
    """和值区间预判（辅助校验项）"""
    if len(data) < 6:
        return None, None
    
    recent_5 = data.head(5)
    sums = []
    for _, row in recent_5.iterrows():
        nums = [int(n) for n in row.values if pd.notna(n)]
        sums.append(get_sum_value(nums))
    
    last_sum = sums[-1]
    amplitudes = [abs(sums[i] - sums[i-1]) for i in range(1, len(sums))]
    amax = max(amplitudes) if amplitudes else 0
    
    sum_min = int(last_sum - amax * 0.6)
    sum_max = int(last_sum + amax * 0.6)
    
    return (sum_min, sum_max), {'last_sum': last_sum, 'amax': amax}

# ==================== 【第二层：中观杀号层】 ====================

def segment_position_kill(data, all_numbers):
    """第一重：分段位次杀号（彩侠核心方法）- 按位次划分而非号码值范围"""
    if len(data) < 11:
        return []
    
    position_segments = [
        (0, 3),
        (4, 7),
        (8, 11),
        (12, 15),
        (16, 19)
    ]
    
    kill_pool = []
    
    for seg_idx, (start_pos, end_pos) in enumerate(position_segments):
        recent_5 = data.head(5)
        recent_10 = data.head(10)
        full_data = data
        
        def get_segment_mean(d, start_pos, end_pos):
            total = 0
            count = 0
            for _, row in d.iterrows():
                nums = sorted([int(n) for n in row.values if pd.notna(n)])
                if len(nums) > end_pos:
                    seg_nums_in_row = nums[start_pos:end_pos + 1]
                    total += sum(seg_nums_in_row)
                    count += len(seg_nums_in_row)
            return total / count if count > 0 else 40
        
        m5 = get_segment_mean(recent_5, start_pos, end_pos)
        m10 = get_segment_mean(recent_10, start_pos, end_pos)
        m_full = get_segment_mean(full_data, start_pos, end_pos)
        
        m = m5 * 0.5 + m10 * 0.3 + m_full * 0.2
        
        seg_numbers = []
        for _, row in data.iterrows():
            nums = sorted([int(n) for n in row.values if pd.notna(n)])
            if len(nums) > end_pos:
                seg_numbers.extend(nums[start_pos:end_pos + 1])
        seg_numbers = sorted(set(seg_numbers))
        
        if not seg_numbers:
            continue
        
        deviations = []
        for n in seg_numbers:
            deviation = abs(n - m)
            hotness = calculate_hotness(data, n, 10)
            deviations.append((n, deviation, hotness))
        
        deviations.sort(key=lambda x: x[1], reverse=True)
        
        cold_kill = deviations[:2]
        hot_kill = sorted(deviations, key=lambda x: x[2], reverse=True)[:2]
        
        for n, _, _ in cold_kill:
            if n not in kill_pool:
                kill_pool.append(n)
        for n, _, _ in hot_kill:
            if n not in kill_pool:
                kill_pool.append(n)
    
    return sorted(kill_pool)[:20]

def road_count_kill(data, road_counts, all_numbers):
    """第二重：012路个数杀号（菲姐核心方法）"""
    n0, n1, n2 = road_counts
    kill_pool = []
    
    for road, keep_count in [(0, n0 + 2), (1, n1 + 2), (2, n2 + 2)]:
        road_nums = get_road_numbers(road)
        
        hotness_list = []
        for n in road_nums:
            hotness = calculate_hotness(data, n, 10)
            hotness_list.append((n, hotness))
        
        hotness_list.sort(key=lambda x: x[1], reverse=True)
        
        keep_nums = set(n for n, _ in hotness_list[:keep_count])
        
        for n in road_nums:
            if n not in keep_nums:
                kill_pool.append(n)
    
    return sorted(kill_pool)

def generate_final_kill_pool(data, road_counts, all_numbers):
    """生成最终杀号池"""
    first_kill = segment_position_kill(data, all_numbers)
    second_kill = road_count_kill(data, road_counts, all_numbers)
    
    first_set = set(first_kill)
    second_set = set(second_kill)
    
    final_kill = sorted(list(first_set & second_set))
    
    if len(final_kill) < 10:
        cold_nums = []
        for n in second_kill:
            if n not in final_kill:
                cold_nums.append((n, calculate_hotness(data, n, 10)))
        cold_nums.sort(key=lambda x: x[1])
        for n, _ in cold_nums[:10 - len(final_kill)]:
            final_kill.append(n)
    
    final_kill = sorted(final_kill)[:10]
    
    watch_list = sorted(list(first_set - second_set))[:10]
    
    return final_kill, watch_list, {'first_kill': first_kill, 'second_kill': second_kill}

# ==================== 【第三层：微观选号层】 ====================

def build_expert_sources(data, road_counts):
    """构建三位专家的号码来源"""
    n0, n1, n2 = road_counts
    
    feijie_nums = []
    for road, top_n in [(0, 2), (1, 3), (2, 3)]:
        road_nums = get_road_numbers(road)
        hotness_list = [(n, calculate_hotness(data, n, 10)) for n in road_nums]
        hotness_list.sort(key=lambda x: x[1], reverse=True)
        feijie_nums.extend([n for n, _ in hotness_list[:top_n]])
    
    caixia_nums = []
    position_segments = [
        (0, 3),
        (4, 7),
        (8, 11),
        (12, 15),
        (16, 19)
    ]
    for start_pos, end_pos in position_segments:
        seg_nums = []
        for _, row in data.iterrows():
            nums = sorted([int(n) for n in row.values if pd.notna(n)])
            if len(nums) > end_pos:
                seg_nums.extend(nums[start_pos:end_pos + 1])
        seg_nums = sorted(set(seg_nums))
        if seg_nums:
            hotness_list = [(n, calculate_hotness(data, n, 10)) for n in seg_nums]
            hotness_list.sort(key=lambda x: x[1], reverse=True)
            caixia_nums.extend([n for n, _ in hotness_list[:3]])
    
    fange_nums = []
    road_2_nums = get_road_numbers(2)
    hotness_list = [(n, calculate_hotness(data, n, 10)) for n in road_2_nums]
    hotness_list.sort(key=lambda x: x[1], reverse=True)
    fange_nums.extend([n for n, _ in hotness_list[:5]])
    
    odd_nums = get_odd_numbers()
    even_nums = get_even_numbers()
    odd_hotness = sum(calculate_hotness(data, n, 10) for n in odd_nums) / len(odd_nums)
    even_hotness = sum(calculate_hotness(data, n, 10) for n in even_nums) / len(even_nums)
    if odd_hotness > even_hotness:
        fange_nums.extend([n for n in odd_nums if calculate_hotness(data, n, 10) >= 2][:5])
    else:
        fange_nums.extend([n for n in even_nums if calculate_hotness(data, n, 10) >= 2][:5])
    
    return {
        'feijie': sorted(set(feijie_nums)),
        'caixia': sorted(set(caixia_nums)),
        'fange': sorted(set(fange_nums))
    }

def calculate_overlap_score(sources, num):
    """计算号码重合度评分"""
    score = 0
    if num in sources['feijie']:
        score += 1
    if num in sources['caixia']:
        score += 1
    if num in sources['fange']:
        score += 1
    return score

def generate_gradient_pools(data, sources, watch_list, span_range, odd_range, road_counts):
    """梯度式号码池生成 - 动态评分版本"""
    all_numbers = get_all_numbers()
    
    scored_nums = []
    for n in all_numbers:
        score = calculate_overlap_score(sources, n)
        omission = calculate_omission(data, n)
        hotness = calculate_hotness(data, n, 10)
        
        hotness_recent3 = calculate_hotness(data, n, 3)
        hotness_trend = hotness_recent3 - (hotness - hotness_recent3) / 7
        
        omission_score = 0
        if 3 <= omission <= 7:
            omission_score = 2
        elif omission >= 8:
            omission_score = 1
        elif omission <= 2:
            omission_score = -1
        
        dynamic_score = score * 3 + omission_score + hotness_trend * 0.5
        
        scored_nums.append((n, dynamic_score, score, omission, hotness))
    
    scored_nums.sort(key=lambda x: (-x[1], -x[2], x[3], -x[4]))
    
    def validate_pool(pool, span_range, odd_range, road_counts, min_size=5):
        if not pool:
            return False
        nums = list(pool)
        if len(nums) < min_size:
            return True
        
        span = max(nums) - min(nums)
        odd_count = get_odd_count(nums)
        n0 = get_road_count(nums, 0)
        n1 = get_road_count(nums, 1)
        n2 = get_road_count(nums, 2)
        
        span_ok = span_range[0] <= span <= span_range[1]
        odd_ok = odd_range[0] <= odd_count <= odd_range[1]
        road_ok = abs(n0 - road_counts[0]) <= 1 and abs(n1 - road_counts[1]) <= 1 and abs(n2 - road_counts[2]) <= 1
        
        return span_ok and odd_ok and road_ok
    
    pools = {}
    
    scored_list = [n for n, _, _, _, _ in scored_nums]
    
    dan_dan = []
    for n, dyn_score, score, omission, hotness in scored_nums:
        if score >= 2 and 3 <= omission <= 7:
            dan_dan = [n]
            break
    if not dan_dan:
        dan_dan = [scored_list[0]]
    
    pools['独胆'] = dan_dan
    
    shuang_dan = []
    remaining = [n for n in scored_list if n != dan_dan[0]]
    for n in remaining[:5]:
        pool = [dan_dan[0], n]
        if validate_pool(pool, span_range, odd_range, road_counts):
            shuang_dan.append(pool)
        else:
            shuang_dan.append(pool)
    pools['双胆'] = shuang_dan[:5]
    
    san_ma = []
    for sd in shuang_dan[:4]:
        for n in remaining:
            if n not in sd:
                pool = sd + [n]
                if validate_pool(pool, span_range, odd_range, road_counts):
                    san_ma.append(pool)
                    break
    pools['三码'] = san_ma[:4]
    
    core_5 = []
    used = set(dan_dan)
    for n, dyn_score, score, omission, hotness in scored_nums:
        if n not in used:
            core_5.append(n)
            used.add(n)
            if len(core_5) == 4:
                break
    core_5 = dan_dan + core_5
    pools['5码核心池'] = core_5
    
    pool_10 = core_5.copy()
    for n, dyn_score, score, omission, hotness in scored_nums:
        if n not in pool_10:
            pool_10.append(n)
            if len(pool_10) == 10:
                break
    pools['10码池'] = pool_10
    
    pool_15 = pool_10.copy()
    warm_nums = []
    for n, dyn_score, score, omission, hotness in scored_nums:
        if n not in pool_15 and score >= 1 and 3 <= omission <= 7:
            warm_nums.append(n)
    pool_15.extend(warm_nums[:5])
    pools['15码池'] = pool_15
    
    pool_17 = pool_15.copy()
    cold_watch = sorted([n for n in watch_list], key=lambda x: calculate_hotness(data, x, 10))[:2]
    pool_17.extend(cold_watch)
    pools['17码池'] = pool_17
    
    pool_20 = pool_17.copy()
    cold_nums = []
    for n, dyn_score, score, omission, hotness in scored_nums:
        if n not in pool_20 and omission >= 8:
            cold_nums.append(n)
    pool_20.extend(cold_nums[:3])
    pools['20码池'] = pool_20
    
    for key in pools:
        pools[key] = sorted(pools[key])
    
    return pools, {'scored_nums': scored_nums}

# ==================== 【模块1】全局配置与数据持久化 ====================
st.set_page_config(
    page_title='快乐8多周期三流派预测系统',
    page_icon='🎱',
    layout='wide',
    initial_sidebar_state='expanded'
)

# 预加载的官方开奖数据（2025250-2025301，共51期）
INITIAL_DATA = [
    ["2025301",8,9,11,13,14,18,21,30,33,34,40,44,46,51,58,62,65,67,77,78],
    ["2025300",4,11,20,26,29,35,37,39,47,54,55,59,63,64,65,67,70,71,72,74],
    ["2025299",9,10,11,19,23,25,39,41,45,51,53,54,59,60,63,65,68,69,70,75],
    ["2025298",3,5,8,13,15,19,20,25,26,27,28,30,33,34,37,45,47,67,69,77],
    ["2025297",4,8,9,11,14,19,36,40,42,48,49,52,56,59,66,68,69,73,76,79],
    ["2025296",7,9,11,14,23,26,31,32,36,37,42,43,48,52,53,54,55,58,64,68],
    ["2025295",2,7,12,13,21,22,23,24,26,34,38,43,53,57,67,69,71,72,77,80],
    ["2025294",1,2,8,15,21,22,24,26,27,30,38,41,43,45,46,50,61,62,70,78],
    ["2025293",5,7,17,19,23,34,35,37,38,41,46,53,56,63,65,66,67,69,71,79],
    ["2025292",1,2,3,10,11,15,16,25,38,40,43,47,50,52,57,62,64,71,78,80],
    ["2025291",4,7,11,17,20,22,27,29,32,34,37,48,55,64,68,69,71,73,74,78],
    ["2025290",8,9,10,19,20,25,26,30,32,35,40,41,45,47,49,51,54,65,68,75],
    ["2025289",3,6,7,10,11,13,14,15,31,35,40,41,43,45,55,57,66,72,73,75],
    ["2025288",4,11,15,16,22,23,37,46,47,49,51,53,54,55,60,62,70,72,73,74],
    ["2025287",1,6,17,18,21,22,23,24,31,32,40,43,48,49,52,57,58,60,68,79],
    ["2025286",6,12,14,16,22,24,25,34,38,39,41,42,43,54,57,58,61,62,68,74],
    ["2025285",5,6,7,9,11,19,24,27,28,29,38,39,41,45,46,63,67,68,73,80],
    ["2025284",10,11,14,19,20,26,29,30,35,37,40,41,45,46,59,68,70,77,78,80],
    ["2025283",2,4,13,19,20,23,29,31,37,40,47,52,53,54,55,63,64,65,68,69],
    ["2025282",5,9,12,15,16,20,22,24,26,30,35,38,39,47,49,56,62,66,72,74],
    ["2025281",8,15,23,24,28,34,35,36,38,43,45,49,51,53,64,67,69,71,74,75],
    ["2025280",6,10,14,15,16,25,32,36,46,49,50,59,64,68,70,72,73,77,78,79],
    ["2025279",1,5,6,14,25,32,35,40,45,47,53,62,63,67,68,70,71,72,75,78],
    ["2025278",4,5,7,8,10,15,17,18,22,26,30,33,39,42,48,50,63,68,72,77],
    ["2025277",9,11,13,14,20,22,39,43,48,52,54,55,57,64,68,69,72,73,75,80],
    ["2025276",3,17,21,22,24,30,33,34,41,44,45,47,48,59,61,68,69,76,78,79],
    ["2025275",7,9,13,14,28,32,33,34,35,37,48,50,51,56,57,59,65,69,72,76],
    ["2025274",2,3,10,18,26,31,33,34,46,49,50,51,54,55,60,62,74,75,76,80],
    ["2025273",8,9,11,13,14,18,20,24,28,30,31,32,38,39,40,46,62,64,69,70],
    ["2025272",3,6,9,10,11,13,14,16,20,22,25,43,47,50,60,61,62,68,73,79],
    ["2025271",1,3,7,15,17,20,27,37,41,42,47,48,53,54,60,62,63,68,77,78],
    ["2025270",2,8,10,20,21,27,28,30,33,36,43,48,49,52,60,61,64,71,75,79],
    ["2025269",1,8,10,15,19,20,24,30,33,43,49,50,56,57,60,67,70,73,78,80],
    ["2025268",5,12,16,18,19,26,31,33,38,39,41,42,49,54,59,64,65,70,73,77],
    ["2025267",8,13,20,21,25,34,37,39,45,47,50,57,58,60,65,71,72,75,78,79],
    ["2025266",1,5,9,13,16,17,25,28,29,33,34,38,45,47,48,55,62,71,73,78],
    ["2025265",2,9,11,16,18,27,28,35,36,38,49,52,54,60,62,64,66,72,77,78],
    ["2025264",6,10,15,16,20,24,25,28,34,35,37,38,42,44,45,49,54,66,69,80],
    ["2025263",4,5,11,13,14,20,23,24,27,32,33,42,45,55,58,62,64,70,79,80],
    ["2025262",8,10,14,19,27,31,33,40,42,44,46,47,49,54,58,60,67,70,75,77],
    ["2025261",3,10,15,17,19,22,23,25,31,35,36,42,60,61,62,65,70,73,76,77],
    ["2025260",3,8,10,11,13,16,21,24,27,38,41,48,54,58,59,61,62,66,69,71],
    ["2025259",4,7,9,19,20,30,33,35,44,45,48,49,50,51,52,70,71,72,74,78],
    ["2025258",1,5,10,12,16,23,25,28,29,36,40,46,51,55,58,64,66,71,76,80],
    ["2025257",1,8,13,15,22,34,36,38,42,43,49,50,51,65,66,67,70,71,79,80],
    ["2025256",8,13,18,29,34,35,39,41,43,45,46,47,57,64,68,71,73,74,75,78],
    ["2025255",5,13,15,21,25,26,27,31,37,39,46,50,54,56,57,59,65,70,78,79],
    ["2025254",16,18,20,29,32,36,37,41,52,53,54,55,56,57,65,69,70,74,75,76],
    ["2025253",3,10,20,23,27,30,32,35,44,48,50,51,53,56,57,63,65,68,70,72],
    ["2025252",13,18,19,26,27,30,33,37,41,43,47,49,53,58,61,64,68,71,73,76],
    ["2025251",1,2,4,14,15,23,25,26,27,30,36,39,42,44,46,52,55,62,65,66],
    ["2025250",1,2,6,16,20,21,23,26,27,29,30,34,40,43,59,63,65,71,79,80],
    # 2025302-2025351期开奖号码
    ["2025302",1,2,8,12,14,15,24,26,27,40,43,53,59,62,65,66,68,74,77,80],
    ["2025303",1,2,10,11,15,25,33,43,44,50,52,54,55,56,57,60,62,69,74,78],
    ["2025304",1,6,17,19,21,30,31,32,33,35,42,49,50,52,59,65,66,68,75,78],
    ["2025305",1,8,9,10,15,18,21,27,32,40,41,43,46,47,50,54,56,60,67,74],
    ["2025306",3,6,7,14,17,20,21,31,32,36,44,47,48,51,52,55,61,70,76,77],
    ["2025307",3,6,12,13,14,16,26,27,41,42,45,49,52,55,63,66,72,75,79,80],
    ["2025308",5,7,8,11,16,17,21,25,29,36,37,39,41,42,46,53,59,62,75,77],
    ["2025309",9,19,20,21,23,30,38,39,40,41,44,48,53,54,58,60,61,65,68,72],
    ["2025310",1,6,7,11,14,15,18,28,30,31,35,48,55,59,61,65,67,69,70,76],
    ["2025311",2,4,15,19,23,24,29,34,37,43,44,55,56,60,62,66,70,73,77,79],
    ["2025312",3,7,16,17,18,19,23,24,26,29,30,37,43,48,57,62,67,72,79,80],
    ["2025313",1,7,22,23,28,29,31,37,43,49,53,55,57,63,64,69,73,76,79,80],
    ["2025314",5,14,15,16,39,40,41,43,44,48,49,53,57,58,60,63,73,76,79,80],
    ["2025315",3,6,8,9,10,14,15,19,23,26,38,40,47,58,61,68,69,74,75,80],
    ["2025316",6,9,16,17,18,20,28,31,33,42,53,54,55,57,60,62,65,67,72,75],
    ["2025317",1,9,10,14,17,21,29,31,36,38,41,44,55,56,58,62,67,68,74,79],
    ["2025318",1,4,15,17,26,27,30,31,36,37,40,41,47,53,54,62,66,74,75,78],
    ["2025319",2,7,8,10,11,21,26,27,28,29,39,46,48,59,61,62,74,77,78,79],
    ["2025320",1,3,8,12,16,17,20,22,25,27,30,32,46,48,52,53,55,62,65,78],
    ["2025321",7,13,14,15,16,18,19,33,35,40,48,52,54,66,69,71,72,74,75,76],
    ["2025322",1,5,6,10,11,17,22,25,28,34,36,39,41,47,57,62,65,71,73,76],
    ["2025323",1,13,18,19,22,24,35,40,44,45,50,51,53,54,57,63,69,71,73,75],
    ["2025324",9,13,20,26,28,32,39,42,43,46,47,49,50,60,61,62,63,64,66,79],
    ["2025325",5,8,10,15,16,17,19,22,26,34,37,41,47,55,57,62,63,65,67,75],
    ["2025326",7,17,22,24,27,28,37,41,42,49,51,53,57,58,69,73,76,77,79,80],
    ["2025327",6,7,10,15,16,17,19,21,22,25,27,35,36,40,44,45,47,56,62,74],
    ["2025328",1,4,6,10,13,27,28,31,38,48,53,58,60,61,68,71,73,74,77,79],
    ["2025329",2,4,10,11,15,17,18,23,26,27,30,33,41,48,52,54,55,59,60,69],
    ["2025330",11,16,17,27,30,31,33,34,37,38,39,44,50,55,58,61,63,70,71,74],
    ["2025331",5,6,7,8,14,18,22,23,25,31,40,52,59,63,71,72,73,76,77,79],
    ["2025332",2,5,6,8,10,16,26,27,35,40,48,49,54,56,57,58,61,72,73,79],
    ["2025333",4,9,11,16,19,20,22,24,28,32,33,37,38,41,46,49,66,71,72,74],
    ["2025334",2,3,8,16,18,24,30,32,33,35,36,42,49,54,63,64,72,74,77,78],
    ["2025335",2,5,13,14,16,17,27,34,39,45,48,50,55,57,58,60,74,76,78,79],
    ["2025336",1,6,8,10,11,13,20,26,27,29,41,43,54,55,59,61,62,71,76,80],
    ["2025337",3,6,8,10,16,20,28,32,33,43,46,48,49,53,60,68,69,76,77,78],
    ["2025338",2,3,9,11,14,25,28,29,34,36,38,39,49,50,58,68,69,71,77,78],
    ["2025339",3,6,7,9,14,19,25,26,31,32,35,36,37,38,60,62,66,67,68,75],
    ["2025340",1,9,14,15,16,20,21,24,29,31,40,45,46,47,49,63,65,68,71,74],
    ["2025341",4,8,9,11,15,19,21,23,24,25,26,37,38,43,45,46,52,63,64,74],
    ["2025342",5,6,10,22,25,33,41,42,53,55,58,59,60,63,66,70,71,73,77,80],
    ["2025343",4,11,23,26,29,30,33,35,44,46,49,50,55,56,58,60,62,65,69,80],
    ["2025344",1,4,6,11,12,20,23,26,30,33,37,40,44,50,52,53,67,68,72,73],
    ["2025345",6,10,11,12,14,19,30,32,35,38,39,41,43,45,46,48,61,67,76,79],
    ["2025346",3,6,8,13,14,23,25,26,28,30,33,38,40,41,42,48,51,56,68,69],
    ["2025347",3,10,11,14,17,20,22,28,34,40,45,46,48,51,55,56,67,71,72,73],
    ["2025348",2,19,20,22,24,25,30,33,35,39,41,49,53,54,55,60,63,66,75,80],
    ["2025349",7,8,18,20,22,23,28,40,41,43,45,47,48,51,53,58,64,67,78,80],
    ["2025350",1,5,6,20,24,30,32,33,35,36,37,38,40,52,55,62,64,70,72,76],
    ["2025351",5,12,14,17,19,21,24,25,31,32,39,42,46,49,50,52,57,63,68,72],
    # 2026001-2026015期开奖号码
    ["2026001",2,5,6,11,24,25,27,32,34,35,39,41,44,51,54,62,70,71,72,75],
    ["2026002",3,8,10,17,22,24,25,28,39,51,61,62,67,69,70,71,72,73,74,80],
    ["2026003",2,7,14,16,22,25,28,31,39,42,47,53,54,55,61,68,69,72,73,78],
    ["2026004",4,5,9,13,16,21,23,24,32,35,37,38,45,50,52,54,55,62,63,64],
    ["2026005",7,8,9,14,18,21,24,26,33,35,41,43,49,54,56,59,60,63,68,76],
    ["2026006",3,5,7,9,19,28,30,32,34,38,49,52,56,61,62,66,73,76,78,79],
    ["2026007",3,13,15,18,20,21,25,32,42,43,45,54,57,62,63,68,72,74,76,80],
    ["2026008",2,4,15,20,21,23,24,34,47,50,51,52,57,58,60,61,66,71,77,79],
    ["2026009",3,4,8,17,18,31,34,37,42,46,47,55,56,61,65,70,74,75,76,80],
    ["2026010",6,7,13,16,19,27,33,37,39,42,43,44,55,59,62,64,65,67,76,80],
    ["2026011",1,3,12,16,22,25,27,30,32,49,52,56,59,61,62,63,66,68,69,79],
    ["2026012",4,11,12,15,16,20,21,26,27,28,30,32,33,41,53,60,62,64,65,76],
    ["2026013",1,5,9,10,11,12,14,15,16,22,28,32,37,41,44,64,72,77,78,80],
    ["2026014",6,12,13,14,18,24,28,29,30,34,38,43,49,52,59,60,64,74,78,80],
    ["2026015",2,8,9,11,14,17,18,19,27,29,31,34,36,41,55,60,64,70,72,79]
]

# 数据持久化函数
def init_lottery_data():
    """初始化或加载基础号码库（优先云端，后本地）"""
    config = get_gist_config()
    
    if config['token']:
        cloud_df = cloud_load_lottery_data(config)
        if cloud_df is not None:
            cloud_df = cloud_df.sort_index(ascending=True)
            local_df = None
            if os.path.exists('lottery_data_v2.csv'):
                local_df = pd.read_csv('lottery_data_v2.csv', index_col='期号', dtype={'期号': str})
                local_df = local_df.sort_index(ascending=True)
            
            if local_df is not None:
                if len(cloud_df) >= len(local_df):
                    save_lottery_data(cloud_df)
                    return cloud_df
                else:
                    return local_df
            return cloud_df
    
    if not os.path.exists('lottery_data_v2.csv'):
        df = pd.DataFrame(INITIAL_DATA, columns=['期号'] + [f'第{i}位' for i in range(1, 21)])
        df['期号'] = df['期号'].astype(str)
        df.set_index('期号', inplace=True)
        df = df.sort_index(ascending=True)
        df.to_csv('lottery_data_v2.csv')
        return df
    else:
        df = pd.read_csv('lottery_data_v2.csv', index_col='期号', dtype={'期号': str})
        df = df.sort_index(ascending=True)
        return df

def save_lottery_data(df):
    """保存基础号码库到本地并同步云端"""
    df.to_csv('lottery_data_v2.csv')
    config = get_gist_config()
    if config['token']:
        with st.spinner('正在同步到云端...'):
            success, error = cloud_save_lottery_data(df, config)
            if success:
                save_gist_config(config)
                st.success('✅ 数据已成功保存到本地 lottery_data_v2.csv，并已同步到云端')
            else:
                st.warning(f'⚠️ 数据已保存到本地，但云端同步失败：{error}')
                st.info('请检查 GitHub Token 是否有效')
    else:
        st.success('✅ 数据已成功保存到本地 lottery_data_v2.csv')

def save_prediction(prediction_data, period):
    """保存预测方案到本地并同步云端"""
    if not os.path.exists('predictions'):
        os.makedirs('predictions')
    
    filename = f'predictions/{period}_prediction.json'
    
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        if existing_data.get('step5_core_pool') == prediction_data.get('step5_core_pool') and \
           existing_data.get('step6_combinations') == prediction_data.get('step6_combinations'):
            return filename
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(prediction_data, f, ensure_ascii=False, indent=2)
    
    sync_predictions_to_cloud()
    
    return filename

def sync_predictions_to_cloud():
    """同步预测数据到云端"""
    predictions = load_all_predictions()
    config = get_gist_config()
    if config['token']:
        success, error = cloud_save_predictions(predictions, config)
        if success:
            save_gist_config(config)
            return True, None
        return False, error
    return False, 'No token'

def load_all_predictions():
    """加载所有已保存的预测记录（优先本地）"""
    predictions = {}
    if os.path.exists('predictions'):
        for file in os.listdir('predictions'):
            if file.endswith('_prediction.json'):
                period = file.replace('_prediction.json', '')
                filepath = os.path.join('predictions', file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        predictions[period] = json.load(f)
                except:
                    pass
    return dict(sorted(predictions.items()))

def save_hit_rate(prediction_period, result_period, hit_rate_data):
    """保存命中率到本地并同步云端"""
    if not os.path.exists('hit_rates'):
        os.makedirs('hit_rates')
    key = f'{prediction_period}_{result_period}'
    filepath = os.path.join('hit_rates', f'{key}_hitrate.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(hit_rate_data, f, ensure_ascii=False, indent=2)
    sync_hit_rates_to_cloud()
    return filepath

def sync_hit_rates_to_cloud():
    """同步命中率数据到云端"""
    hit_rates = load_all_hit_rates()
    config = get_gist_config()
    if config['token']:
        success, error = cloud_save_hit_rates(hit_rates, config)
        if success:
            save_gist_config(config)
            return True, None
        return False, error
    return False, 'No token'

def load_all_hit_rates():
    """加载所有已保存的命中率记录"""
    hit_rates = {}
    if os.path.exists('hit_rates'):
        for file in os.listdir('hit_rates'):
            if file.endswith('_hitrate.json'):
                filepath = os.path.join('hit_rates', file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        key = f"{data['prediction_period']}_{data['result_period']}"
                        hit_rates[key] = data
                except:
                    pass
    return dict(sorted(hit_rates.items(), key=lambda x: x[0], reverse=True))

# 加载数据到Session State（全局通用调用）
if 'lottery_data' not in st.session_state:
    st.session_state.lottery_data = init_lottery_data()

# ==================== 【模块2】侧边栏导航与全局状态 ====================
with st.sidebar:
    st.title('🎱 快乐8预测系统')
    st.divider()
    st.markdown('### 📊 系统状态')
    st.write(f'当前数据量：**{len(st.session_state.lottery_data)}** 期')
    st.write(f'最新期号：**{st.session_state.lottery_data.index[-1]}**')
    st.divider()
    st.markdown('### ☁️ 云端同步设置')
    
    config = get_gist_config()
    
    with st.expander('⚙️ GitHub Gist 配置', expanded=not bool(config['token'])):
        st.caption('用于将数据同步到 GitHub Gist，防止程序重启后数据丢失')
        
        token_input = st.text_input(
            'GitHub Personal Access Token',
            value=config['token'],
            type='password',
            help='需要创建 GitHub Personal Access Token，勾选 gist 权限'
        )
        
        if st.button('💾 保存 Token', use_container_width=True):
            if token_input:
                test_result, error = get_or_create_gist(
                    token_input,
                    'test_connection.txt',
                    'Connection test',
                    '快乐8预测系统-连接测试'
                )
                if test_result:
                    config['token'] = token_input
                    save_gist_config(config)
                    st.success('✅ Token 验证成功！')
                    st.rerun()
                else:
                    st.error(f'❌ Token 验证失败：{error}')
            else:
                st.warning('⚠️ 请输入 Token')
        
        with st.expander('📖 如何获取 GitHub Token？'):
            st.markdown('''
            **获取 GitHub Personal Access Token 步骤：**
            
            1. 登录 GitHub，点击右上角头像 → **Settings**
            2. 左侧菜单找到 **Developer settings**
            3. 点击 **Personal access tokens** → **Tokens (classic)**
            4. 点击 **Generate new token (classic)**
            5. 勾选权限：**gist**（允许创建和编辑 Gist）
            6. 设置有效期，点击生成
            7. 复制生成的 Token 并粘贴到上方输入框
            
            **注意：** Token 只会显示一次，请妥善保管！
            ''')
    
    if config['token']:
        st.success('✅ 云端同步已启用')
        
        with st.expander('📋 云端存储状态', expanded=False):
            st.write(f'号码库 Gist ID：{config["lottery_gist_id"][:8] + "..." if config["lottery_gist_id"] else "未设置"}')
            st.write(f'预测方案 Gist ID：{config["predictions_gist_id"][:8] + "..." if config["predictions_gist_id"] else "未设置"}')
            st.write(f'命中率 Gist ID：{config["hitrates_gist_id"][:8] + "..." if config["hitrates_gist_id"] else "未设置"}')
            
            col_sync1, col_sync2 = st.columns(2)
            with col_sync1:
                if st.button('🔄 手动同步', use_container_width=True):
                    with st.spinner('正在同步...'):
                        df = st.session_state.lottery_data
                        success1, _ = cloud_save_lottery_data(df, config)
                        success2, _ = cloud_save_predictions(load_all_predictions(), config)
                        success3, _ = cloud_save_hit_rates(load_all_hit_rates(), config)
                        if success1 and success2 and success3:
                            save_gist_config(config)
                            st.success('✅ 同步成功！')
                        else:
                            st.error('⚠️ 部分同步失败')
            
            with col_sync2:
                if st.button('📥 从云端恢复', use_container_width=True):
                    with st.spinner('正在从云端恢复...'):
                        cloud_df = cloud_load_lottery_data(config)
                        if cloud_df is not None:
                            st.session_state.lottery_data = cloud_df.sort_index(ascending=True)
                            save_lottery_data(st.session_state.lottery_data)
                            st.success('✅ 数据已从云端恢复！')
                            st.rerun()
                        else:
                            st.warning('⚠️ 云端暂无数据')
    
    st.divider()
    st.markdown('### 📝 开发日志')
    st.info('V3.1 已上线：新增 GitHub Gist 云端同步功能，数据从此不丢失！')

# ==================== 【模块3】主界面Tab布局 ====================
tabs = st.tabs([
    '📚 Tab 1 号码库管理',
    '📊 Tab 2 数据分析',
    '🔗 Tab 3 相随号数据（预留）',
    '🔍 Tab 4 深度复盘',
    '🎯 Tab 5 前段库（1-40）',
    '📈 Tab 6 后段库（41-80）',
    '📋 Tab 7 体系全流程 SOP',
    '🔮 Tab 8 预测结果',
    '⚙️ Tab 9 预留板块',
    '🎯 Tab 10 三维融合预测',
    '📚 Tab 11 三维融合体系',
    '🔗 Tab 12 选号策略体系'
])

# ==================== 【Tab 1】号码库管理 ====================
with tabs[0]:
    st.header('📚 基础号码库管理')
    st.markdown('''<div style="background-color: #f0f2f6; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
    <p style="font-size: 16px; line-height: 1.6;">全局通用调用的基础数据库，支持新增、修改、查看开奖号码。</p>
    <ul style="margin-top: 10px; font-size: 14px;">
    <li>✅ 支持查看历史开奖数据</li>
    <li>✅ 新增最新开奖号码</li>
    <li>✅ 修改历史开奖数据</li>
    <li>✅ 自动排序和数据持久化</li>
    </ul>
    </div>''', unsafe_allow_html=True)

    # 左右分栏布局
    col_left, col_right = st.columns([1, 1.5])
    
    # 左侧：新增和修改
    with col_left:
        # 1. 新增数据
        st.subheader('➕ 新增开奖号码')
        
        # 自动生成下一期期号（最新期号+1）
        def generate_next_period():
            if not st.session_state.lottery_data.empty:
                max_period = st.session_state.lottery_data.index[-1]
                # 解析期号：前4位是年份，后3位是期数
                year = int(max_period[:4])
                period_num = int(max_period[4:])
                # 期数+1，超过999则进入下一年
                next_period_num = period_num + 1
                if next_period_num > 999:
                    next_year = year + 1
                    next_period_num = 1
                else:
                    next_year = year
                return f"{next_year}{next_period_num:03d}"
            else:
                # 默认起始期号
                return "2025001"
        
        next_period = generate_next_period()
        
        with st.form(key='add_form'):
            new_period = st.text_input('期号', value=next_period, placeholder='如 2025001', help='7位数字格式：年+期号')
            new_nums_input = st.text_input(
                '开奖号码',
                placeholder='20个号码，空格/逗号分隔',
                help='1-80之间，自动排序'
            )
            submit_button = st.form_submit_button('✅ 新增号码', type='primary', use_container_width=True)
            
            if submit_button:
                success = False
                error_msg = ''
                
                # 验证期号（7位数字格式）
                if not new_period:
                    error_msg = '❌ 请输入期号'
                elif not new_period.isdigit():
                    error_msg = '❌ 期号只能包含数字'
                elif len(new_period) != 7:
                    error_msg = '❌ 期号必须是7位数字（格式：年+期号，如2025001）'
                elif new_period in st.session_state.lottery_data.index:
                    error_msg = f'❌ 期号 {new_period} 已存在，请选择其他期号'
                else:
                    # 处理号码输入
                    try:
                        # 支持多种分隔符：空格、逗号、分号、换行等
                        cleaned_input = new_nums_input.replace(',', ' ').replace(';', ' ').replace('\n', ' ')
                        nums = [int(x.strip()) for x in cleaned_input.split() if x.strip()]
                        
                        if len(nums) == 0:
                            error_msg = '❌ 未检测到任何号码，请输入开奖号码'
                        elif len(nums) < 20:
                            error_msg = f'❌ 号码数量不足，当前输入 {len(nums)} 个，需要 20 个'
                        elif len(nums) > 20:
                            error_msg = f'❌ 号码数量超出，当前输入 {len(nums)} 个，需要 20 个'
                        else:
                            # 检查号码范围
                            out_of_range = [n for n in nums if n < 1 or n > 80]
                            if out_of_range:
                                error_msg = f'❌ 号码超出范围(1-80)：{", ".join(map(str, sorted(out_of_range)))}'
                            else:
                                # 检查重复号码
                                duplicates = []
                                seen = set()
                                for n in nums:
                                    if n in seen:
                                        duplicates.append(n)
                                    seen.add(n)
                                if duplicates:
                                    error_msg = f'❌ 存在重复号码：{", ".join(map(str, sorted(set(duplicates))))}'
                                else:
                                    # 一切正常，保存数据
                                    nums.sort()
                                    st.session_state.lottery_data.loc[new_period] = nums
                                    st.session_state.lottery_data = st.session_state.lottery_data.sort_index(ascending=True)
                                    save_lottery_data(st.session_state.lottery_data)
                                    success = True
                    except ValueError as e:
                        error_msg = f'❌ 输入包含无效字符：{str(e)}'
                
                if success:
                    st.success(f'✅ 期号 {new_period} 添加成功！')
                    st.info(f'号码已自动排序：{" ".join(map(str, nums))}')
                    if len(st.session_state.lottery_data) >= 10:
                        st.session_state['auto_run_sop'] = True
                    st.rerun()
                else:
                    st.error(error_msg)

        st.divider()

        # 2. 修改数据
        st.subheader('✏️ 修改开奖号码')
        period_list = st.session_state.lottery_data.index.tolist() if len(st.session_state.lottery_data) > 0 else []
        if period_list:
            with st.form(key='modify_form'):
                modify_period = st.selectbox('选择期号', period_list, index=len(period_list)-1)
                current_nums = st.session_state.lottery_data.loc[modify_period].tolist()
                modify_nums_input = st.text_input(
                    '开奖号码',
                    value=' '.join(map(str, current_nums)),
                    placeholder='20个号码，空格/逗号分隔'
                )
                submit_button = st.form_submit_button('✅ 修改号码', type='primary', use_container_width=True)
                
                if submit_button:
                    try:
                        nums = [int(x.strip()) for x in modify_nums_input.replace(',', ' ').split() if x.strip()]
                        if len(nums) != 20:
                            st.error(f'❌ 请输入20个号码')
                        elif any(n < 1 or n > 80 for n in nums):
                            st.error('❌ 号码必须在1-80之间')
                        elif len(nums) != len(set(nums)):
                            st.error('❌ 号码不能重复')
                        else:
                            nums.sort()
                            st.session_state.lottery_data.loc[modify_period] = nums
                            save_lottery_data(st.session_state.lottery_data)
                            st.success('✅ 修改成功！')
                            st.rerun()
                    except ValueError:
                        st.error('❌ 请输入有效数字')
        else:
            st.info('暂无数据，请先添加')

        st.divider()

        # 3. 删除数据
        st.subheader('🗑️ 删除开奖号码')
        delete_period_list = st.session_state.lottery_data.index.tolist() if len(st.session_state.lottery_data) > 0 else []
        if delete_period_list:
            with st.form(key='delete_form'):
                delete_period = st.selectbox('选择要删除的期号', delete_period_list, index=len(delete_period_list)-1)
                confirm_checkbox = st.checkbox(f'确认删除期号 {delete_period}')
                submit_button = st.form_submit_button('🗑️ 删除号码', use_container_width=True)
                
                if submit_button:
                    if confirm_checkbox:
                        st.session_state.lottery_data = st.session_state.lottery_data.drop(delete_period)
                        save_lottery_data(st.session_state.lottery_data)
                        st.success(f'✅ 期号 {delete_period} 删除成功！')
                        st.rerun()
                    else:
                        st.error('❌ 请先勾选确认框')
        else:
            st.info('暂无数据可删除')

    # 右侧：查看已有的号码
    with col_right:
        st.subheader('📋 开奖号码列表')
        
        # 重新获取最新的期号列表
        display_period_list = st.session_state.lottery_data.index.tolist() if len(st.session_state.lottery_data) > 0 else []
        
        # 筛选和搜索
        col_filter1, col_filter2 = st.columns([1, 2])
        with col_filter1:
            quick_range = st.selectbox('快速选择', ['全部', '最近10期', '最近20期', '最近30期'], index=1)
        with col_filter2:
            search_period = st.text_input('搜索期号', placeholder='输入关键词')
        
        if display_period_list:
            # 快捷范围选择
            if quick_range == '最近10期':
                filtered_periods = display_period_list[-10:]
            elif quick_range == '最近20期':
                filtered_periods = display_period_list[-20:]
            elif quick_range == '最近30期':
                filtered_periods = display_period_list[-30:]
            else:
                filtered_periods = display_period_list
            
            # 搜索过滤
            if search_period:
                filtered_periods = [p for p in filtered_periods if search_period in p]
            
            # 倒序显示
            filtered_periods.reverse()
            
            # 统计信息
            st.markdown(f'''
            <div style="display: flex; gap: 12px; margin-bottom: 12px; flex-wrap: wrap;">
            <span style="background-color: #e3f2fd; padding: 6px 12px; border-radius: 4px; font-size: 12px;">📊 总期数: {len(st.session_state.lottery_data)}</span>
            <span style="background-color: #e8f5e8; padding: 6px 12px; border-radius: 4px; font-size: 12px;">🔢 当前: {len(filtered_periods)}期</span>
            <span style="background-color: #fff3e0; padding: 6px 12px; border-radius: 4px; font-size: 12px;">🆕 最新: {st.session_state.lottery_data.index[-1]}</span>
            </div>
            ''', unsafe_allow_html=True)
            
            # 紧凑卡片显示
            for period in filtered_periods:
                nums = st.session_state.lottery_data.loc[period].tolist()
                nums_str = ' '.join(f'{n:02d}' for n in nums)
                
                st.markdown(f'''
                <div style="background-color: #f8f9fa; padding: 10px 14px; border-radius: 5px; margin-bottom: 6px;">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                <span style="font-weight: bold; color: #1565c0; font-size: 13px;">{period}</span>
                <span style="font-family: monospace; font-size: 12px; color: #333;">{nums_str}</span>
                </div>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.info('暂无数据，请在左侧添加')

# ==================== 【Tab 2】数据分析 ====================
with tabs[1]:
    st.header('📊 多周期数据分析')
    st.markdown('调用号码库数据，进行多维度统计分析。')
    st.divider()

    # 1. 周期选择
    period_options = ['全部', 100, 50, 30, 10, 5]
    selected_period = st.selectbox(
        '请选择分析周期',
        period_options,
        index=0,
        help='选择要分析的最近N期数据，"全部"表示使用所有数据（150期以上）'
    )

    # 获取最近N期数据
    data = st.session_state.lottery_data
    if selected_period == '全部':
        recent_data = data
    elif len(data) >= selected_period:
        recent_data = data.tail(selected_period)
    else:
        recent_data = data
        st.warning(f'⚠️ 数据不足 {selected_period} 期，仅分析现有 {len(recent_data)} 期')

    # 2. 统计所有号码出现次数
    all_numbers = []
    for col in recent_data.columns:
        all_numbers.extend(recent_data[col].dropna().astype(int).tolist())
    
    number_counts = pd.Series(all_numbers).value_counts().reindex(range(1, 81), fill_value=0).sort_index()
    number_counts_df = number_counts.rename('出现次数').to_frame()
    number_counts_df['排名'] = number_counts_df['出现次数'].rank(ascending=False, method='min').astype(int)

    # 3. 展示出现次数统计
    st.subheader(f'📌 近 {selected_period} 期号码出现次数')
    col_stat1, col_stat2 = st.columns([3, 1])
    with col_stat1:
        st.bar_chart(number_counts, color='#FF4B4B')
    with col_stat2:
        st.dataframe(
            number_counts_df[['排名', '出现次数']].sort_values('排名'),
            use_container_width=True,
            height=400
        )

    # 4. 冷热温号判定
    st.divider()
    st.subheader('🔥 冷热温号判定')
    st.caption('判定规则：热号（前20%）、温号（中间60%）、冷号（后20%）')
    
    # 过滤掉未出现的号码（避免分位数偏差）
    valid_counts = number_counts[number_counts > 0]
    if len(valid_counts) > 0:
        hot_thresh = valid_counts.quantile(0.8)
        cold_thresh = valid_counts.quantile(0.2)
        
        hot_nums = number_counts[number_counts >= hot_thresh].index.tolist()
        cold_nums = number_counts[number_counts <= cold_thresh].index.tolist()
        warm_nums = number_counts[(number_counts > cold_thresh) & (number_counts < hot_thresh)].index.tolist()
        
        col_hot, col_warm, col_cold = st.columns(3)
        with col_hot:
            st.markdown('''<div style="background-color: #ffebee; padding: 16px; border-radius: 8px;">
            <h4 style="color: #c62828; margin-top: 0;">🔥 热号 <span style="font-size: 14px; font-weight: normal;">({}个)</span></h4>
            <p style="font-size: 12px; color: #757575;">出现次数 ≥ {:.1f}</p>
            <p style="font-family: monospace; font-size: 14px; color: #c62828; line-height: 1.6;">{}</p>
            </div>'''.format(len(hot_nums), hot_thresh, ' '.join(f'<span style="color: #c62828; font-weight: bold;">{n:02d}</span>' for n in sorted(hot_nums))), unsafe_allow_html=True)
        with col_warm:
            st.markdown('''<div style="background-color: #fff8e1; padding: 16px; border-radius: 8px;">
            <h4 style="color: #f57c00; margin-top: 0;">🌡️ 温号 <span style="font-size: 14px; font-weight: normal;">({}个)</span></h4>
            <p style="font-size: 12px; color: #757575;">出现次数 {:.1f} ~ {:.1f}</p>
            <p style="font-family: monospace; font-size: 14px; color: #f57c00; line-height: 1.6;">{}</p>
            </div>'''.format(len(warm_nums), cold_thresh, hot_thresh, ' '.join(f'<span style="color: #f57c00;">{n:02d}</span>' for n in sorted(warm_nums))), unsafe_allow_html=True)
        with col_cold:
            st.markdown('''<div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px;">
            <h4 style="color: #1565c0; margin-top: 0;">❄️ 冷号 <span style="font-size: 14px; font-weight: normal;">({}个)</span></h4>
            <p style="font-size: 12px; color: #757575;">出现次数 ≤ {:.1f}</p>
            <p style="font-family: monospace; font-size: 14px; color: #1565c0; line-height: 1.6;">{}</p>
            </div>'''.format(len(cold_nums), cold_thresh, ' '.join(f'<span style="color: #1565c0; font-weight: bold;">{n:02d}</span>' for n in sorted(cold_nums))), unsafe_allow_html=True)

    # 5. 012 路统计
    st.divider()
    st.subheader('🔢 012 路统计')
    road_counts = defaultdict(int)
    for num in all_numbers:
        road = num % 3
        road_counts[road] += 1
    
    road_df = pd.DataFrame({
        '路数': ['0路（除3余0）', '1路（除3余1）', '2路（除3余2）'],
        '出现次数': [road_counts[0], road_counts[1], road_counts[2]],
        '占比': [
            f"{road_counts[0]/len(all_numbers)*100:.1f}%",
            f"{road_counts[1]/len(all_numbers)*100:.1f}%",
            f"{road_counts[2]/len(all_numbers)*100:.1f}%"
        ]
    }).set_index('路数')
    
    col_road1, col_road2 = st.columns([2, 1])
    with col_road1:
        st.bar_chart(road_df['出现次数'], color=['#FF9F43'])
    with col_road2:
        st.dataframe(road_df, use_container_width=True)

# ==================== 【Tab 3】跟随号分析 ====================
with tabs[2]:
    st.header('🔗 跟随号分析')
    st.markdown('基于 Tab 1 号码库，选择开奖期数和分析周期，分析该期开奖号码在指定周期内的跟随号。')
    st.divider()
    
    data = st.session_state.lottery_data
    
    analysis_periods = ['全部', 100, 50, 30, 10, 5]
    selected_period = st.selectbox(
        '请选择分析周期',
        analysis_periods,
        index=0,
        key='tab3_analysis_period'
    )
    
    if selected_period == '全部':
        min_data_needed = 2
    else:
        min_data_needed = selected_period + 1
    
    if len(data) >= min_data_needed:
        period_list = sorted(data.index.tolist())
        
        if selected_period == '全部':
            available_periods = period_list[1:]
        else:
            available_periods = period_list[selected_period:]
        
        if not available_periods:
            st.warning(f'⚠️ 数据不足，无法选择符合{selected_period}期周期要求的开奖期数')
        else:
            selected_draw_period = st.selectbox(
                '请选择开奖期数',
                available_periods,
                index=len(available_periods)-1,
                key='tab3_period_select'
            )
            
            period_idx = period_list.index(selected_draw_period)
            if selected_period == '全部':
                before_periods = period_list[:period_idx]
            else:
                before_periods = period_list[period_idx-selected_period:period_idx]
            
            draw_numbers = sorted(data.loc[selected_draw_period].dropna().astype(int).tolist())
            
            st.markdown(f'''<div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; margin-bottom: 12px;">
            <h4 style="color: #1565c0; margin-top: 0;">📌 {selected_draw_period}期开奖号码</h4>
            <p style="font-family: monospace; font-size: 16px;">{' '.join(f'{n:02d}' for n in draw_numbers)}</p>
            <p style="font-size: 12px; color: #666;">分析前{len(before_periods)}期（期数：{before_periods[0]}~{before_periods[-1]}）的跟随号</p>
            </div>''', unsafe_allow_html=True)
            
            def get_follow_numbers(data, target_num, before_periods):
                follow_nums = []
                for i in range(len(before_periods) - 1):
                    current_period = before_periods[i]
                    next_period = before_periods[i+1]
                    current_nums = set(data.loc[current_period].dropna().astype(int).tolist())
                    next_nums = set(data.loc[next_period].dropna().astype(int).tolist())
                    if target_num in current_nums:
                        follow_nums.extend(list(next_nums))
                return follow_nums
            
            all_follow_results = []
            num_follow_sets = {}
            for num in draw_numbers:
                follow_nums = get_follow_numbers(data, num, before_periods)
                if follow_nums:
                    freq = pd.Series(follow_nums).value_counts()
                    top3 = freq.head(3).to_dict()
                    all_follow_results.append({
                        '号码': num,
                        '跟随次数': len(follow_nums),
                        '跟随号码数': len(set(follow_nums)),
                        '前3跟随号': top3
                    })
                    num_follow_sets[num] = set(top3.keys())
            
            if all_follow_results:
                common_follow_counts = {}
                for num, follow_set in num_follow_sets.items():
                    for follow_num in follow_set:
                        if follow_num not in common_follow_counts:
                            common_follow_counts[follow_num] = {'关联数': 0, '关联号码': [], '总次数': 0}
                        common_follow_counts[follow_num]['关联数'] += 1
                        common_follow_counts[follow_num]['关联号码'].append(num)
                
                for follow_num, info in common_follow_counts.items():
                    total_count = 0
                    for result in all_follow_results:
                        if follow_num in result['前3跟随号']:
                            total_count += result['前3跟随号'][follow_num]
                    common_follow_counts[follow_num]['总次数'] = total_count
                
                common_follows = sorted(
                    common_follow_counts.items(),
                    key=lambda x: (-x[1]['关联数'], -x[1]['总次数'])
                )
                
                multi_common = [(num, info) for num, info in common_follows if info['关联数'] >= 2]
                
                if multi_common:
                    st.subheader('⭐ 共同跟随号（关联≥2个开奖号码）')
                    
                    rows = []
                    for num, info in multi_common[:10]:
                        rows.append({
                            '跟随号码': num,
                            '关联开奖号码数': info['关联数'],
                            '总跟随次数': info['总次数'],
                            '关联开奖号码': ', '.join(f'{n:02d}' for n in sorted(info['关联号码']))
                        })
                    
                    df_common = pd.DataFrame(rows)
                    st.dataframe(df_common, use_container_width=True, hide_index=True)
                    
                    st.markdown(f'''
                    <div style="background-color: #e8f5e8; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
                    <span style="color: #2e7d32;">💡 提示：以上号码是多个开奖号码共同的跟随号，值得重点关注</span>
                    </div>
                    ''', unsafe_allow_html=True)
            
            st.subheader('📊 各号码跟随号分析')
            
            for result in all_follow_results:
                st.markdown(f'''
                <div style="background-color: #fff3e0; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
                <h4 style="margin-top: 0; color: #ef6c00;">🔗 号码 {result['号码']:02d} 的跟随号</h4>
                <p style="font-size: 14px; color: #666;">出现 {result['跟随次数']} 次，共 {result['跟随号码数']} 个不同跟随号</p>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 6px; margin-top: 8px;">
                {''.join([f'<div style="background-color: #fff; padding: 6px; border-radius: 4px; text-align: center; font-size: 13px;">\n<span style="font-weight: bold; color: #c62828;">{k:02d}</span>\n<span style="color: #666; font-size: 11px;">({v}次)</span>\n</div>' for k, v in result['前3跟随号'].items()])}
                </div>
                </div>
                ''', unsafe_allow_html=True)
            
            st.subheader('🔥 综合跟随号排行榜')
            
            combined_follow = {}
            for result in all_follow_results:
                for follow_num, count in result['前3跟随号'].items():
                    if follow_num not in combined_follow:
                        combined_follow[follow_num] = {'次数': 0, '关联号码': []}
                    combined_follow[follow_num]['次数'] += count
                    combined_follow[follow_num]['关联号码'].append(result['号码'])
            
            sorted_combined = sorted(
                combined_follow.items(),
                key=lambda x: (-x[1]['次数'], -len(x[1]['关联号码']))
            )[:15]
            
            if sorted_combined:
                rows = []
                for num, info in sorted_combined:
                    rows.append({
                        '跟随号码': num,
                        '总跟随次数': info['次数'],
                        '关联开奖号码数': len(info['关联号码']),
                        '关联开奖号码': ', '.join(f'{n:02d}' for n in sorted(info['关联号码']))
                    })
                
                df_top = pd.DataFrame(rows)
                st.dataframe(df_top, use_container_width=True, hide_index=True)
            
            st.subheader('🎯 跟随号唯一号码池')
            
            all_unique_follow_nums = sorted(set(
                follow_num for result in all_follow_results 
                for follow_num in result['前3跟随号'].keys()
            ))
            
            if all_unique_follow_nums:
                year = int(selected_draw_period[:4])
                period_num = int(selected_draw_period[4:])
                next_period_num = period_num + 1
                next_period = f"{year}{next_period_num:03d}"
                
                if 'follow_pool_dict' not in st.session_state:
                    st.session_state.follow_pool_dict = {}
                st.session_state.follow_pool_dict[next_period] = {
                    'unique_follow_nums': all_unique_follow_nums,
                    'draw_numbers': draw_numbers,
                    'analysis_period': selected_period,
                    'source_period': selected_draw_period,
                    'save_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                st.session_state.follow_unique_pool = all_unique_follow_nums
                
                st.markdown(f'''<div style="background-color: #f3e5f5; padding: 16px; border-radius: 8px;">
                <h4 style="color: #6a1b9a; margin-top: 0;">📋 唯一跟随号号码池（共 {len(all_unique_follow_nums)} 个）</h4>
                <p style="font-family: monospace; font-size: 16px; letter-spacing: 2px;">{' '.join(f'{n:02d}' for n in all_unique_follow_nums)}</p>
                </div>''', unsafe_allow_html=True)
                
                st.markdown(f'''<div style="background-color: #e8f5e8; padding: 12px; border-radius: 6px; margin-top: 12px;">
                <span style="color: #2e7d32;">💡 提示：以上号码是所有开奖号码跟随号的去重集合，可作为选号参考</span>
                </div>''', unsafe_allow_html=True)
                
                follow_data = {
                    'period': selected_period,
                    'analysis_period': selected_period,
                    'draw_period': selected_draw_period,
                    'target_period': next_period,
                    'draw_numbers': draw_numbers,
                    'unique_follow_nums': all_unique_follow_nums,
                    'count': len(all_unique_follow_nums),
                    'save_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                os.makedirs('follow_data', exist_ok=True)
                filename = f'follow_data/{next_period}跟随号.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(follow_data, f, ensure_ascii=False, indent=2)
                st.success(f'✅ 数据已自动保存到 {filename}')
                
                col_save = st.columns(1)
                with col_save[0]:
                    json_str = json.dumps(all_unique_follow_nums, ensure_ascii=False)
                    st.download_button(
                        '📥 下载号码池',
                        data=json_str,
                        file_name=f'{next_period}跟随号.json',
                        mime='application/json'
                    )
            else:
                st.info('暂无跟随号数据')
    else:
        st.warning(f'⚠️ 数据不足 {min_data_needed} 期，无法进行{selected_period}期跟随号分析')

# ==================== 【Tab 4】深度复盘 ====================
with tabs[3]:
    st.header('🔍 组合同出分析')
    st.markdown('基于 Tab 1 号码库数据，分析近20、10、5期的三码/四码/五码同出数据（仅显示出现次数>2次）。')
    st.divider()

    if len(st.session_state.lottery_data) >= 5:
        data = st.session_state.lottery_data
        
        def calculate_combinations(data, period, combo_size):
            """计算指定周期内的组合出现次数（去重保证唯一性）"""
            if period == '全部':
                recent_data = data
            else:
                recent_data = data.tail(period) if len(data) >= period else data
            combo_counts = defaultdict(int)
            for idx, row in recent_data.iterrows():
                nums = sorted(set(row.dropna().astype(int).tolist()))
                for combo in itertools.combinations(nums, combo_size):
                    combo_counts[combo] += 1
            return combo_counts, len(recent_data)
        
        def format_combo(combo):
            """格式化组合显示"""
            return '-'.join(f'{n:02d}' for n in combo)
        
        combo_type = st.selectbox(
            '选择组合类型',
            ['双码同出', '三码同出', '四码同出', '五码同出'],
            index=0,
            key='combo_type_select'
        )
        
        combo_size_map = {'双码同出': 2, '三码同出': 3, '四码同出': 4, '五码同出': 5}
        combo_size = combo_size_map[combo_type]
        
        period_options = ['全部', 100, 50, 30, 10, 5]
        selected_period = st.selectbox(
            '选择分析周期',
            period_options,
            index=0,
            key='tab4_period_select'
        )
        
        if selected_period == '全部':
            long_period = '全部'
            mid_period = 50
            short_period = 10
        elif selected_period == 100:
            long_period = 100
            mid_period = 50
            short_period = 10
        elif selected_period == 50:
            long_period = 50
            mid_period = 30
            short_period = 5
        elif selected_period == 30:
            long_period = 30
            mid_period = 10
            short_period = 5
        elif selected_period == 10:
            long_period = 10
            mid_period = 5
            short_period = 3
        else:
            long_period = 5
            mid_period = 3
            short_period = 2
        
        tab_all, tab_trend, tab_new, tab_recent5 = st.tabs(['📈 全周期对比', '📉 频率递增', '✨ 近期新增', '🔥 近期出现'])
        
        with tab_all:
            combo_long, _ = calculate_combinations(data, long_period, combo_size)
            combo_mid, _ = calculate_combinations(data, mid_period, combo_size)
            combo_short, _ = calculate_combinations(data, short_period, combo_size)
            
            long_label = '全部期' if long_period == '全部' else f'近{long_period}期'
            mid_label = f'近{mid_period}期'
            short_label = f'近{short_period}期'
            
            all_combos = set(combo_long.keys()) | set(combo_mid.keys()) | set(combo_short.keys())
            
            rows = []
            for combo in all_combos:
                cnt_long = combo_long.get(combo, 0)
                cnt_mid = combo_mid.get(combo, 0)
                cnt_short = combo_short.get(combo, 0)
                max_cnt = max(cnt_long, cnt_mid, cnt_short)
                if max_cnt > 2:
                    rows.append({
                        '组合': format_combo(combo),
                        long_label: cnt_long,
                        mid_label: cnt_mid,
                        short_label: cnt_short,
                        '最高次数': max_cnt
                    })
            
            df = pd.DataFrame(rows)
            df = df.sort_values('最高次数', ascending=False)
            
            st.markdown(f'''
            <div style="background-color: #e3f2fd; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
            <span style="color: #1565c0;">📊 {combo_type} - 共 {len(df)} 组数据（出现次数>2次）</span>
            </div>
            ''', unsafe_allow_html=True)
            
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        with tab_trend:
            trend_label = f'{short_label} > {mid_label} > {long_label}'
            st.markdown(f'''<div style="background-color: #e8f5e8; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
            <span style="color: #2e7d32;">📈 频率递增{combo_type}：{trend_label}</span>
            </div>''', unsafe_allow_html=True)
            
            combo_short, _ = calculate_combinations(data, short_period, combo_size)
            combo_mid, _ = calculate_combinations(data, mid_period, combo_size)
            combo_long, _ = calculate_combinations(data, long_period, combo_size)
            
            increasing_combos = []
            for combo, cnt_short in combo_short.items():
                cnt_mid = combo_mid.get(combo, 0)
                cnt_long = combo_long.get(combo, 0)
                if cnt_short > cnt_mid > cnt_long:
                    increasing_combos.append((combo, cnt_short, cnt_mid, cnt_long))
            
            increasing_combos.sort(key=lambda x: (-x[1], x[0]))
            
            if increasing_combos:
                rows = []
                for combo, cnt_short, cnt_mid, cnt_long in increasing_combos:
                    rows.append({
                        '组合': format_combo(combo),
                        short_label: cnt_short,
                        mid_label: cnt_mid,
                        long_label: cnt_long
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info(f'暂无频率递增的{combo_type}组合')
        
        with tab_new:
            new_label = f'{short_label}出现 > 0 且{mid_label}出现 = 0'
            st.markdown(f'''<div style="background-color: #f3e5f5; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
            <span style="color: #7b1fa2;">✨ 近期新增{combo_type}：{new_label}</span>
            </div>''', unsafe_allow_html=True)
            
            combo_short, _ = calculate_combinations(data, short_period, combo_size)
            combo_mid, _ = calculate_combinations(data, mid_period, combo_size)
            
            new_combos = []
            for combo, cnt_short in combo_short.items():
                cnt_mid = combo_mid.get(combo, 0)
                if cnt_short > 0 and cnt_mid == 0:
                    new_combos.append((combo, cnt_short))
            
            new_combos.sort(key=lambda x: (-x[1], x[0]))
            
            if new_combos:
                rows = []
                for combo, cnt in new_combos:
                    rows.append({
                        '组合': format_combo(combo),
                        f'{short_label}出现次数': cnt
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info(f'暂无近期新增的{combo_type}组合')
        
        with tab_recent5:
            recent_period = short_period
            recent_label = '全部期' if recent_period == '全部' else f'近{recent_period}期'
            st.markdown(f'''<div style="background-color: #ffebee; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
            <span style="color: #c62828;">🔥 {recent_label}出现{combo_type}：显示所有在{recent_label}出现过的组合</span>
            </div>''', unsafe_allow_html=True)
            
            if recent_period == '全部':
                recent_data = data
            else:
                recent_data = data.tail(recent_period)
            
            combo_period_map = {}
            for period_idx, (period, row) in enumerate(recent_data.iterrows()):
                nums = sorted(set(row.dropna().astype(int).tolist()))
                for combo in itertools.combinations(nums, combo_size):
                    if combo not in combo_period_map:
                        combo_period_map[combo] = {'期数': [], '出现次数': 0}
                    combo_period_map[combo]['期数'].append(str(period))
                    combo_period_map[combo]['出现次数'] += 1
            
            rows = []
            for combo, info in combo_period_map.items():
                rows.append({
                    '组合': format_combo(combo),
                    '出现次数': info['出现次数'],
                    '出现在期数': ', '.join(info['期数'])
                })
            
            df_recent = pd.DataFrame(rows)
            df_recent = df_recent.sort_values('出现次数', ascending=False)
            
            st.markdown(f'''
            <div style="background-color: #ffebee; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
            <span style="color: #c62828;">📊 {combo_type} - {recent_label}共 {len(df_recent)} 组数据</span>
            </div>
            ''', unsafe_allow_html=True)
            
            st.dataframe(df_recent, use_container_width=True, hide_index=True)
    else:
        st.warning('⚠️ 数据不足 5 期，无法进行分析')

# ==================== 【Tab 5】跟随号与杀号对比 ====================
with tabs[4]:
    st.header('🔄 跟随号与杀号对比')
    st.markdown('''<div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
    <p style="font-size: 16px; line-height: 1.6;">对接 Tab 3（跟随号）和 Tab 10（杀号）数据，按期号一一对应显示，相同号码标注，列出剩余跟随号码。</p>
    <p style="font-size: 14px; color: #666;">🔴 深红=与杀号相同 | 🟠 橙色=与观察号相同</p>
    </div>''', unsafe_allow_html=True)
    
    follow_dict = st.session_state.get('follow_pool_dict', {})
    kill_dict = {}
    if os.path.exists('kill_data'):
        for filename in os.listdir('kill_data'):
            if filename.endswith('杀号.json'):
                period = filename.replace('杀号.json', '')
                try:
                    with open(f'kill_data/{filename}', 'r', encoding='utf-8') as f:
                        kill_dict[period] = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass
    
    valid_periods = sorted([p for p in follow_dict if p in kill_dict], reverse=True)
    
    if not valid_periods:
        st.warning('⚠️ 暂无完整数据')
    else:
        for target_period in valid_periods:
            follow_data = follow_dict[target_period]
            kill_data = kill_dict[target_period]
            follow_nums = follow_data['unique_follow_nums']
            kill_nums = kill_data['final_kill']
            watch_nums = kill_data.get('watch_list', [])
            source_period = follow_data.get('source_period', '')
            
            follow_set = set(follow_nums)
            kill_set = set(kill_nums)
            watch_set = set(watch_nums)
            
            kill_common = sorted(follow_set & kill_set)
            watch_common = sorted(follow_set & watch_set)
            remaining_nums = sorted(follow_set - kill_set - watch_set)
            
            st.markdown(f'''<div style="background-color: #f5f5f5; padding: 14px; border-radius: 8px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="font-weight: bold; color: #1565c0;">{target_period}期</span>
            <span style="font-size: 12px; color: #666;">{source_period}期跟随 → {target_period}期</span>
            </div>
            <div style="display: flex; gap: 16px; flex-wrap: wrap;">
            <div style="flex: 1; min-width: 200px;">
            <span style="font-size: 12px; color: #6a1b9a;">跟随号:</span>
            <span style="font-family: monospace; font-size: 16px; margin-left: 4px;">{' '.join(f'<span style="color: #c62828; font-weight: bold;">{n:02d}</span>' if n in kill_set else f'<span style="color: #ef6c00; font-weight: bold;">{n:02d}</span>' if n in watch_set else f'{n:02d}' for n in follow_nums)}</span>
            </div>
            <div style="flex: 1; min-width: 200px;">
            <span style="font-size: 12px; color: #c62828;">杀号:</span>
            <span style="font-family: monospace; font-size: 16px; margin-left: 4px;">{' '.join(f'<span style="color: #c62828; font-weight: bold;">{n:02d}</span>' if n in follow_set else f'{n:02d}' for n in kill_nums)}</span>
            </div>
            </div>
            <div style="margin-top: 8px;">
            <span style="font-size: 12px; color: #2e7d32;">剩余:</span>
            <span style="font-family: monospace; font-size: 18px; font-weight: bold; margin-left: 4px;">{' '.join(f'{n:02d}' for n in remaining_nums)}</span>
            </div>
            </div>''', unsafe_allow_html=True)
            
            if remaining_nums:
                os.makedirs('remaining_data', exist_ok=True)
                remaining_filename = f'remaining_data/{target_period}剩余.json'
                with open(remaining_filename, 'w', encoding='utf-8') as f:
                    json.dump({
                        'period': target_period,
                        'source_period': source_period,
                        'remaining_nums': remaining_nums,
                        'follow_nums': follow_nums,
                        'kill_nums': kill_nums,
                        'watch_nums': watch_nums,
                        'kill_common': kill_common,
                        'watch_common': watch_common,
                        'save_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }, f, ensure_ascii=False, indent=2)

# ==================== 【Tab 6】剩余号码与开奖对比 ====================
with tabs[5]:
    st.header('📊 剩余号码 vs 开奖号码对比')
    st.markdown('''<div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
    <p style="font-size: 16px; line-height: 1.6;">对接 Tab 1（号码库）和 Tab 5（剩余号码）数据，按期号一一对应对比。</p>
    <p style="font-size: 14px; color: #666;">🔴 红色=命中开奖号码</p>
    </div>''', unsafe_allow_html=True)
    
    lottery_data = st.session_state.lottery_data
    remaining_dict = {}
    if os.path.exists('remaining_data'):
        for filename in os.listdir('remaining_data'):
            if filename.endswith('剩余.json'):
                period = filename.replace('剩余.json', '')
                try:
                    with open(f'remaining_data/{filename}', 'r', encoding='utf-8') as f:
                        remaining_dict[period] = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass
    
    valid_periods = sorted([p for p in lottery_data.index if p in remaining_dict], reverse=True)
    
    if not valid_periods:
        st.warning('⚠️ 暂无完整对比数据')
    else:
        hit_stats = []
        for period in valid_periods:
            draw_numbers = sorted([int(n) for n in lottery_data.loc[period].dropna().tolist()])
            remaining_nums = remaining_dict[period].get('remaining_nums', [])
            hit_count = len(set(draw_numbers) & set(remaining_nums))
            hit_stats.append({'period': period, 'hit': hit_count, 'total': len(remaining_nums)})
        
        st.markdown('''<div style="background-color: #e8f5e8; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
        <h4 style="margin-top: 0; color: #2e7d32;">📈 命中统计</h4>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
        <thead>
        <tr style="background-color: #c8e6c9;">
        <th style="border: 1px solid #a5d6a7; padding: 8px; text-align: left;">期号</th>
        <th style="border: 1px solid #a5d6a7; padding: 8px; text-align: center;">剩余号码</th>
        <th style="border: 1px solid #a5d6a7; padding: 8px; text-align: center;">命中数量</th>
        </tr>
        </thead>
        <tbody>
        ''' + ''.join([f'''<tr>
        <td style="border: 1px solid #a5d6a7; padding: 8px;">{stat['period']}</td>
        <td style="border: 1px solid #a5d6a7; padding: 8px; text-align: center;">{stat['total']}</td>
        <td style="border: 1px solid #a5d6a7; padding: 8px; text-align: center;"><span style="color: #c62828; font-weight: bold;">{stat['hit']}</span></td>
        </tr>''' for stat in hit_stats]) + '''
        </tbody>
        </table>
        </div>''', unsafe_allow_html=True)
        
        for period in valid_periods:
            draw_numbers = sorted([int(n) for n in lottery_data.loc[period].dropna().tolist()])
            remaining_nums = remaining_dict[period].get('remaining_nums', [])
            draw_set = set(draw_numbers)
            remaining_set = set(remaining_nums)
            hit_nums = sorted(remaining_set & draw_set)
            
            st.markdown(f'''<div style="background-color: #f5f5f5; padding: 14px; border-radius: 8px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="font-weight: bold; color: #1565c0;">{period}期</span>
            <span style="font-size: 12px; color: #2e7d32;">命中 <span style="font-weight: bold;">{len(hit_nums)}</span> 个</span>
            </div>
            <div style="display: flex; gap: 16px; flex-wrap: wrap;">
            <div style="flex: 1; min-width: 200px;">
            <span style="font-size: 12px; color: #6a1b9a;">剩余:</span>
            <span style="font-family: monospace; font-size: 16px; margin-left: 4px;">{' '.join(f'<span style="color: #c62828; font-weight: bold;">{n:02d}</span>' if n in draw_set else f'{n:02d}' for n in remaining_nums)}</span>
            </div>
            <div style="flex: 1; min-width: 200px;">
            <span style="font-size: 12px; color: #2e7d32;">开奖:</span>
            <span style="font-family: monospace; font-size: 16px; margin-left: 4px;">{' '.join(f'<span style="color: #c62828; font-weight: bold;">{n:02d}</span>' if n in remaining_set else f'{n:02d}' for n in draw_numbers)}</span>
            </div>
            </div>
            </div>''', unsafe_allow_html=True)

# ==================== 【Tab 7】体系全流程 SOP（完整实现） ====================
with tabs[6]:
    st.header('📋 体系全流程标准化执行 SOP')
    st.divider()

    # ==================== 【SOP 核心算法模块】 ====================
    def build_front_segment_data():
        """构建前段库数据（1-40区间）"""
        front_segment_data = {}
        for period in st.session_state.lottery_data.index:
            numbers = st.session_state.lottery_data.loc[period].tolist()
            front_numbers = sorted([int(n) for n in numbers if 1 <= n <= 40])
            if front_numbers:
                front_segment_data[period] = front_numbers
        return front_segment_data

    def convert_to_dataframe(segment_data):
        """将前段库数据转换为DataFrame格式"""
        max_len = max(len(v) for v in segment_data.values()) if segment_data else 0
        rows = []
        for period in sorted(segment_data.keys()):
            nums = segment_data[period]
            row = nums + [None] * (max_len - len(nums))
            rows.append(row)
        df = pd.DataFrame(rows, index=sorted(segment_data.keys()))
        return df

    def calculate_number_stats(data, period):
        """计算号码的基础统计数据"""
        recent_data = data.tail(period)
        all_numbers = []
        for col in recent_data.columns:
            all_numbers.extend(recent_data[col].dropna().astype(int).tolist())
        
        number_counts = pd.Series(all_numbers).value_counts().reindex(range(1, 41), fill_value=0)
        return number_counts

    def calculate_omission(data, num):
        """计算号码的遗漏期数"""
        last_appear = -1
        for i, (period, row) in enumerate(data.iloc[::-1].iterrows()):
            if num in row.values:
                last_appear = i
                break
        return last_appear if last_appear != -1 else len(data)

    def calculate_cooccurrence(data, num1, num2, period=50):
        """计算两码共现次数"""
        recent_data = data.tail(period)
        count = 0
        for _, row in recent_data.iterrows():
            nums = set(row.dropna().astype(int).tolist())
            if num1 in nums and num2 in nums:
                count += 1
        return count

    def step1_prepare_data(data):
        """Step 1: 基础数据准备"""
        stats_100 = calculate_number_stats(data, min(100, len(data)))
        stats_50 = calculate_number_stats(data, min(50, len(data)))
        stats_30 = calculate_number_stats(data, min(30, len(data)))
        stats_20 = calculate_number_stats(data, min(20, len(data)))
        stats_10 = calculate_number_stats(data, min(10, len(data)))
        
        omission = {}
        for num in range(1, 41):
            omission[num] = calculate_omission(data, num)
        
        return {
            'stats_100': stats_100,
            'stats_50': stats_50,
            'stats_30': stats_30,
            'stats_20': stats_20,
            'stats_10': stats_10,
            'omission': omission
        }

    def step2_risk_control(data, prepared_data):
        """Step 2: 刚性风控规则执行"""
        last_period = data.index[-1]
        last_2_period = data.index[-2] if len(data) >= 2 else None
        last_3_period = data.index[-3] if len(data) >= 3 else None
        
        last_nums = set(data.loc[last_period].dropna().astype(int).tolist())
        last_2_nums = set(data.loc[last_2_period].dropna().astype(int).tolist()) if last_2_period else set()
        last_3_nums = set(data.loc[last_3_period].dropna().astype(int).tolist()) if last_3_period else set()
        
        three_consecutive = last_nums & last_2_nums & last_3_nums
        
        two_consecutive = last_nums & last_2_nums
        
        hot_fuse = []
        stats_10 = prepared_data['stats_10']
        for num in range(1, 41):
            if stats_10[num] >= 4:
                hot_fuse.append(num)
        
        exclude_list = list(three_consecutive) + list(hot_fuse)
        exclude_list = list(set(exclude_list))
        
        downgrade_list = list(two_consecutive - set(exclude_list))
        
        return {
            'three_consecutive': list(three_consecutive),
            'two_consecutive': list(two_consecutive),
            'hot_fuse': hot_fuse,
            'exclude_list': exclude_list,
            'downgrade_list': downgrade_list
        }

    def step3_market_judge(data, prepared_data):
        """Step 3: 行情周期判定"""
        recent_7 = data.tail(7)
        
        stats_50 = prepared_data['stats_50']
        hot_thresh = stats_50.quantile(0.8)
        cold_thresh = stats_50.quantile(0.2)
        
        warm_count = 0
        hot_count = 0
        cold_count = 0
        
        for _, row in recent_7.iterrows():
            nums = row.dropna().astype(int).tolist()
            for num in nums:
                if stats_50[num] >= hot_thresh:
                    hot_count += 1
                elif stats_50[num] <= cold_thresh:
                    cold_count += 1
                else:
                    warm_count += 1
        
        total = hot_count + warm_count + cold_count
        warm_ratio = warm_count / total if total > 0 else 0
        hot_ratio = hot_count / total if total > 0 else 0
        cold_ratio = cold_count / total if total > 0 else 0
        
        # 优先级：冷号主导 > 热号主导 > 温号主导 > 均衡行情
        if cold_ratio >= 0.40:
            market_type = "冷号主导行情"
        elif hot_ratio >= 0.35:
            market_type = "热号主导行情"
        elif warm_ratio >= 0.45:
            market_type = "温号主导行情"
        else:
            market_type = "均衡行情"
        
        if market_type == "冷号主导行情":
            position = {'stable': 0.20, 'warm': 0.30, 'hot': 0.10, 'cold': 0.40}
        elif market_type == "热号主导行情":
            position = {'stable': 0.35, 'warm': 0.30, 'hot': 0.20, 'cold': 0.15}
        elif market_type == "温号主导行情":
            position = {'stable': 0.25, 'warm': 0.50, 'hot': 0.10, 'cold': 0.15}
        else:
            position = {'stable': 0.30, 'warm': 0.40, 'hot': 0.15, 'cold': 0.15}
        
        return {
            'market_type': market_type,
            'warm_ratio': warm_ratio,
            'hot_ratio': hot_ratio,
            'cold_ratio': cold_ratio,
            'position': position
        }

    def step4_select_numbers(data, prepared_data, risk_data, market_data):
        """Step 4: 三大流派号码筛选（前段库专用）"""
        stats_100 = prepared_data['stats_100']
        stats_50 = prepared_data['stats_50']
        stats_30 = prepared_data['stats_30']
        stats_20 = prepared_data['stats_20']
        stats_10 = prepared_data['stats_10']
        omission = prepared_data['omission']
        exclude_list = risk_data['exclude_list']
        
        # 第一流派：均衡稳胆流
        stable_candidates = []
        for num in range(1, 41):
            if num in exclude_list:
                continue
            if (stats_100[num] >= 10 and 
                stats_30[num] >= 3 and 
                stats_10[num] >= 2 and
                omission[num] <= 4):
                stable_candidates.append(num)
        
        stable_scores = {}
        for num in stable_candidates:
            stable_scores[num] = stats_100[num] * 0.4 + stats_50[num] * 0.3 + stats_30[num] * 0.3
        stable_candidates = sorted(stable_candidates, key=lambda x: stable_scores[x], reverse=True)[:5]
        
        # 第二流派：温号轮动流
        warm_candidates = []
        for num in range(1, 41):
            if num in exclude_list or num in stable_candidates:
                continue
            if (3 <= omission[num] <= 6 and 
                stats_30[num] >= 3 and
                1 <= stats_10[num] <= 2):
                warm_candidates.append(num)
        
        warm_scores = {}
        for num in warm_candidates:
            score = stats_30[num]
            for stable_num in stable_candidates[:3]:
                score += calculate_cooccurrence(data, num, stable_num, 30) * 2
            warm_scores[num] = score
        warm_candidates = sorted(warm_candidates, key=lambda x: warm_scores[x], reverse=True)[:6]
        
        # 第三流派：热号主攻流
        hot_candidates = []
        for num in range(1, 41):
            if num in exclude_list or num in stable_candidates or num in warm_candidates:
                continue
            if (stats_50[num] >= 6 and
                2 <= stats_10[num] <= 3 and
                omission[num] <= 3):
                hot_candidates.append(num)
        
        hot_candidates = sorted(hot_candidates, key=lambda x: stats_50[x], reverse=True)[:3]
        
        # 辅助模块：冷号回补流
        cold_candidates = []
        for num in range(1, 41):
            if num in exclude_list or num in stable_candidates or num in warm_candidates or num in hot_candidates:
                continue
            if (5 <= omission[num] <= 10 and
                stats_100[num] >= 8):
                cold_candidates.append(num)
        
        cold_candidates = sorted(cold_candidates, key=lambda x: omission[x])[:3]
        
        return {
            'stable': stable_candidates,
            'warm': warm_candidates,
            'hot': hot_candidates,
            'cold': cold_candidates
        }

    def step5_build_core_pool(selected_numbers, market_data, risk_data):
        """Step 5: 10码核心池锁定（前段库专用）"""
        position = market_data['position']
        market_type = market_data['market_type']
        total_size = 10
        
        stable_count = max(1, int(total_size * position['stable']))
        warm_count = max(1, int(total_size * position['warm']))
        hot_count = max(1, int(total_size * position['hot']))
        cold_count = total_size - stable_count - warm_count - hot_count
        
        if cold_count < 1:
            cold_count = 1
            hot_count = max(1, hot_count - 1)
        
        # 冷号主导行情时，热号最多1个
        if market_type == "冷号主导行情":
            hot_count = min(hot_count, 1)
        
        core_pool = []
        
        stable_nums = selected_numbers['stable'][:stable_count] if selected_numbers['stable'] else []
        warm_nums = selected_numbers['warm'][:warm_count] if selected_numbers['warm'] else []
        hot_nums = selected_numbers['hot'][:hot_count] if selected_numbers['hot'] else []
        cold_nums = selected_numbers['cold'][:cold_count] if selected_numbers['cold'] else []
        
        core_pool.extend(stable_nums)
        core_pool.extend(warm_nums)
        core_pool.extend(hot_nums)
        core_pool.extend(cold_nums)
        
        core_pool = sorted(list(set(core_pool)))
        
        if len(core_pool) < total_size:
            all_available = selected_numbers['stable'] + selected_numbers['warm'] + selected_numbers['hot'] + selected_numbers['cold']
            all_available = sorted(list(set(all_available)))
            for num in all_available:
                if num not in core_pool and len(core_pool) < total_size:
                    core_pool.append(num)
        
        # 强制平衡规则：奇偶4:6~6:4
        def is_balanced(pool):
            if len(pool) < total_size:
                return False
            evens = sum(1 for n in pool if n % 2 == 0)
            odds = total_size - evens
            if evens < 4 or evens > 6:
                return False
            return True
        
        if not is_balanced(core_pool) and len(core_pool) >= total_size:
            all_available = sorted(list(set(
                selected_numbers['stable'] + selected_numbers['warm'] + 
                selected_numbers['hot'] + selected_numbers['cold']
            )))
            best_pool = core_pool
            best_score = float('inf')
            
            from itertools import combinations
            for candidate in combinations(all_available, total_size):
                candidate = sorted(list(candidate))
                if not is_balanced(candidate):
                    continue
                
                score = 0
                for i, num in enumerate(candidate):
                    if num in stable_nums:
                        score += (10 - i) * 5
                    elif num in warm_nums:
                        score += (10 - i) * 3
                    elif num in hot_nums:
                        score += (10 - i) * 2
                    elif num in cold_nums:
                        score += (10 - i) * 1
                
                if score < best_score:
                    best_score = score
                    best_pool = candidate
            
            if best_pool != core_pool:
                core_pool = best_pool
        
        backup_pool = {
            'level1': [num for num in selected_numbers['stable'] + selected_numbers['warm'] if num not in core_pool][:4],
            'level2': [num for num in selected_numbers['hot'] + selected_numbers['cold'] if num not in core_pool][:4],
            'level3': risk_data['three_consecutive'] + risk_data['downgrade_list']
        }
        
        return {
            'core_pool': core_pool,
            'backup_pool': backup_pool
        }

    def step6_build_combinations(core_pool, selected_numbers, data):
        """Step 6: 三层对冲组合构建"""
        
        core_pool_sorted = sorted(core_pool)
        n = len(core_pool_sorted)
        
        eight_code = []
        # 策略1：全核心池覆盖
        for i in range(10):
            if n >= 8:
                # 不同的起始位置和步长
                start = i % n
                step = ((i // 2) % 3) + 1
                comb = []
                for j in range(8):
                    idx = (start + j * step) % n
                    comb.append(core_pool_sorted[idx])
                comb = sorted(list(set(comb)))
                # 如果不够8个，补充
                while len(comb) < 8:
                    for num in core_pool_sorted:
                        if num not in comb:
                            comb.append(num)
                            break
                    comb.sort()
            else:
                # 核心池小于8，重复使用
                comb = (core_pool_sorted * 2)[:8]
            eight_code.append(sorted(comb))
        
        six_code = []
        for i in range(10):
            if n >= 6:
                # 不同策略
                if i == 0:
                    comb = core_pool_sorted[:6]
                elif i == 1:
                    comb = core_pool_sorted[-6:]
                elif i == 2:
                    comb = [core_pool_sorted[i % n] for i in [0, 2, 4, 6, 8, 10]][:6]
                elif i == 3:
                    comb = [core_pool_sorted[i % n] for i in [1, 3, 5, 7, 9, 11]][:6]
                elif i == 4:
                    comb = [core_pool_sorted[i % n] for i in [0, 1, n-2, n-1, n//2-1, n//2]][:6]
                elif i == 5:
                    comb = [core_pool_sorted[i % n] for i in [0, n//3, 2*n//3, n-1, 1, n-2]][:6]
                elif i == 6:
                    comb = [core_pool_sorted[i % n] for i in [0, n-1, 1, n-2, 2, n-3]][:6]
                elif i == 7:
                    comb = [core_pool_sorted[i % n] for i in range(0, n, 2)][:6]
                elif i == 8:
                    comb = [core_pool_sorted[i % n] for i in range(1, n, 2)][:6]
                else:
                    mid = n // 2
                    comb = core_pool_sorted[max(0, mid-3):min(n, mid+3)]
                comb = sorted(list(set(comb)))
                while len(comb) < 6:
                    for num in core_pool_sorted:
                        if num not in comb:
                            comb.append(num)
                            break
                    comb.sort()
            else:
                comb = (core_pool_sorted * 2)[:6]
            six_code.append(sorted(comb))
        
        three_code = []
        # 使用组合策略生成不同的3码组合
        for i in range(10):
            if n >= 3:
                # 不同的组合策略
                if i == 0:
                    comb = core_pool_sorted[:3]
                elif i == 1:
                    comb = core_pool_sorted[-3:]
                elif i == 2:
                    comb = [core_pool_sorted[0], core_pool_sorted[n//2], core_pool_sorted[-1]]
                elif i == 3:
                    comb = [core_pool_sorted[1], core_pool_sorted[n//2], core_pool_sorted[-2]]
                elif i == 4:
                    comb = [core_pool_sorted[0], core_pool_sorted[1], core_pool_sorted[2]]
                elif i == 5:
                    comb = [core_pool_sorted[-3], core_pool_sorted[-2], core_pool_sorted[-1]]
                elif i == 6:
                    comb = [core_pool_sorted[0], core_pool_sorted[n//3], core_pool_sorted[2*n//3]]
                elif i == 7:
                    comb = [core_pool_sorted[1], core_pool_sorted[n//3+1], core_pool_sorted[2*n//3+1]]
                elif i == 8:
                    comb = [core_pool_sorted[0], core_pool_sorted[n-2], core_pool_sorted[n-1]]
                elif i == 9:
                    comb = [core_pool_sorted[n//4], core_pool_sorted[n//2], core_pool_sorted[3*n//4]]
                comb = sorted(list(set(comb)))
                while len(comb) < 3:
                    for num in core_pool_sorted:
                        if num not in comb:
                            comb.append(num)
                            break
                    comb.sort()
            else:
                comb = (core_pool_sorted * 2)[:3]
            three_code.append(sorted(comb))
        
        return {
            'eight_code': eight_code,
            'six_code': six_code,
            'three_code': three_code
        }

    # ==================== 【SOP 主界面】 ====================
    st.markdown("""
    ## 📋 体系全流程标准化执行 SOP（前段库专用）
    <div style="background-color: #f0f2f6; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
    <p style="font-size: 16px; line-height: 1.6;">
    本 SOP 基于 Tab 5 前段库（1-40区间）数据进行预测，每期严格按步骤执行，确保预测的科学性和一致性。
    </p>
    <ul style="margin-top: 10px; font-size: 14px;">
    <li>✅ 8步标准化流程，确保预测的科学性和一致性</li>
    <li>✅ 基于多周期数据的量化分析（1-40区间）</li>
    <li>✅ 自动生成10码核心池和三层对冲组合</li>
    <li>✅ 完整的风控机制，避免极端情况</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # 构建前段库数据
    front_segment_data = build_front_segment_data()
    front_df = convert_to_dataframe(front_segment_data)
    
    st.divider()
    st.subheader('🔮 为 N+1 期进行预测')
    
    if len(front_df) >= 10:
        period_list = front_df.index.tolist()
        sop_n_period = st.selectbox(
            '请选择 N 期数（已开奖的最后一期）',
            period_list,
            index=len(period_list)-1,
            help='选择已开奖的最后一期 N，系统将为 N+1 期准备预测',
            key='sop_period_front'
        )
        
        n_plus_1 = str(int(sop_n_period) + 1)
        st.write(f'已选择 **{sop_n_period}** 期，将为 **{n_plus_1}** 期进行预测')
        
        if st.button('🚀 执行完整 SOP 流程', type='primary', use_container_width=True, key='sop_button_front'):
            # 根据选择的期数裁剪前段库数据，只使用到 sop_n_period 期为止的数据
            data = front_df.loc[:sop_n_period].copy()
            
            # 进度条和状态显示
            col_progress, col_status = st.columns([1, 3])
            with col_progress:
                progress_bar = st.progress(0)
            with col_status:
                status_text = st.empty()
            
            # Step 1
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 1/8: 基础数据准备...</div>', unsafe_allow_html=True)
            prepared_data = step1_prepare_data(data)
            progress_bar.progress(12)
            
            # Step 2
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 2/8: 刚性风控规则执行...</div>', unsafe_allow_html=True)
            risk_data = step2_risk_control(data, prepared_data)
            progress_bar.progress(25)
            
            # Step 3
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 3/8: 行情周期判定...</div>', unsafe_allow_html=True)
            market_data = step3_market_judge(data, prepared_data)
            progress_bar.progress(37)
            
            # Step 4
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 4/8: 三大流派号码筛选...</div>', unsafe_allow_html=True)
            selected_numbers = step4_select_numbers(data, prepared_data, risk_data, market_data)
            progress_bar.progress(50)
            
            # Step 5
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 5/8: 10码核心池锁定...</div>', unsafe_allow_html=True)
            core_pool_data = step5_build_core_pool(selected_numbers, market_data, risk_data)
            progress_bar.progress(62)
            
            # Step 6
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 6/8: 三层对冲组合构建...</div>', unsafe_allow_html=True)
            combinations = step6_build_combinations(core_pool_data['core_pool'], selected_numbers, data)
            progress_bar.progress(75)
            
            # Step 7
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 7/8: 终版方案存档锁定...</div>', unsafe_allow_html=True)
            prediction_data = {
                'period': n_plus_1,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'step1_prepared': {
                    'stats_100': prepared_data['stats_100'].to_dict(),
                    'omission': prepared_data['omission']
                },
                'step2_risk': risk_data,
                'step3_market': market_data,
                'step4_selected': selected_numbers,
                'step5_core_pool': core_pool_data,
                'step6_combinations': combinations,
                'core_pool': ' '.join(map(str, sorted(core_pool_data['core_pool']))),
                'combinations': combinations
            }
            filename = save_prediction(prediction_data, n_plus_1)
            st.session_state['prediction_data'] = prediction_data
            progress_bar.progress(87)
            
            # Step 8
            status_text.text('Step 8/8: 完成！')
            progress_bar.progress(100)
            
            # 展示结果
            st.success(f'✅ SOP 流程执行完成！预测方案已保存至：{filename}')
            st.divider()
            
            # 展示 Step 2 风控结果
            st.subheader('📌 Step 2: 刚性风控执行结果')
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.markdown('''
                <div style="background-color: #ffebee; padding: 12px; border-radius: 6px;">
                <h4 style="margin-top: 0; color: #c62828;">三期连开号（剔除）</h4>
                <p>{}</p>
                </div>
                '''.format(risk_data['three_consecutive'] if risk_data['three_consecutive'] else '无'), unsafe_allow_html=True)
            with col_r2:
                st.markdown('''
                <div style="background-color: #fff3e0; padding: 12px; border-radius: 6px;">
                <h4 style="margin-top: 0; color: #ef6c00;">两期连开号（降权）</h4>
                <p>{}</p>
                </div>
                '''.format(risk_data['downgrade_list'] if risk_data['downgrade_list'] else '无'), unsafe_allow_html=True)
            with col_r3:
                st.markdown('''
                <div style="background-color: #e3f2fd; padding: 12px; border-radius: 6px;">
                <h4 style="margin-top: 0; color: #1565c0;">过热熔断号（剔除）</h4>
                <p>{}</p>
                </div>
                '''.format(risk_data['hot_fuse'] if risk_data['hot_fuse'] else '无'), unsafe_allow_html=True)
            
            # 展示 Step 3 行情判定
            st.divider()
            st.subheader('📌 Step 3: 行情周期判定')
            
            market_colors = {
                "冷号主导行情": {"bg": "#e3f2fd", "text": "#1565c0"},
                "热号主导行情": {"bg": "#ffebee", "text": "#c62828"},
                "温号主导行情": {"bg": "#fffde7", "text": "#f57f17"},
                "均衡行情": {"bg": "#e8f5e8", "text": "#2e7d32"}
            }
            mc = market_colors.get(market_data['market_type'], market_colors["均衡行情"])
            
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.markdown(f'''
                <div style="background-color: {mc['bg']}; padding: 16px; border-radius: 8px; text-align: center;">
                <h3 style="margin-top: 0; color: {mc['text']};">{market_data['market_type']}</h3>
                <p style="margin-bottom: 0; color: {mc['text']};">判定行情类型</p>
                </div>
                ''', unsafe_allow_html=True)
            with col_m2:
                st.markdown(f'''
                <div style="background-color: {mc['bg']}; padding: 12px; border-radius: 6px;">
                <h4 style="margin-top: 0; color: {mc['text']};">近7期冷热占比</h4>
                <ul style="margin-bottom: 0;">
                <li>冷号占比：{market_data['cold_ratio']:.1%}</li>
                <li>温号占比：{market_data['warm_ratio']:.1%}</li>
                <li>热号占比：{market_data['hot_ratio']:.1%}</li>
                </ul>
                </div>
                ''', unsafe_allow_html=True)
            
            st.markdown('''
                <div style="background-color: #f3e5f5; padding: 12px; border-radius: 6px;">
                <h4 style="margin-top: 0; color: #7b1fa2;">动态仓位分配</h4>
                <ul style="margin-bottom: 0;">
                <li>均衡稳胆流：{}%</li>
                <li>温号轮动流：{}%</li>
                <li>热号主攻流：{}%</li>
                <li>冷号回补流：{}%</li>
                </ul>
                </div>
                '''.format(
                    int(market_data["position"]["stable"]*100),
                    int(market_data["position"]["warm"]*100),
                    int(market_data["position"]["hot"]*100),
                    int(market_data["position"]["cold"]*100)
                ), unsafe_allow_html=True)
            
            # 展示 Step 4-5 核心池
            st.divider()
            st.subheader('📌 Step 4-5: 10码终版核心池')
            col_c1, col_c2 = st.columns([3, 1])
            with col_c1:
                st.markdown('''<div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; margin-bottom: 12px;"><h4 style="margin-top: 0; color: #1565c0;">10码核心池（升序）</h4><p style="font-family: monospace; font-size: 14px;">{}</p></div>'''.format(' '.join(map(str, sorted(core_pool_data['core_pool'])))), unsafe_allow_html=True)
                
                col_flow1, col_flow2 = st.columns(2)
                with col_flow1:
                    st.markdown('''<div style="background-color: #e8f5e8; padding: 12px; border-radius: 6px;"><h4 style="margin-top: 0; color: #2e7d32;">S级稳胆</h4><p>{}</p></div>'''.format(selected_numbers['stable']), unsafe_allow_html=True)
                    st.markdown('''<div style="background-color: #fff3e0; padding: 12px; border-radius: 6px; margin-top: 12px;"><h4 style="margin-top: 0; color: #ef6c00;">B级热号</h4><p>{}</p></div>'''.format(selected_numbers['hot']), unsafe_allow_html=True)
                with col_flow2:
                    st.markdown('''<div style="background-color: #fffde7; padding: 12px; border-radius: 6px;"><h4 style="margin-top: 0; color: #f57f17;">A级温号</h4><p>{}</p></div>'''.format(selected_numbers['warm']), unsafe_allow_html=True)
                    st.markdown('''<div style="background-color: #f3e5f5; padding: 12px; border-radius: 6px; margin-top: 12px;"><h4 style="margin-top: 0; color: #7b1fa2;">C级冷号</h4><p>{}</p></div>'''.format(selected_numbers['cold']), unsafe_allow_html=True)
            with col_c2:
                st.markdown('''<div style="background-color: #fce4ec; padding: 12px; border-radius: 6px; margin-bottom: 12px;"><h4 style="margin-top: 0; color: #c2185b;">一级备选池</h4><p>{}</p></div>'''.format(core_pool_data['backup_pool']['level1']), unsafe_allow_html=True)
                st.markdown('''<div style="background-color: #e0f7fa; padding: 12px; border-radius: 6px; margin-bottom: 12px;"><h4 style="margin-top: 0; color: #006064;">二级对冲池</h4><p>{}</p></div>'''.format(core_pool_data['backup_pool']['level2']), unsafe_allow_html=True)
                st.markdown('''<div style="background-color: #ffebee; padding: 12px; border-radius: 6px;"><h4 style="margin-top: 0; color: #c62828;">三级极端容错池</h4><p>{}</p></div>'''.format(core_pool_data['backup_pool']['level3']), unsafe_allow_html=True)
            
            # 展示 Step 6 组合
            st.divider()
            st.subheader('📌 Step 6: 全玩法组合打法')
            
            tab_8, tab_6, tab_3 = st.tabs(['10组8码', '10组6码', '10组3码'])
            with tab_8:
                col_8_1, col_8_2 = st.columns(2)
                for i, comb in enumerate(combinations['eight_code'], 1):
                    if i <= 5:
                        with col_8_1:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">8-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
                    else:
                        with col_8_2:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">8-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
            with tab_6:
                col_6_1, col_6_2 = st.columns(2)
                for i, comb in enumerate(combinations['six_code'], 1):
                    if i <= 5:
                        with col_6_1:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">6-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
                    else:
                        with col_6_2:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">6-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
            with tab_3:
                col_3_1, col_3_2 = st.columns(2)
                for i, comb in enumerate(combinations['three_code'], 1):
                    if i <= 5:
                        with col_3_1:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">3-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
                    else:
                        with col_3_2:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">3-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
    
    if len(front_df) >= 10 and 'auto_run_sop' in st.session_state and st.session_state['auto_run_sop']:
        last_period = front_df.index[-1]
        n_plus_1 = str(int(last_period) + 1)

        with st.spinner(f'🔄 检测到新增数据，正在自动为 {n_plus_1} 期生成预测...'):
            data = front_df.loc[:last_period].copy()

            prepared_data = step1_prepare_data(data)
            risk_data = step2_risk_control(data, prepared_data)
            market_data = step3_market_judge(data, prepared_data)
            selected_numbers = step4_select_numbers(data, prepared_data, risk_data, market_data)
            core_pool_data = step5_build_core_pool(selected_numbers, market_data, risk_data)
            combinations = step6_build_combinations(core_pool_data['core_pool'], selected_numbers, data)

            prediction_data = {
                'period': n_plus_1,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'auto_generated': True,
                'step1_prepared': {
                    'stats_100': prepared_data['stats_100'].to_dict(),
                    'omission': prepared_data['omission']
                },
                'step2_risk': risk_data,
                'step3_market': market_data,
                'step4_selected': selected_numbers,
                'step5_core_pool': core_pool_data,
                'step6_combinations': combinations,
                'core_pool': ' '.join(map(str, sorted(core_pool_data['core_pool']))),
                'combinations': combinations
            }

            save_prediction(prediction_data, n_plus_1)
            st.session_state['prediction_data'] = prediction_data
            st.session_state['auto_run_sop'] = False

        st.success(f'✅ 自动预测完成！已为 **{n_plus_1}** 期生成预测方案')

        st.divider()
        st.subheader('📌 Step 2: 刚性风控执行结果')
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.markdown('''
            <div style="background-color: #ffebee; padding: 12px; border-radius: 6px;">
            <h4 style="margin-top: 0; color: #c62828;">三期连开号（剔除）</h4>
            <p>{}</p>
            </div>
            '''.format(risk_data['three_consecutive'] if risk_data['three_consecutive'] else '无'), unsafe_allow_html=True)
        with col_r2:
            st.markdown('''
            <div style="background-color: #fff3e0; padding: 12px; border-radius: 6px;">
            <h4 style="margin-top: 0; color: #ef6c00;">两期连开号（降权）</h4>
            <p>{}</p>
            </div>
            '''.format(risk_data['downgrade_list'] if risk_data['downgrade_list'] else '无'), unsafe_allow_html=True)
        with col_r3:
            st.markdown('''
            <div style="background-color: #e3f2fd; padding: 12px; border-radius: 6px;">
            <h4 style="margin-top: 0; color: #1565c0;">过热熔断号（剔除）</h4>
            <p>{}</p>
            </div>
            '''.format(risk_data['hot_fuse'] if risk_data['hot_fuse'] else '无'), unsafe_allow_html=True)

        st.divider()
        st.subheader('📌 Step 3: 行情周期判定')
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown('''
            <div style="background-color: #e8f5e8; padding: 16px; border-radius: 8px; text-align: center;">
            <h3 style="margin-top: 0; color: #2e7d32;">{}</h3>
            <p style="margin-bottom: 0; color: #2e7d32;">判定行情类型</p>
            </div>
            '''.format(market_data['market_type']), unsafe_allow_html=True)
        with col_m2:
            st.markdown('''
            <div style="background-color: #f3e5f5; padding: 12px; border-radius: 6px;">
            <h4 style="margin-top: 0; color: #7b1fa2;">动态仓位分配</h4>
            <ul style="margin-bottom: 0;">
            <li>均衡稳胆流：{}%</li>
            <li>温号轮动流：{}%</li>
            <li>热号主攻流：{}%</li>
            <li>冷号回补流：{}%</li>
            </ul>
            </div>
            '''.format(
                int(market_data["position"]["stable"]*100),
                int(market_data["position"]["warm"]*100),
                int(market_data["position"]["hot"]*100),
                int(market_data["position"]["cold"]*100)
            ), unsafe_allow_html=True)

        st.divider()
        st.subheader('📌 Step 4-5: 15码终版核心池')
        col_c1, col_c2 = st.columns([3, 1])
        with col_c1:
            st.markdown('''<div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; margin-bottom: 12px;"><h4 style="margin-top: 0; color: #1565c0;">15码核心池（升序）</h4><p style="font-family: monospace; font-size: 14px;">{}</p></div>'''.format(' '.join(map(str, sorted(core_pool_data['core_pool'])))), unsafe_allow_html=True)

            col_flow1, col_flow2 = st.columns(2)
            with col_flow1:
                st.markdown('''<div style="background-color: #e8f5e8; padding: 12px; border-radius: 6px;"><h4 style="margin-top: 0; color: #2e7d32;">S级稳胆</h4><p>{}</p></div>'''.format(selected_numbers['stable']), unsafe_allow_html=True)
                st.markdown('''<div style="background-color: #fff3e0; padding: 12px; border-radius: 6px; margin-top: 12px;"><h4 style="margin-top: 0; color: #ef6c00;">B级热号</h4><p>{}</p></div>'''.format(selected_numbers['hot']), unsafe_allow_html=True)
            with col_flow2:
                st.markdown('''<div style="background-color: #fffde7; padding: 12px; border-radius: 6px;"><h4 style="margin-top: 0; color: #f57f17;">A级温号</h4><p>{}</p></div>'''.format(selected_numbers['warm']), unsafe_allow_html=True)
                st.markdown('''<div style="background-color: #f3e5f5; padding: 12px; border-radius: 6px; margin-top: 12px;"><h4 style="margin-top: 0; color: #7b1fa2;">C级冷号</h4><p>{}</p></div>'''.format(selected_numbers['cold']), unsafe_allow_html=True)
        with col_c2:
            st.markdown('''<div style="background-color: #fce4ec; padding: 12px; border-radius: 6px; margin-bottom: 12px;"><h4 style="margin-top: 0; color: #c2185b;">一级备选池</h4><p>{}</p></div>'''.format(core_pool_data['backup_pool']['level1']), unsafe_allow_html=True)
            st.markdown('''<div style="background-color: #e0f7fa; padding: 12px; border-radius: 6px; margin-bottom: 12px;"><h4 style="margin-top: 0; color: #006064;">二级对冲池</h4><p>{}</p></div>'''.format(core_pool_data['backup_pool']['level2']), unsafe_allow_html=True)
            st.markdown('''<div style="background-color: #ffebee; padding: 12px; border-radius: 6px;"><h4 style="margin-top: 0; color: #c62828;">三级极端容错池</h4><p>{}</p></div>'''.format(core_pool_data['backup_pool']['level3']), unsafe_allow_html=True)

        st.divider()
        st.subheader('📌 Step 6: 全玩法组合打法（自动生成）')

        tab_8, tab_6, tab_3 = st.tabs(['10组8码', '10组6码', '10组3码'])
        with tab_8:
            col_8_1, col_8_2 = st.columns(2)
            for i, comb in enumerate(combinations['eight_code'], 1):
                if i <= 5:
                    with col_8_1:
                        st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">8-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
                else:
                    with col_8_2:
                        st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">8-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
        with tab_6:
            col_6_1, col_6_2 = st.columns(2)
            for i, comb in enumerate(combinations['six_code'], 1):
                if i <= 5:
                    with col_6_1:
                        st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">6-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
                else:
                    with col_6_2:
                        st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">6-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
        with tab_3:
            col_3_1, col_3_2 = st.columns(2)
            for i, comb in enumerate(combinations['three_code'], 1):
                if i <= 5:
                    with col_3_1:
                        st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">3-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
                else:
                    with col_3_2:
                        st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">3-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)

        st.info(f'📅 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}（自动执行）')
    
    elif len(st.session_state.lottery_data) < 10:
        st.warning('⚠️ 数据不足 10 期，无法执行完整 SOP 流程')

# ==================== 【Tab 8】体系全流程 SOP（后段库专用） ====================
with tabs[7]:
    st.header('📋 体系全流程标准化执行 SOP')
    st.divider()

    # ==================== 【SOP 核心算法模块】 ====================
    def build_back_segment_data():
        """从 Tab 6 后段库获取数据"""
        if 'back_segment_data' in st.session_state:
            return st.session_state['back_segment_data']
        back_segment_data = {}
        for period in st.session_state.lottery_data.index:
            numbers = st.session_state.lottery_data.loc[period].tolist()
            back_numbers = sorted([int(n) for n in numbers if 41 <= n <= 80])
            if back_numbers:
                back_segment_data[period] = back_numbers
        return back_segment_data

    def convert_to_dataframe_back(segment_data):
        """将后段库数据转换为DataFrame格式"""
        max_len = max(len(v) for v in segment_data.values()) if segment_data else 0
        rows = []
        for period in sorted(segment_data.keys()):
            nums = segment_data[period]
            row = nums + [None] * (max_len - len(nums))
            rows.append(row)
        df = pd.DataFrame(rows, index=sorted(segment_data.keys()))
        return df

    def calculate_number_stats_back(data, period):
        """计算号码的基础统计数据（后段库）"""
        recent_data = data.tail(period)
        all_numbers = []
        for col in recent_data.columns:
            all_numbers.extend(recent_data[col].dropna().astype(int).tolist())
        
        number_counts = pd.Series(all_numbers).value_counts().reindex(range(41, 81), fill_value=0)
        return number_counts

    def calculate_omission_back(data, num):
        """计算号码的遗漏期数"""
        last_appear = -1
        for i, (period, row) in enumerate(data.iloc[::-1].iterrows()):
            if num in row.values:
                last_appear = i
                break
        return last_appear if last_appear != -1 else len(data)

    def calculate_cooccurrence_back(data, num1, num2, period=50):
        """计算两码共现次数"""
        recent_data = data.tail(period)
        count = 0
        for _, row in recent_data.iterrows():
            nums = set(row.dropna().astype(int).tolist())
            if num1 in nums and num2 in nums:
                count += 1
        return count

    def step1_prepare_data_back(data):
        """Step 1: 基础数据准备"""
        stats_100 = calculate_number_stats_back(data, min(100, len(data)))
        stats_50 = calculate_number_stats_back(data, min(50, len(data)))
        stats_30 = calculate_number_stats_back(data, min(30, len(data)))
        stats_20 = calculate_number_stats_back(data, min(20, len(data)))
        stats_10 = calculate_number_stats_back(data, min(10, len(data)))
        
        omission = {}
        for num in range(41, 81):
            omission[num] = calculate_omission_back(data, num)
        
        return {
            'stats_100': stats_100,
            'stats_50': stats_50,
            'stats_30': stats_30,
            'stats_20': stats_20,
            'stats_10': stats_10,
            'omission': omission
        }

    def step2_risk_control_back(data, prepared_data):
        """Step 2: 刚性风控规则执行"""
        last_period = data.index[-1]
        last_2_period = data.index[-2] if len(data) >= 2 else None
        last_3_period = data.index[-3] if len(data) >= 3 else None
        
        last_nums = set(data.loc[last_period].dropna().astype(int).tolist())
        last_2_nums = set(data.loc[last_2_period].dropna().astype(int).tolist()) if last_2_period else set()
        last_3_nums = set(data.loc[last_3_period].dropna().astype(int).tolist()) if last_3_period else set()
        
        three_consecutive = last_nums & last_2_nums & last_3_nums
        
        two_consecutive = last_nums & last_2_nums
        
        hot_fuse = []
        stats_10 = prepared_data['stats_10']
        for num in range(41, 81):
            if stats_10[num] >= 4:
                hot_fuse.append(num)
        
        exclude_list = list(three_consecutive) + list(hot_fuse)
        exclude_list = list(set(exclude_list))
        
        downgrade_list = list(two_consecutive - set(exclude_list))
        
        return {
            'three_consecutive': list(three_consecutive),
            'two_consecutive': list(two_consecutive),
            'hot_fuse': hot_fuse,
            'exclude_list': exclude_list,
            'downgrade_list': downgrade_list
        }

    def step3_market_judge_back(data, prepared_data):
        """Step 3: 行情周期判定"""
        recent_7 = data.tail(7)
        
        stats_50 = prepared_data['stats_50']
        hot_thresh = stats_50.quantile(0.8)
        cold_thresh = stats_50.quantile(0.2)
        
        warm_count = 0
        hot_count = 0
        cold_count = 0
        
        for _, row in recent_7.iterrows():
            nums = row.dropna().astype(int).tolist()
            for num in nums:
                if stats_50[num] >= hot_thresh:
                    hot_count += 1
                elif stats_50[num] <= cold_thresh:
                    cold_count += 1
                else:
                    warm_count += 1
        
        total = hot_count + warm_count + cold_count
        warm_ratio = warm_count / total if total > 0 else 0
        hot_ratio = hot_count / total if total > 0 else 0
        
        if warm_ratio >= 0.45:
            market_type = "温号主导行情"
        elif hot_ratio >= 0.35:
            market_type = "热号主导行情"
        else:
            market_type = "均衡行情"
        
        if market_type == "温号主导行情":
            position = {'stable': 0.25, 'warm': 0.50, 'hot': 0.10, 'cold': 0.15}
        elif market_type == "热号主导行情":
            position = {'stable': 0.35, 'warm': 0.30, 'hot': 0.20, 'cold': 0.15}
        else:
            position = {'stable': 0.30, 'warm': 0.40, 'hot': 0.15, 'cold': 0.15}
        
        return {
            'market_type': market_type,
            'warm_ratio': warm_ratio,
            'hot_ratio': hot_ratio,
            'position': position
        }

    def step4_select_numbers_back(data, prepared_data, risk_data, market_data):
        """Step 4: 三大流派号码筛选（后段库专用）"""
        stats_100 = prepared_data['stats_100']
        stats_50 = prepared_data['stats_50']
        stats_30 = prepared_data['stats_30']
        stats_20 = prepared_data['stats_20']
        stats_10 = prepared_data['stats_10']
        omission = prepared_data['omission']
        exclude_list = risk_data['exclude_list']
        
        stable_candidates = []
        for num in range(41, 81):
            if num in exclude_list:
                continue
            if (stats_100[num] >= 10 and 
                stats_30[num] >= 3 and 
                stats_10[num] >= 2 and
                omission[num] <= 4):
                stable_candidates.append(num)
        
        stable_scores = {}
        for num in stable_candidates:
            stable_scores[num] = stats_100[num] * 0.4 + stats_50[num] * 0.3 + stats_30[num] * 0.3
        stable_candidates = sorted(stable_candidates, key=lambda x: stable_scores[x], reverse=True)[:5]
        
        warm_candidates = []
        for num in range(41, 81):
            if num in exclude_list or num in stable_candidates:
                continue
            if (3 <= omission[num] <= 6 and 
                stats_30[num] >= 3 and
                1 <= stats_10[num] <= 2):
                warm_candidates.append(num)
        
        warm_scores = {}
        for num in warm_candidates:
            score = stats_30[num]
            for stable_num in stable_candidates[:3]:
                score += calculate_cooccurrence_back(data, num, stable_num, 30) * 2
            warm_scores[num] = score
        warm_candidates = sorted(warm_candidates, key=lambda x: warm_scores[x], reverse=True)[:6]
        
        hot_candidates = []
        for num in range(41, 81):
            if num in exclude_list or num in stable_candidates or num in warm_candidates:
                continue
            if (stats_50[num] >= 6 and
                2 <= stats_10[num] <= 3 and
                omission[num] <= 3):
                hot_candidates.append(num)
        
        hot_candidates = sorted(hot_candidates, key=lambda x: stats_50[x], reverse=True)[:3]
        
        cold_candidates = []
        for num in range(41, 81):
            if num in exclude_list or num in stable_candidates or num in warm_candidates or num in hot_candidates:
                continue
            if (5 <= omission[num] <= 10 and
                stats_100[num] >= 8):
                cold_candidates.append(num)
        
        cold_candidates = sorted(cold_candidates, key=lambda x: omission[x])[:3]
        
        return {
            'stable': stable_candidates,
            'warm': warm_candidates,
            'hot': hot_candidates,
            'cold': cold_candidates
        }

    def step5_build_core_pool_back(selected_numbers, market_data, risk_data):
        """Step 5: 10码核心池锁定（后段库专用）"""
        position = market_data['position']
        total_size = 10
        
        stable_count = max(1, int(total_size * position['stable']))
        warm_count = max(1, int(total_size * position['warm']))
        hot_count = max(1, int(total_size * position['hot']))
        cold_count = total_size - stable_count - warm_count - hot_count
        
        if cold_count < 1:
            cold_count = 1
            hot_count = max(1, hot_count - 1)
        
        core_pool = []
        
        stable_nums = selected_numbers['stable'][:stable_count] if selected_numbers['stable'] else []
        warm_nums = selected_numbers['warm'][:warm_count] if selected_numbers['warm'] else []
        hot_nums = selected_numbers['hot'][:hot_count] if selected_numbers['hot'] else []
        cold_nums = selected_numbers['cold'][:cold_count] if selected_numbers['cold'] else []
        
        core_pool.extend(stable_nums)
        core_pool.extend(warm_nums)
        core_pool.extend(hot_nums)
        core_pool.extend(cold_nums)
        
        core_pool = sorted(list(set(core_pool)))
        
        if len(core_pool) < total_size:
            all_available = selected_numbers['stable'] + selected_numbers['warm'] + selected_numbers['hot'] + selected_numbers['cold']
            all_available = sorted(list(set(all_available)))
            for num in all_available:
                if num not in core_pool and len(core_pool) < total_size:
                    core_pool.append(num)
        
        backup_pool = {
            'level1': [num for num in selected_numbers['stable'] + selected_numbers['warm'] if num not in core_pool][:4],
            'level2': [num for num in selected_numbers['hot'] + selected_numbers['cold'] if num not in core_pool][:4],
            'level3': risk_data['three_consecutive'] + risk_data['downgrade_list']
        }
        
        return {
            'core_pool': core_pool,
            'backup_pool': backup_pool
        }

    def step6_build_combinations_back(core_pool, selected_numbers, data):
        """Step 6: 三层对冲组合构建"""
        
        core_pool_sorted = sorted(core_pool)
        n = len(core_pool_sorted)
        
        eight_code = []
        for i in range(10):
            if n >= 8:
                start = i % n
                step = ((i // 2) % 3) + 1
                comb = []
                for j in range(8):
                    idx = (start + j * step) % n
                    comb.append(core_pool_sorted[idx])
                comb = sorted(list(set(comb)))
                while len(comb) < 8:
                    for num in core_pool_sorted:
                        if num not in comb:
                            comb.append(num)
                            break
                    comb.sort()
            else:
                comb = (core_pool_sorted * 2)[:8]
            eight_code.append(sorted(comb))
        
        six_code = []
        for i in range(10):
            if n >= 6:
                if i == 0:
                    comb = core_pool_sorted[:6]
                elif i == 1:
                    comb = core_pool_sorted[-6:]
                elif i == 2:
                    comb = [core_pool_sorted[i % n] for i in [0, 2, 4, 6, 8, 10]][:6]
                elif i == 3:
                    comb = [core_pool_sorted[i % n] for i in [1, 3, 5, 7, 9, 11]][:6]
                elif i == 4:
                    comb = [core_pool_sorted[i % n] for i in [0, 1, n-2, n-1, n//2-1, n//2]][:6]
                elif i == 5:
                    comb = [core_pool_sorted[i % n] for i in [0, n//3, 2*n//3, n-1, 1, n-2]][:6]
                elif i == 6:
                    comb = [core_pool_sorted[i % n] for i in [0, n-1, 1, n-2, 2, n-3]][:6]
                elif i == 7:
                    comb = [core_pool_sorted[i % n] for i in range(0, n, 2)][:6]
                elif i == 8:
                    comb = [core_pool_sorted[i % n] for i in range(1, n, 2)][:6]
                else:
                    mid = n // 2
                    comb = core_pool_sorted[max(0, mid-3):min(n, mid+3)]
                comb = sorted(list(set(comb)))
                while len(comb) < 6:
                    for num in core_pool_sorted:
                        if num not in comb:
                            comb.append(num)
                            break
                    comb.sort()
            else:
                comb = (core_pool_sorted * 2)[:6]
            six_code.append(sorted(comb))
        
        three_code = []
        for i in range(10):
            if n >= 3:
                if i == 0:
                    comb = core_pool_sorted[:3]
                elif i == 1:
                    comb = core_pool_sorted[-3:]
                elif i == 2:
                    comb = [core_pool_sorted[0], core_pool_sorted[n//2], core_pool_sorted[-1]]
                elif i == 3:
                    comb = [core_pool_sorted[1], core_pool_sorted[n//2], core_pool_sorted[-2]]
                elif i == 4:
                    comb = [core_pool_sorted[0], core_pool_sorted[1], core_pool_sorted[2]]
                elif i == 5:
                    comb = [core_pool_sorted[-3], core_pool_sorted[-2], core_pool_sorted[-1]]
                elif i == 6:
                    comb = [core_pool_sorted[0], core_pool_sorted[n//3], core_pool_sorted[2*n//3]]
                elif i == 7:
                    comb = [core_pool_sorted[1], core_pool_sorted[n//3+1], core_pool_sorted[2*n//3+1]]
                elif i == 8:
                    comb = [core_pool_sorted[0], core_pool_sorted[n-2], core_pool_sorted[n-1]]
                elif i == 9:
                    comb = [core_pool_sorted[n//4], core_pool_sorted[n//2], core_pool_sorted[3*n//4]]
                comb = sorted(list(set(comb)))
                while len(comb) < 3:
                    for num in core_pool_sorted:
                        if num not in comb:
                            comb.append(num)
                            break
                    comb.sort()
            else:
                comb = (core_pool_sorted * 2)[:3]
            three_code.append(sorted(comb))
        
        return {
            'eight_code': eight_code,
            'six_code': six_code,
            'three_code': three_code
        }

    # ==================== 【SOP 主界面】 ====================
    st.markdown("""
    ## 📋 体系全流程标准化执行 SOP（后段库专用）
    <div style="background-color: #f0f2f6; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
    <p style="font-size: 16px; line-height: 1.6;">
    本 SOP 基于 Tab 6 后段库（41-80区间）数据进行预测，每期严格按步骤执行，确保预测的科学性和一致性。
    </p>
    <ul style="margin-top: 10px; font-size: 14px;">
    <li>✅ 8步标准化流程，确保预测的科学性和一致性</li>
    <li>✅ 基于多周期数据的量化分析（41-80区间）</li>
    <li>✅ 自动生成10码核心池和三层对冲组合</li>
    <li>✅ 完整的风控机制，避免极端情况</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    back_segment_data = build_back_segment_data()
    back_df = convert_to_dataframe_back(back_segment_data)
    
    st.divider()
    st.subheader('🔮 为 N+1 期进行预测')
    
    if len(back_df) >= 10:
        period_list = back_df.index.tolist()
        sop_n_period = st.selectbox(
            '请选择 N 期数（已开奖的最后一期）',
            period_list,
            index=len(period_list)-1,
            help='选择已开奖的最后一期 N，系统将为 N+1 期准备预测',
            key='sop_period_back'
        )
        
        n_plus_1 = str(int(sop_n_period) + 1)
        st.write(f'已选择 **{sop_n_period}** 期，将为 **{n_plus_1}** 期进行预测')
        
        if st.button('🚀 执行完整 SOP 流程', type='primary', use_container_width=True, key='sop_button_back'):
            data = back_df.loc[:sop_n_period].copy()
            
            col_progress, col_status = st.columns([1, 3])
            with col_progress:
                progress_bar = st.progress(0)
            with col_status:
                status_text = st.empty()
            
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 1/8: 基础数据准备...</div>', unsafe_allow_html=True)
            prepared_data = step1_prepare_data_back(data)
            progress_bar.progress(12)
            
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 2/8: 刚性风控规则执行...</div>', unsafe_allow_html=True)
            risk_data = step2_risk_control_back(data, prepared_data)
            progress_bar.progress(25)
            
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 3/8: 行情周期判定...</div>', unsafe_allow_html=True)
            market_data = step3_market_judge_back(data, prepared_data)
            progress_bar.progress(37)
            
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 4/8: 三大流派号码筛选...</div>', unsafe_allow_html=True)
            selected_numbers = step4_select_numbers_back(data, prepared_data, risk_data, market_data)
            progress_bar.progress(50)
            
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 5/8: 10码核心池锁定...</div>', unsafe_allow_html=True)
            core_pool_data = step5_build_core_pool_back(selected_numbers, market_data, risk_data)
            progress_bar.progress(62)
            
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 6/8: 三层对冲组合构建...</div>', unsafe_allow_html=True)
            combinations = step6_build_combinations_back(core_pool_data['core_pool'], selected_numbers, data)
            progress_bar.progress(75)
            
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 7/8: 终版方案存档锁定...</div>', unsafe_allow_html=True)
            prediction_data = {
                'period': n_plus_1,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'step1_prepared': {
                    'stats_100': prepared_data['stats_100'].to_dict(),
                    'omission': prepared_data['omission']
                },
                'step2_risk': risk_data,
                'step3_market': market_data,
                'step4_selected': selected_numbers,
                'step5_core_pool': core_pool_data,
                'step6_combinations': combinations,
                'core_pool': ' '.join(map(str, sorted(core_pool_data['core_pool']))),
                'combinations': combinations
            }
            filename = save_prediction(prediction_data, n_plus_1)
            st.session_state['prediction_data'] = prediction_data
            progress_bar.progress(87)
            
            status_text.text('Step 8/8: 完成！')
            progress_bar.progress(100)
            
            st.success(f'✅ SOP 流程执行完成！预测方案已保存至：{filename}')
            st.divider()
            
            st.subheader('📌 Step 2: 刚性风控执行结果')
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.markdown('''
                <div style="background-color: #ffebee; padding: 12px; border-radius: 6px;">
                <h4 style="margin-top: 0; color: #c62828;">三期连开号（剔除）</h4>
                <p>{}</p>
                </div>
                '''.format(risk_data['three_consecutive'] if risk_data['three_consecutive'] else '无'), unsafe_allow_html=True)
            with col_r2:
                st.markdown('''
                <div style="background-color: #fff3e0; padding: 12px; border-radius: 6px;">
                <h4 style="margin-top: 0; color: #ef6c00;">两期连开号（降权）</h4>
                <p>{}</p>
                </div>
                '''.format(risk_data['downgrade_list'] if risk_data['downgrade_list'] else '无'), unsafe_allow_html=True)
            with col_r3:
                st.markdown('''
                <div style="background-color: #e3f2fd; padding: 12px; border-radius: 6px;">
                <h4 style="margin-top: 0; color: #1565c0;">过热熔断号（剔除）</h4>
                <p>{}</p>
                </div>
                '''.format(risk_data['hot_fuse'] if risk_data['hot_fuse'] else '无'), unsafe_allow_html=True)
            
            st.divider()
            st.subheader('📌 Step 3: 行情周期判定')
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.markdown('''
                <div style="background-color: #e8f5e8; padding: 16px; border-radius: 8px; text-align: center;">
                <h3 style="margin-top: 0; color: #2e7d32;">{}</h3>
                <p style="margin-bottom: 0; color: #2e7d32;">判定行情类型</p>
                </div>
                '''.format(market_data['market_type']), unsafe_allow_html=True)
            with col_m2:
                st.markdown('''
                <div style="background-color: #f3e5f5; padding: 12px; border-radius: 6px;">
                <h4 style="margin-top: 0; color: #7b1fa2;">动态仓位分配</h4>
                <ul style="margin-bottom: 0;">
                <li>均衡稳胆流：{}%</li>
                <li>温号轮动流：{}%</li>
                <li>热号主攻流：{}%</li>
                <li>冷号回补流：{}%</li>
                </ul>
                </div>
                '''.format(
                    int(market_data["position"]["stable"]*100),
                    int(market_data["position"]["warm"]*100),
                    int(market_data["position"]["hot"]*100),
                    int(market_data["position"]["cold"]*100)
                ), unsafe_allow_html=True)
            
            st.divider()
            st.subheader('📌 Step 4-5: 10码终版核心池')
            col_c1, col_c2 = st.columns([3, 1])
            with col_c1:
                st.markdown('''<div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; margin-bottom: 12px;"><h4 style="margin-top: 0; color: #1565c0;">10码核心池（升序）</h4><p style="font-family: monospace; font-size: 14px;">{}</p></div>'''.format(' '.join(map(str, sorted(core_pool_data['core_pool'])))), unsafe_allow_html=True)
                
                col_flow1, col_flow2 = st.columns(2)
                with col_flow1:
                    st.markdown('''<div style="background-color: #e8f5e8; padding: 12px; border-radius: 6px;"><h4 style="margin-top: 0; color: #2e7d32;">S级稳胆</h4><p>{}</p></div>'''.format(selected_numbers['stable']), unsafe_allow_html=True)
                    st.markdown('''<div style="background-color: #fff3e0; padding: 12px; border-radius: 6px; margin-top: 12px;"><h4 style="margin-top: 0; color: #ef6c00;">B级热号</h4><p>{}</p></div>'''.format(selected_numbers['hot']), unsafe_allow_html=True)
                with col_flow2:
                    st.markdown('''<div style="background-color: #fffde7; padding: 12px; border-radius: 6px;"><h4 style="margin-top: 0; color: #f57f17;">A级温号</h4><p>{}</p></div>'''.format(selected_numbers['warm']), unsafe_allow_html=True)
                    st.markdown('''<div style="background-color: #f3e5f5; padding: 12px; border-radius: 6px; margin-top: 12px;"><h4 style="margin-top: 0; color: #7b1fa2;">C级冷号</h4><p>{}</p></div>'''.format(selected_numbers['cold']), unsafe_allow_html=True)
            with col_c2:
                st.markdown('''<div style="background-color: #fce4ec; padding: 12px; border-radius: 6px; margin-bottom: 12px;"><h4 style="margin-top: 0; color: #c2185b;">一级备选池</h4><p>{}</p></div>'''.format(core_pool_data['backup_pool']['level1']), unsafe_allow_html=True)
                st.markdown('''<div style="background-color: #e0f7fa; padding: 12px; border-radius: 6px; margin-bottom: 12px;"><h4 style="margin-top: 0; color: #006064;">二级对冲池</h4><p>{}</p></div>'''.format(core_pool_data['backup_pool']['level2']), unsafe_allow_html=True)
                st.markdown('''<div style="background-color: #ffebee; padding: 12px; border-radius: 6px;"><h4 style="margin-top: 0; color: #c62828;">三级极端容错池</h4><p>{}</p></div>'''.format(core_pool_data['backup_pool']['level3']), unsafe_allow_html=True)
            
            st.divider()
            st.subheader('📌 Step 6: 全玩法组合打法')
            
            tab_8, tab_6, tab_3 = st.tabs(['10组8码', '10组6码', '10组3码'])
            with tab_8:
                col_8_1, col_8_2 = st.columns(2)
                for i, comb in enumerate(combinations['eight_code'], 1):
                    if i <= 5:
                        with col_8_1:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">8-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
                    else:
                        with col_8_2:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">8-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
            with tab_6:
                col_6_1, col_6_2 = st.columns(2)
                for i, comb in enumerate(combinations['six_code'], 1):
                    if i <= 5:
                        with col_6_1:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">6-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
                    else:
                        with col_6_2:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">6-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
            with tab_3:
                col_3_1, col_3_2 = st.columns(2)
                for i, comb in enumerate(combinations['three_code'], 1):
                    if i <= 5:
                        with col_3_1:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">3-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
                    else:
                        with col_3_2:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">3-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
    
    elif len(st.session_state.lottery_data) < 10:
        st.warning('⚠️ 数据不足 10 期，无法执行完整 SOP 流程')

# ==================== 【Tab 9】号码关联分析 ====================
with tabs[8]:
    st.header('🔍 号码关联分析')
    st.markdown('基于 Tab 4 组合同出数据，输入号码搜索关联号码，找出与多个输入号码都有关联的高频号码。')
    st.divider()

    if len(st.session_state.lottery_data) >= 5:
        data = st.session_state.lottery_data
        
        def calculate_combinations(data, period, combo_size):
            if period == '全部':
                recent_data = data
            else:
                recent_data = data.tail(period) if len(data) >= period else data
            combo_counts = {}
            for idx, row in recent_data.iterrows():
                nums = sorted(set(row.dropna().astype(int).tolist()))
                for combo in itertools.combinations(nums, combo_size):
                    key = tuple(sorted(combo))
                    combo_counts[key] = combo_counts.get(key, 0) + 1
            return combo_counts
        
        input_nums_str = st.text_input(
            '输入号码（用空格或逗号分隔，如：3 15 23）',
            '',
            key='tab9_input_nums',
            help='输入多个号码，系统将搜索与这些号码同出的关联号码'
        )
        
        combo_size = st.selectbox(
            '选择组合类型',
            ['三码同出', '四码同出', '五码同出'],
            index=0,
            key='tab9_combo_size'
        )
        
        period_options = ['全部', 100, 50, 30, 10, 5]
        selected_period = st.selectbox(
            '选择分析周期',
            period_options,
            index=0,
            key='tab9_period_select'
        )
        
        if selected_period == '全部':
            long_period = '全部'
            mid_period = 50
            short_period = 10
        elif selected_period == 100:
            long_period = 100
            mid_period = 50
            short_period = 10
        elif selected_period == 50:
            long_period = 50
            mid_period = 30
            short_period = 5
        elif selected_period == 30:
            long_period = 30
            mid_period = 10
            short_period = 5
        elif selected_period == 10:
            long_period = 10
            mid_period = 5
            short_period = 3
        else:
            long_period = 5
            mid_period = 3
            short_period = 2
        
        long_label = '全部期' if long_period == '全部' else f'近{long_period}期'
        mid_label = f'近{mid_period}期'
        short_label = f'近{short_period}期'
        
        combo_size_map = {'三码同出': 3, '四码同出': 4, '五码同出': 5}
        size = combo_size_map[combo_size]
        
        if input_nums_str:
            input_nums = []
            for num_str in input_nums_str.replace(',', ' ').split():
                try:
                    num = int(num_str)
                    if 1 <= num <= 80:
                        input_nums.append(num)
                except ValueError:
                    pass
            
            input_nums = sorted(list(set(input_nums)))
            
            if input_nums:
                st.markdown(f'''<div style="background-color: #e3f2fd; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
                <span style="color: #1565c0;">📌 输入号码：{', '.join(str(n) for n in input_nums)}</span>
                </div>''', unsafe_allow_html=True)
                
                combo_long = calculate_combinations(data, long_period, size)
                combo_mid = calculate_combinations(data, mid_period, size)
                combo_short = calculate_combinations(data, short_period, size)
                
                all_combos = {}
                for combo, cnt in combo_long.items():
                    all_combos[combo] = {long_label: cnt, mid_label: combo_mid.get(combo, 0), short_label: combo_short.get(combo, 0)}
                
                matching_combos = []
                for combo, counts in all_combos.items():
                    matched_input = [n for n in input_nums if n in combo]
                    if matched_input:
                        other_nums = [n for n in combo if n not in input_nums]
                        if other_nums:
                            matching_combos.append({
                                '组合': '-'.join(f'{n:02d}' for n in combo),
                                '匹配输入': ', '.join(str(n) for n in matched_input),
                                '关联号码': ', '.join(str(n) for n in other_nums),
                                long_label: counts[long_label],
                                mid_label: counts[mid_label],
                                short_label: counts[short_label],
                                '匹配数': len(matched_input)
                            })
                
                df_matching = pd.DataFrame(matching_combos)
                df_matching = df_matching.sort_values(['匹配数', long_label], ascending=[False, False])
                
                st.subheader('📊 包含输入号码的同出组合')
                st.markdown(f'''<div style="background-color: #e8f5e8; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
                <span style="color: #2e7d32;">共找到 {len(df_matching)} 组包含输入号码的{combo_size}组合</span>
                </div>''', unsafe_allow_html=True)
                st.dataframe(df_matching, use_container_width=True, hide_index=True)
                
                st.subheader('🔥 关联号码排行榜（前10名）')
                
                num_association = {}
                for combo, counts in all_combos.items():
                    matched_count = sum(1 for n in input_nums if n in combo)
                    if matched_count > 0:
                        for num in combo:
                            if num not in input_nums:
                                if num not in num_association:
                                    num_association[num] = {'关联次数': 0, '关联组合': [], '匹配输入': set()}
                                num_association[num]['关联次数'] += 1
                                num_association[num]['关联组合'].append('-'.join(f'{n:02d}' for n in combo))
                                for in_num in input_nums:
                                    if in_num in combo:
                                        num_association[num]['匹配输入'].add(in_num)
                
                filtered_associations = {k: v for k, v in num_association.items() if v['关联次数'] >= 2}
                sorted_associations = sorted(
                    filtered_associations.items(),
                    key=lambda x: (-x[1]['关联次数'], -len(x[1]['匹配输入']))
                )[:10]
                
                if sorted_associations:
                    rows = []
                    for num, info in sorted_associations:
                        rows.append({
                            '关联号码': num,
                            '关联次数': info['关联次数'],
                            '关联输入号码数': len(info['匹配输入']),
                            '关联输入号码': ', '.join(str(n) for n in sorted(info['匹配输入']))
                        })
                    
                    df_top = pd.DataFrame(rows)
                    st.dataframe(df_top, use_container_width=True, hide_index=True)
                    
                    st.subheader('📋 详细关联信息')
                    for num, info in sorted_associations:
                        st.markdown(f'''
                        <div style="background-color: #fff3e0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                        <h4 style="margin-top: 0; color: #ef6c00;">号码 {num}（关联 {info['关联次数']} 次）</h4>
                        <p><strong>关联输入号码：</strong>{', '.join(str(n) for n in sorted(info['匹配输入']))}</p>
                        <p><strong>关联组合：</strong>{', '.join(info['关联组合'][:10])}{'...' if len(info['关联组合']) > 10 else ''}</p>
                        </div>
                        ''', unsafe_allow_html=True)
                else:
                    st.info('暂无与输入号码关联的其他号码')
            else:
                st.warning('⚠️ 请输入有效的号码（1-80之间）')
        else:
            st.info('💡 请在上方输入框中输入号码，系统将搜索与之关联的号码组合')
    else:
        st.warning('⚠️ 数据不足 5 期，无法进行分析')

# ==================== 【Tab 10】三层体系预测系统 ====================
with tabs[9]:
    st.header('🎯 乐8三维融合预测系统')
    st.markdown('''<div style="background-color: #f0f2f6; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
    <p style="font-size: 16px; line-height: 1.6;">基于Tab 11三维融合体系架构实现的完整预测系统，对接Tab 1号码库数据。</p>
    <ul style="margin-top: 10px; font-size: 14px;">
    <li>✅ 第一层：宏观边界层（跨度预判 → 奇偶比预判 → 012路预判 → 和值校验）</li>
    <li>✅ 第二层：中观杀号层（双重交叉验证，10个杀号+10个待观察号）</li>
    <li>✅ 第三层：微观选号层（梯度体系 + 重合度评分）</li>
    </ul>
    </div>''', unsafe_allow_html=True)
    
    st.markdown('### 📋 基础规范（与Tab 11一致）')
    col_spec1, col_spec2 = st.columns(2)
    with col_spec1:
        st.markdown('''
        **冷热号定义（近10期）:**
        - 热号：出现≥5次
        - 温号：出现3-4次
        - 冷号：出现≤2次
        ''')
    with col_spec2:
        st.markdown('''
        **分段标准（彩侠原版）:**
        - 1段：01-20 | 2段：10-40 | 3段：30-60 | 4段：40-70 | 5段：60-80
        ''')
    
    if st.session_state.lottery_data.empty:
        st.warning('⚠️ 请先在Tab 1中添加号码数据')
    else:
        period_list = st.session_state.lottery_data.index.tolist()[::-1]
        
        col_period, col_button = st.columns([1, 2])
        
        with col_period:
            selected_base_period = st.selectbox('选择基准期数（预测下一期号码）', period_list, index=0)
        
        if st.button('🚀 执行预测', type='primary', use_container_width=True):
            original_index = st.session_state.lottery_data.index.get_loc(selected_base_period)
            if original_index < 9:
                st.warning(f'⚠️ 数据不足，{selected_base_period}期之前只有{original_index}期数据，无法进行完整预测')
                st.stop()
            
            data = st.session_state.lottery_data.iloc[:original_index + 1]
            
            all_numbers = get_all_numbers()
            
            year = int(selected_base_period[:4])
            period_num = int(selected_base_period[4:])
            next_year = year
            next_period_num = period_num + 1
            target_period = f"{next_year}{next_period_num:03d}"
            
            st.markdown(f'''<div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
            <h4 style="margin-top: 0; color: #1565c0;">🎯 预测目标期号</h4>
            <p style="font-size: 24px; font-weight: bold;">{target_period}</p>
            <p style="font-size: 14px; color: #666;">基准期号：{selected_base_period} | 基于该期及之前共{len(data)}期历史数据进行预测</p>
            </div>''', unsafe_allow_html=True)
            
            st.subheader('📊 第一层：宏观边界层')
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('### 3.1 跨度预判（菲姐・振幅周期法）')
                st.markdown('*统计周期：近10期，近5期权重70%，远5期权重30%*')
                span_range, period_type, span_info = predict_span(data)
                if span_range:
                    st.markdown(f'''
                    - **周期类型**: {period_type}
                    - **上期振幅**: {span_info['amplitudes'][-1]}
                    - **本期跨度区间**: <span style="color: #c62828; font-weight: bold;">{span_range[0]}-{span_range[1]}</span>
                    ''', unsafe_allow_html=True)
                    st.markdown(f'''<div style="background-color: #fff3e0; padding: 12px; border-radius: 6px;">
                    <small>近10期跨度: {span_info['spans']}</small>
                    </div>''', unsafe_allow_html=True)
                else:
                    st.info('数据不足，无法进行跨度预判')
            
            with col2:
                st.markdown('### 3.2 奇偶比预判（凡哥・冷热转换法）')
                st.markdown('*统计周期：近7期+近3期，近3期权重60%，远4期权重40%*')
                odd_range, even_range, ratio_info = predict_odd_even_ratio(data)
                if odd_range:
                    st.markdown(f'''
                    - **近7期差值D7**: {ratio_info['d7']}
                    - **近3期差值D3**: {ratio_info['d3']}
                    - **加权差值**: {ratio_info['weighted_diff']:.1f}
                    - **奇数预判**: {odd_range[0]}-{odd_range[1]} 个
                    - **偶数预判**: {even_range[0]}-{even_range[1]} 个
                    - **奇偶比区间**: <span style="color: #c62828; font-weight: bold;">{odd_range[0]}-{odd_range[1]}:{even_range[0]}-{even_range[1]}</span>
                    ''', unsafe_allow_html=True)
                else:
                    st.info('数据不足，无法进行奇偶比预判')
            
            col3, col4 = st.columns(2)
            
            with col3:
                st.markdown('### 3.3 012路个数预判（菲姐・趋势均值法）')
                st.markdown('*统计周期：近10期+近5期，近5期权重60%，远5期权重40%*')
                road_counts, road_info = predict_road_counts(data)
                if road_counts:
                    n0, n1, n2 = road_counts
                    st.markdown(f'''
                    - **0路均值(近5期)**: {road_info['means_recent5'][0]:.1f} | (远5期): {road_info['means_far5'][0]:.1f} | 趋势: {road_info['trends'][0]}
                    - **1路均值(近5期)**: {road_info['means_recent5'][1]:.1f} | (远5期): {road_info['means_far5'][1]:.1f} | 趋势: {road_info['trends'][1]}
                    - **2路均值(近5期)**: {road_info['means_recent5'][2]:.1f} | (远5期): {road_info['means_far5'][2]:.1f} | 趋势: {road_info['trends'][2]}
                    - **本期预判**: <span style="color: #c62828; font-weight: bold;">0路{n0}个 | 1路{n1}个 | 2路{n2}个</span>
                    ''', unsafe_allow_html=True)
                else:
                    st.info('数据不足，无法进行012路预判')
            
            with col4:
                st.markdown('### 3.4 和值区间预判（辅助校验）')
                sum_range, sum_info = predict_sum_range(data)
                if sum_range:
                    st.markdown(f'''
                    - **上期和值**: {sum_info['last_sum']}
                    - **最大振幅**: {sum_info['amax']}
                    - **本期和值区间**: <span style="color: #c62828; font-weight: bold;">{sum_range[0]}-{sum_range[1]}</span>
                    ''', unsafe_allow_html=True)
                else:
                    st.info('数据不足，无法进行和值预判')
            
            st.divider()
            
            st.subheader('🗡️ 第二层：中观杀号层')
            
            if road_counts:
                final_kill, watch_list, kill_info = generate_final_kill_pool(data, road_counts, all_numbers)
                
                col_k1, col_k2 = st.columns(2)
                
                with col_k1:
                    st.markdown('### 4.1 第一重：分段位次杀号（彩侠核心方法）')
                    st.markdown('*权重分配：近5期0.5、近10期0.3、全周期0.2*')
                    st.markdown(f'**第一重杀号池（{len(kill_info["first_kill"])}个）:**')
                    st.markdown(' '.join(f'{n:02d}' for n in kill_info['first_kill']))
                
                with col_k2:
                    st.markdown('### 4.2 第二重：012路个数杀号（菲姐核心方法）')
                    st.markdown(f'**第二重杀号池（{len(kill_info["second_kill"])}个）:**')
                    st.markdown(' '.join(f'{n:02d}' for n in kill_info['second_kill']))
                
                follow_kill = []
                follow_pool_info = None
                
                if 'follow_pool_dict' in st.session_state and st.session_state.follow_pool_dict:
                    if target_period in st.session_state.follow_pool_dict:
                        follow_pool_info = st.session_state.follow_pool_dict[target_period]
                        follow_pool = follow_pool_info['unique_follow_nums']
                        source_period = follow_pool_info.get('source_period', selected_base_period)
                        
                        follow_kill = []
                        for num in follow_pool:
                            hotness = calculate_hotness(data, num, 10)
                            if hotness >= 5:
                                follow_kill.append(num)
                        
                        st.markdown('### 4.3 第三重：跟随号杀号（对接Tab 3）')
                        st.markdown(f'*期号对应：{source_period}期跟随 → {target_period}期（{len(follow_pool)}个）中热度≥5的号码*')
                        st.markdown(f'**第三重杀号池（{len(follow_kill)}个）:**')
                        st.markdown(' '.join(f'{n:02d}' for n in follow_kill))
                    else:
                        st.markdown('### 4.3 第三重：跟随号杀号（对接Tab 3）')
                        st.info(f'⚠️ 未找到{target_period}期的跟随号数据，请先在Tab 3中分析{selected_base_period}期数据')
                
                if follow_kill:
                    final_kill = sorted(list(set(final_kill) | set(follow_kill)))[:10]
                
                col_k3, col_k4 = st.columns(2)
                
                with col_k3:
                    st.markdown('### 4.4 最终杀号池')
                    st.markdown(f'''<div style="background-color: #ffebee; padding: 16px; border-radius: 8px;">
                    <h4 style="margin-top: 0; color: #c62828;">🎯 杀号（10个）</h4>
                    <p style="font-family: monospace; font-size: 18px; font-weight: bold;">{' '.join(f'{n:02d}' for n in final_kill)}</p>
                    </div>''', unsafe_allow_html=True)
                
                with col_k4:
                    st.markdown('### 待观察号')
                    st.markdown(f'''<div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px;">
                    <h4 style="margin-top: 0; color: #1565c0;">👀 待观察号（{len(watch_list)}个）</h4>
                    <p style="font-family: monospace; font-size: 16px;">{' '.join(f'{n:02d}' for n in watch_list)}</p>
                    <p style="font-size: 12px; color: #666;">选号时优先级最低</p>
                    </div>''', unsafe_allow_html=True)
                
                st.markdown('**容错机制**: 默认保留2个杀号容错，即允许10个杀号中开出2个')
                
                kill_data = {
                    'target_period': target_period,
                    'base_period': selected_base_period,
                    'final_kill': final_kill,
                    'watch_list': watch_list,
                    'first_kill': kill_info['first_kill'],
                    'second_kill': kill_info['second_kill'],
                    'follow_kill': follow_kill,
                    'save_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                os.makedirs('kill_data', exist_ok=True)
                kill_filename = f'kill_data/{target_period}杀号.json'
                with open(kill_filename, 'w', encoding='utf-8') as f:
                    json.dump(kill_data, f, ensure_ascii=False, indent=2)
                st.success(f'✅ 最终杀号池已自动保存到 {kill_filename}')
            else:
                st.info('请先完成第一层宏观边界预判')
            


# ==================== 【Tab 11】乐8三维融合预测体系 ====================
with tabs[10]:
    st.header('📚 乐8三维融合预测体系 V1.0')
    st.markdown('''
## 体系概述

本体系100%基于彩侠、菲姐、凡哥三位专家的经实战验证的核心优势构建，剔除各自短板模块，按「宏观定边界→中观杀垃圾→微观选核心」的三层递进逻辑形成完整闭环，所有规则量化可复现，无主观模糊判断。

---

## 一、体系核心设计理念与架构

### 1. 核心设计原则

- **优势互补原则**：仅保留三位专家准确率经复盘验证的模块，短板模块全部剔除，用其他专家的优势替代。
- **交叉验证原则**：所有核心结论（杀号、胆码）必须通过至少两种独立逻辑验证，单一方法结论不生效。
- **优先级递减原则**：宏观指标 > 杀号规则 > 选号结果，低层结论不得推翻高层边界。
- **风控兜底原则**：所有环节预留容错空间，避免极端走势出现大面积失误。

### 2. 整体三层架构

| 层级 | 核心作用 | 对应专家优势 | 输出结果 |
|------|----------|--------------|----------|
| 宏观边界层 | 锁定开奖整体框架，排除90%极端不可能组合 | 菲姐（跨度、012路个数）+ 凡哥（奇偶比） | 跨度区间、奇偶比区间、012路个数、和值区间 |
| 中观杀号层 | 批量排除低概率号码，将80码压缩至40码以内 | 彩侠（分段位次杀号）+ 菲姐（012路杀号） | 最终杀号10个、待观察号10个 |
| 微观选号层 | 梯度筛选核心号码，适配全场景投注 | 彩侠（梯度选号体系）+ 多专家重合度 | 独胆、双胆、5/10/15/17/20码分级大底 |

### 3. 适配场景

覆盖快乐8全玩法：选1至选10直选、复式投注、胆拖投注，兼顾小额高频与大额复式需求。

---

## 二、前置基础规范（统一标准，无标准不分析）

所有环节必须遵循以下统一定义，不得自行修改。

### 1. 基础定义

**号码范围：** 01-80，每期开出20个号码，按从小到大排序后分析。

**012路划分：**
- 0路：除以3余0（03、06、09…78），共27个
- 1路：除以3余1（01、04、07…79），共27个
- 2路：除以3余2（02、05、08…80），共26个

**位次分段标准（彩侠原版）：** 将从小到大排序的20个开奖号分为5段
- 1段：第1-4位，天然区间01-20
- 2段：第5-8位，天然区间10-40
- 3段：第9-12位，天然区间30-60
- 4段：第13-16位，天然区间40-70
- 5段：第17-20位，天然区间60-80

**冷热号定义：** 基于近10期出现次数
- 热号：出现≥5次
- 温号：出现3-4次
- 冷号：出现≤2次

**遗漏值：** 某号码距离上次开出的间隔期数。

### 2. 核心指标计算公式

- 跨度 = 当期最大开奖号 - 当期最小开奖号
- 和值 = 当期20个开奖号码之和
- 奇偶比 = 奇数个数：偶数个数
- 振幅 = |本期指标值 - 上期指标值|

### 3. 数据周期规范

| 分析环节 | 统计周期 | 权重分配 |
|----------|----------|----------|
| 跨度预判 | 近10期 | 近5期权重70%，远5期权重30% |
| 奇偶比预判 | 近7期 + 近3期 | 近3期权重60%，远4期权重40% |
| 012路个数预判 | 近10期 + 近5期 | 近5期权重60%，远5期权重40% |
| 分段杀号 | 近5期 + 近10期 + 全周期 | 近5期0.5、近10期0.3、全周期0.2 |
''')

# ==================== 【Tab 12】选号策略体系说明书 ====================
with tabs[11]:
    st.header('📋 选号策略体系说明书')
    st.markdown('''
## 第一层：宏观边界层（定全局框架）

**执行顺序：** 跨度预判 → 奇偶比预判 → 012路个数预判 → 和值区间校验

### 3.1 跨度预判（菲姐・振幅周期法，优先级最高）

**操作步骤：**
- 提取近10期跨度，计算9个相邻跨度振幅：`振幅n = |跨度n - 跨度n-1|`
- 判定当前振幅周期：
  - 收窄期：上期振幅 ≤ 3 → 本期跨度在上期基础上 ±2
  - 正常期：上期振幅 4-9 → 本期跨度在上期基础上 ±3
  - 放大期：上期振幅 ≥ 10 → 本期跨度在上期基础上 ±5
- 在计算出的跨度候选值中，选取近10期出现次数最多的作为主预判值，最终输出「主预判值 ±1」的区间。

**输出标准：** 明确给出本期跨度区间，如 75-77。

### 3.2 奇偶比预判（凡哥・冷热转换法）

**操作步骤：**
- 统计近7期奇数总个数S7、偶数总个数E7=140-S7，计算差值D7 = |S7-E7|
- 统计近3期奇数总个数S3、偶数总个数E3=60-S3，计算差值D3 = |S3-E3|

**逻辑判定：**
- 若D7 ≥ 5（某一方明显偏热）且D3 ≤ 3（近期回归均衡）→ 本期偏冷一方反弹，个数在均值10基础上 +1~+2
- 若D7 ≤ 4（整体均衡）→ 本期维持均衡，奇数个数9-11
- 若连续2期某一方个数≥12 → 本期该方回落至10个以内

**输出奇偶比区间，如 11-13:7-9。**

### 3.3 012路个数预判（菲姐・趋势均值法）

**操作步骤：**
- 计算近10期各路平均出号数：
  - 0路均值 = 近10期0路总数/10
  - 1路、2路同理
- 结合近5期趋势调整：近5期某路个数持续上升则+1，持续下降则-1
- 最终输出本期各路预判个数N0、N1、N2，三者之和必须等于20，误差允许±1。

### 3.4 和值区间预判（辅助校验项）

- 提取近5期和值，计算最大振幅Amax
- 本期和值区间 = 上期和值 ± (Amax × 0.6)
- 仅用于最终大底校验，不参与选号。

### 3.5 宏观指标一致性校验

**校验规则：** 跨度、奇偶比、012路个数三者逻辑自洽，例如跨度小则和值必然偏低，奇数多则1路+2路个数必然偏多。

**修正规则：** 若出现逻辑矛盾，优先修正012路个数，不得修改跨度。

---

## 第二层：中观杀号层（双重交叉验证）

**核心目标：** 杀号准确率≥90%，8个杀号错杀≤1个

### 4.1 第一重：分段位次杀号（彩侠核心方法）

**操作步骤：**
- 对5个分段分别计算综合均值M：
  - `M = 近5期均值×0.5 + 近10期均值×0.3 + 全周期均值×0.2`
- 对该分段对应区间内的所有号码，计算与综合均值M的偏离度：
  - `偏离度 = |号码 - M|`
- 每个分段杀掉偏离度最大的4个号码（最冷2个 + 最热2个）
- 汇总得到第一重候选杀号池，共20个号码。

### 4.2 第二重：012路个数杀号（菲姐核心方法）

**操作步骤：**
- 基于第一层预判的各路个数N0、N1、N2，对每一路号码按近10期出现次数从高到低排序。
- 每一路保留「预判个数 + 2」个最热号码，其余全部纳入候选杀号池。

**例：** 预判2路出4个 → 保留最热的6个2路号，其余20个2路号全部进入第二重杀号池

**汇总得到第二重候选杀号池，约60-65个号码。**

### 4.3 最终杀号池生成规则

**入选规则：** 只有同时出现在第一重、第二重杀号池的号码，才能进入最终杀号池。

**数量固定：** 最终杀号固定为8个；若交叉后不足8个，从第二重杀号池中补充最冷的号码补至8个。

**待观察号：** 仅在第一重杀号池、不在第二重的号码，标记为待观察号，共8个；不纳入杀号，但选号时优先级最低。

**容错机制：** 默认保留1个杀号容错，即允许8个杀号中开出1个。

---

## 第三层：微观选号层（梯度体系 + 重合度）

**核心逻辑：** 以重合度为核心，按梯度逐层扩容，全层级匹配宏观指标

### 5.1 核心号码池构建与重合度评分

**号码来源（仅保留三位专家高准确率模块）：**
- 菲姐来源：012路推荐中，各路排名前3的号码（0路准确率低，仅取前2个）
- 彩侠来源：分段推荐的核心号、独胆双胆三码中的所有号码
- 凡哥来源：2路号码推荐的前5个（0路、1路准确率低，全部剔除）；奇偶推荐对应的核心号

**重合度评分规则：**
- 同时出现在3个来源：3分（最高优先级）
- 同时出现在2个来源：2分（次高优先级）
- 仅出现在1个来源：1分（备选优先级）

### 5.2 梯度式号码池生成（彩侠梯度逻辑）

严格按重合度从高到低逐层扩容，每一层都必须通过宏观指标校验。

| 层级 | 号码数 | 规则 |
|------|--------|------|
| 独胆 | 1个 | 重合度最高 + 遗漏值3-7期的号码；若多个分数相同，选热度中等的温号 |
| 双胆 | 5组 | 独胆分别搭配5个次高重合度号码，每组2个 |
| 三码 | 4组 | 双胆分别搭配第三高重合度号码，每组3个 |
| 5码核心池 | 5个 | 独胆 + 重合度排名前4的号码 |
| 10码池 | 10个 | 5码池 + 重合度排名5-9的号码 |
| 15码池 | 15个 | 10码池 + 5个中等重合度温号 |
| 17码池 | 17个 | 15码池 + 2个待观察号（选最冷的2个） |
| 20码池 | 20个 | 17码池 + 3个高遗漏冷号（遗漏≥8期） |

### 5.3 全层级强制校验

每一层号码池生成后，必须满足：
1. 奇偶个数在第一层预判的区间内
2. 012路个数与第一层预判误差≤1
3. 最大号 - 最小号在第一层跨度区间内

**不满足则替换对应号码，直至符合要求。**
''')
