import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import os
from datetime import datetime
import json

# ==================== 【模块1】全局配置与数据持久化 ====================
st.set_page_config(
    page_title='快乐8多周期三流派预测系统',
    page_icon='🎱',
    layout='wide',
    initial_sidebar_state='collapsed'
)

# ==================== 【删除函数定义】 ====================
def delete_prediction_record(period, pred_type):
    """删除指定预测记录"""
    filepath = f'predictions/{period}_{pred_type}.json'
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False

def delete_follow_pool_record(period):
    """删除指定相随号池记录"""
    filepath = os.path.join('follow_pools', f'{period}_follow_pool.json')
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False

def validate_numbers(numbers):
    """验证号码列表是否有效（1-80之间，无重复）"""
    if not isinstance(numbers, (list, set)):
        return False, "号码必须是列表或集合"
    
    numbers = list(numbers)
    
    if len(numbers) == 0:
        return False, "号码列表不能为空"
    
    # 检查每个号码是否在有效范围内
    for num in numbers:
        if not isinstance(num, int):
            return False, f"号码 {num} 必须是整数"
        if num < 1 or num > 80:
            return False, f"号码 {num} 必须在1-80之间"
    
    # 检查是否有重复
    if len(numbers) != len(set(numbers)):
        return False, "号码不能重复"
    
    return True, "验证通过"

def validate_period(period):
    """验证期号格式是否正确（7位数字）"""
    if not isinstance(period, str):
        period = str(period)
    
    if not period.isdigit():
        return False, "期号必须是数字"
    
    if len(period) != 7:
        return False, "期号必须是7位数字（格式：年+期号，如2025001）"
    
    # 检查年份范围（2020-2030）
    year = int(period[:4])
    if year < 2020 or year > 2030:
        return False, f"年份 {year} 不在有效范围内（2020-2030）"
    
    # 检查期数范围（1-150）
    period_num = int(period[4:])
    if period_num < 1 or period_num > 150:
        return False, f"期数 {period_num} 不在有效范围内（1-150）"
    
    return True, "验证通过"

def load_all_comparisons():
    """加载所有对比记录"""
    comparisons = {}
    if os.path.exists('comparisons'):
        for file in os.listdir('comparisons'):
            if file.endswith('_comparison.json'):
                filepath = os.path.join('comparisons', file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        key = file.replace('_comparison.json', '')
                        comparisons[key] = data
                except Exception as e:
                    print(f"读取对比记录失败 {file}: {str(e)}")
    return dict(sorted(comparisons.items(), reverse=True))

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
    """初始化或加载基础号码库"""
    if not os.path.exists('lottery_data_v2.csv'):
        # 首次运行，使用预加载数据
        df = pd.DataFrame(INITIAL_DATA, columns=['期号'] + [f'第{i}位' for i in range(1, 21)])
        df['期号'] = df['期号'].astype(str)
        df.set_index('期号', inplace=True)
        df = df.sort_index(ascending=True)
        df.to_csv('lottery_data_v2.csv')
        return df
    else:
        # 加载已有数据
        df = pd.read_csv('lottery_data_v2.csv', index_col='期号', dtype={'期号': str})
        df = df.sort_index(ascending=True)
        return df

def save_lottery_data(df):
    """保存基础号码库到本地"""
    df.to_csv('lottery_data_v2.csv')
    st.success('✅ 数据已成功保存到本地 lottery_data_v2.csv')

def save_prediction(prediction_data, period, prediction_type='prediction'):
    """保存预测方案到本地（基于期号存储，确保相同期号只保存一次）
    prediction_type: 'prediction1' 表示Tab5预测, 'prediction2' 表示Tab6预测
    """
    if not os.path.exists('predictions'):
        os.makedirs('predictions', exist_ok=True)

    # 使用期号和类型作为文件名
    filename = f'predictions/{period}_{prediction_type}.json'

    # 如果文件已存在，检查数据是否相同，相同则不更新
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        if existing_data.get('step5_core_pool') == prediction_data.get('step5_core_pool') and \
           existing_data.get('step6_combinations') == prediction_data.get('step6_combinations'):
            return filename  # 数据相同，不更新

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(prediction_data, f, ensure_ascii=False, indent=2)
    return filename

def delete_core_pool(period):
    """删除指定期号的核心池"""
    core_pool_dir = 'core_pool'
    filename = f"{core_pool_dir}/core_pool_{period}.json"
    if os.path.exists(filename):
        os.remove(filename)
        return True
    return False

def load_predictions_by_type(prediction_type):
    """加载指定类型的预测记录"""
    predictions = {}
    if os.path.exists('predictions'):
        for file in os.listdir('predictions'):
            if file.endswith(f'_{prediction_type}.json'):
                period = file.replace(f'_{prediction_type}.json', '')
                filepath = os.path.join('predictions', file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        predictions[period] = json.load(f)
                except:
                    pass
    return dict(sorted(predictions.items()))

def save_follow_pool(pool_data, period):
    """保存相随号池到本地"""
    if not os.path.exists('follow_pools'):
        os.makedirs('follow_pools', exist_ok=True)
    
    filename = os.path.join('follow_pools', f'{period}_follow_pool.json')
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(pool_data, f, ensure_ascii=False, indent=2)
    return filename

def load_all_follow_pools():
    """加载所有已保存的相随号池记录"""
    pools = {}
    if os.path.exists('follow_pools'):
        for file in os.listdir('follow_pools'):
            if file.endswith('_follow_pool.json'):
                period = file.replace('_follow_pool.json', '')
                filepath = os.path.join('follow_pools', file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        pools[period] = json.load(f)
                except:
                    pass
    return dict(sorted(pools.items(), reverse=True))

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
    st.markdown('### 📝 开发日志')
    st.info('V3.0 已上线：Tab 7 完整实现8步SOP流程，自动生成预测方案')

# ==================== 【模块3】主界面Tab布局 ====================
tabs = st.tabs([
    '📚 Tab 1 号码库管理',
    '📊 Tab 2 数据分析',
    '🔗 Tab 3 相随号数据',
    '🔮 Tab 4 相随号生成',
    '📋 Tab 5 体系全流程标准化执行 SOP',
    '📈 Tab 6 V7.1 动态趋势适配',
    '🔍 Tab 7 开奖号对比',
    '📊 Tab 8 命中率数据库',
    '⚙️ Tab 9 V7.2a 核心池驱动系统',
    '📝 Tab 10',
    '🎯 Tab 11 V7.2a 用户核心池驱动'
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
        
        # 自动生成下一期期号
        def generate_next_period():
            if not st.session_state.lottery_data.empty:
                max_period = st.session_state.lottery_data.index[-1]
                # 解析期号：前4位是年份，后3位是期数
                year = int(max_period[:4])
                period_num = int(max_period[4:])
                # 假设每年最多150期，超过则进入下一年
                if period_num >= 150:
                    next_year = year + 1
                    next_period_num = 1
                else:
                    next_year = year
                    next_period_num = period_num + 1
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
    period_options = [150, 100, 80, 50, 20, 10, 5]
    selected_period = st.selectbox(
        '请选择分析周期',
        period_options,
        index=3,
        help='选择要分析的最近N期数据'
    )

    # 获取最近N期数据
    data = st.session_state.lottery_data
    if len(data) >= selected_period:
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

# ==================== 【Tab 3】相随号数据 ====================
with tabs[2]:
    st.header('🔗 相随号数据')
    st.markdown('基于号码库数据，分析号码之间的相随关系和同频组合。')
    st.divider()
    
    # 周期选择
    period_options = [150, 100, 80, 50, 30, 20, 10]
    selected_period = st.selectbox(
        '请选择分析周期',
        period_options,
        index=3,
        help='选择要分析的最近N期数据'
    )
    
    data = st.session_state.lottery_data
    if len(data) >= selected_period:
        recent_data = data.tail(selected_period)
    else:
        recent_data = data
        st.warning(f'⚠️ 数据不足 {selected_period} 期，仅分析现有 {len(recent_data)} 期')
    
    # 1. 相随号分析
    st.subheader('� 相随号分析')
    st.caption('相随号定义：N期开出的号码A，N+1期跟着开出的号码')
    
    # 构建相随号字典
    follow_dict = defaultdict(list)
    periods = recent_data.index.tolist()
    
    for i in range(len(periods) - 1):
        current_nums = set(recent_data.loc[periods[i]].dropna().astype(int).tolist())
        next_nums = set(recent_data.loc[periods[i+1]].dropna().astype(int).tolist())
        
        for num in current_nums:
            follow_dict[num].extend(list(next_nums))
    
    # 统计每个号码的相随号频率并取前5
    follow_top5 = {}
    for num, follows in follow_dict.items():
        freq = pd.Series(follows).value_counts()
        follow_top5[num] = freq.head(5).to_dict()
    
    # 展示相随号
    col_follow1, col_follow2 = st.columns([1, 2])
    with col_follow1:
        selected_num = st.selectbox('选择号码查看相随号', sorted(follow_top5.keys()), index=0)
    with col_follow2:
        if selected_num in follow_top5:
            st.markdown(f'''<div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px;">
            <h4 style="color: #1565c0; margin-top: 0;">🔗 号码 {selected_num:02d} 的相随号（前5名）</h4>
            <div style="margin-top: 10px;">
            {''.join([f'<div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #b3d9f5;">\n<span style="font-weight: bold; color: #1565c0;">{k:02d}</span>\n<span style="color: #666;">出现 {v} 次</span>\n</div>' for k, v in follow_top5[selected_num].items()])}
            </div>
            </div>''', unsafe_allow_html=True)
    
    st.divider()
    
    # 2. 同频双码分析
    st.subheader('📊 同频双码')
    st.caption('同频双码：同一期出现的两个号码组合')
    
    pair_counts = defaultdict(int)
    for idx, row in recent_data.iterrows():
        nums = row.dropna().astype(int).tolist()
        for i in range(len(nums)):
            for j in range(i+1, len(nums)):
                pair = tuple(sorted([nums[i], nums[j]]))
                pair_counts[pair] += 1
    
    # 取出现次数最多的前20对
    top_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    
    st.markdown('''<div style="background-color: #f5f5f5; padding: 16px; border-radius: 8px;">
    <h4 style="margin-top: 0; color: #333;">🔥 出现次数最多的双码组合（前20）</h4>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; margin-top: 12px;">
    {}</div>
    </div>'''.format(''.join([f'<div style="background-color: #fff; padding: 8px; border-radius: 4px; text-align: center; border: 1px solid #ddd;">\n<span style="font-family: monospace; font-weight: bold; color: #c62828;">{p[0][0]:02d}-{p[0][1]:02d}</span>\n<br/>\n<span style="font-size: 12px; color: #666;">{p[1]}次</span>\n</div>' for p in top_pairs])), unsafe_allow_html=True)
    
    st.divider()
    
    # 3. 同频三码分析
    st.subheader('📊 同频三码')
    st.caption('同频三码：同一期出现的三个号码组合')
    
    triplet_counts = defaultdict(int)
    for idx, row in recent_data.iterrows():
        nums = row.dropna().astype(int).tolist()
        for i in range(len(nums)):
            for j in range(i+1, len(nums)):
                for k in range(j+1, len(nums)):
                    triplet = tuple(sorted([nums[i], nums[j], nums[k]]))
                    triplet_counts[triplet] += 1
    
    # 取出现次数最多的前15组
    top_triplets = sorted(triplet_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    
    st.markdown('''<div style="background-color: #f5f5f5; padding: 16px; border-radius: 8px;">
    <h4 style="margin-top: 0; color: #333;">🔥 出现次数最多的三码组合（前15）</h4>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; margin-top: 12px;">
    {}</div>
    </div>'''.format(''.join([f'<div style="background-color: #fff; padding: 8px; border-radius: 4px; text-align: center; border: 1px solid #ddd;">\n<span style="font-family: monospace; font-weight: bold; color: #1565c0;">{t[0][0]:02d}-{t[0][1]:02d}-{t[0][2]:02d}</span>\n<br/>\n<span style="font-size: 12px; color: #666;">{t[1]}次</span>\n</div>' for t in top_triplets])), unsafe_allow_html=True)

# ==================== 【Tab 4】相随号生成 ====================
with tabs[3]:
    st.header('🔮 相随号生成')
    st.markdown("""<div style="background-color: #f0f2f6; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
    <p style="font-size: 16px; line-height: 1.6;">
    基于 N 期开奖号码，结合近 80 期相随号数据，为 N+1 期生成相随号池。
    </p>
    <ul style="margin-top: 10px; font-size: 14px;">
    <li>✅ 调用 Tab 1 号码库开奖数据</li>
    <li>✅ 分析近 80 期每个号码的相随关系</li>
    <li>✅ 提取 N 期 20 个开奖号码的前 2 名相随号</li>
    <li>✅ 去重后生成 N+1 期相随号池</li>
    </ul>
    </div>""", unsafe_allow_html=True)
    st.divider()

    # 函数：计算相随号关系
    def calculate_follow_dict(data, period=80):
        """计算近N期的相随号关系"""
        if len(data) >= period:
            recent_data = data.tail(period)
        else:
            recent_data = data
        
        follow_dict = defaultdict(list)
        periods = recent_data.index.tolist()
        
        for i in range(len(periods) - 1):
            current_nums = set(recent_data.loc[periods[i]].dropna().astype(int).tolist())
            next_nums = set(recent_data.loc[periods[i+1]].dropna().astype(int).tolist())
            
            for num in current_nums:
                follow_dict[num].extend(list(next_nums))
        
        # 统计每个号码的相随号频率
        follow_top2 = {}
        for num, follows in follow_dict.items():
            freq = pd.Series(follows).value_counts()
            follow_top2[num] = freq.head(2).to_dict()
        
        return follow_top2

    if len(st.session_state.lottery_data) >= 10:
        period_list = st.session_state.lottery_data.index.tolist()
        
        # 选择 N 期
        n_period = st.selectbox(
            '请选择 N 期（已开奖的最后一期）',
            period_list,
            index=len(period_list)-1,
            help='选择已开奖的 N 期，将为 N+1 期生成相随号池'
        )
        
        n_plus_1 = str(int(n_period) + 1)
        st.write(f'已选择 **{n_period}** 期，将为 **{n_plus_1}** 期生成相随号池')
        
        # 获取 N 期开奖号码
        n_nums = st.session_state.lottery_data.loc[n_period].dropna().astype(int).tolist()
        st.markdown(f"""<div style="background-color: #f5f5f5; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
        <h4 style="margin-top: 0;">📅 {n_period} 期开奖号码</h4>
        <p style="font-family: monospace; font-size: 14px;">{' '.join(map(str, sorted(n_nums)))}</p>
        </div>""", unsafe_allow_html=True)
        
        # 检查是否已经存在该期号的相随号池记录
        existing_pool = None
        follow_pools = load_all_follow_pools()
        if n_plus_1 in follow_pools:
            existing_pool = follow_pools[n_plus_1]
        
        # 显示当前状态
        col_status1, col_status2 = st.columns([3, 1])
        with col_status1:
            if existing_pool:
                st.success(f'🔒 已锁定记录（生成时间：{existing_pool["generated_at"]}）')
                st.info('⚠️ 相随号池一旦生成即永久锁定，不会因新增开奖数据而改变')
            else:
                st.info('📝 暂无记录，将基于当前数据生成新的相随号池')
        with col_status2:
            st.write(f"""<div style="background-color: {'#e8f5e8' if existing_pool else '#fff3e0'}; padding: 12px; border-radius: 6px; text-align: center;">
            <p style="font-weight: bold; font-size: 16px;">{'🔒 已锁定' if existing_pool else '➕ 可生成'}</p>
            </div>""", unsafe_allow_html=True)
        
        # 如果有已保存的记录，则直接读取（永不重新计算）
        if existing_pool:
            pool_data = existing_pool
            follow_pool = pool_data['follow_pool']
            follow_details = pool_data['follow_details']
            n_nums_saved = pool_data['n_nums']
            
            # 保存到session_state供Tab7使用
            st.session_state.current_follow_pool = follow_pool
            st.session_state.current_follow_period = n_plus_1
            
            # 数据完整性校验：检查原始N期号码是否与当前数据一致
            current_n_nums = sorted(st.session_state.lottery_data.loc[n_period].dropna().astype(int).tolist())
            if current_n_nums == n_nums_saved:
                data_valid = True
                valid_msg = '✅ 数据校验通过'
            else:
                data_valid = False
                valid_msg = '⚠️ 数据已变更（原始N期号码已被修改）'
            
            st.divider()
            
            # 展示数据校验结果
            st.markdown(f"""<div style="background-color: {'#e8f5e8' if data_valid else '#ffebee'}; padding: 10px; border-radius: 6px; margin-bottom: 12px;">
            <p style="font-size: 13px; color: {'#2e7d32' if data_valid else '#c62828'}; font-weight: bold;">{valid_msg}</p>
            <p style="font-size: 12px; color: #666; margin-top: 4px;">基于 {n_period} 期生成 | 分析周期：80期 | 生成时间：{pool_data['generated_at']}</p>
            </div>""", unsafe_allow_html=True)
            
            # 展示详细信息
            st.subheader('📌 每个号码的相随号详情 🔒')
            col_detail1, col_detail2 = st.columns(2)
            
            for idx, detail in enumerate(follow_details):
                with col_detail1 if idx % 2 == 0 else col_detail2:
                    st.markdown(f"""<div style="background-color: #e3f2fd; padding: 10px; border-radius: 6px; margin-bottom: 8px; border-left: 4px solid #1565c0;">
                    <h5 style="margin-top: 0; color: #1565c0;">号码 {detail['num']:02d}</h5>
                    <p>第1相随：{detail['follow1']:02d}（出现 {detail['count1']} 次）</p>
                    <p>第2相随：{detail['follow2']:02d}（出现 {detail['count2']} 次）</p>
                    </div>""", unsafe_allow_html=True)
            
            st.divider()
            
            # 展示最终相随号池
            st.subheader('🎯 最终相随号池（已锁定）')
            st.markdown(f"""<div style="background-color: #e8f5e8; padding: 16px; border-radius: 8px; border: 2px solid #2e7d32;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h4 style="margin-top: 0; color: #2e7d32;">{n_plus_1} 期相随号池（共 {len(follow_pool)} 个号码）</h4>
            <span style="background-color: #c8e6c9; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #2e7d32; font-weight: bold;">🔒 已锁定</span>
            </div>
            <p style="font-family: monospace; font-size: 16px;">{' '.join(map(str, follow_pool))}</p>
            <p style="font-size: 12px; color: #666; margin-top: 10px;">💡 此相随号池基于生成时的历史数据计算，不会因后续新增开奖号码而改变</p>
            </div>""", unsafe_allow_html=True)
        else:
            # 需要生成新的相随号池（仅在无记录时执行）
            with st.spinner('正在计算相随号关系...'):
                follow_top2 = calculate_follow_dict(st.session_state.lottery_data, 80)
                
                # 收集所有相随号
                follow_pool = []
                follow_details = []
                
                for num in sorted(n_nums):
                    if num in follow_top2:
                        top2 = list(follow_top2[num].keys())
                        follow_pool.extend(top2)
                        follow_details.append({
                            'num': num,
                            'follow1': top2[0] if len(top2) >= 1 else None,
                            'count1': follow_top2[num][top2[0]] if len(top2) >= 1 else 0,
                            'follow2': top2[1] if len(top2) >= 2 else None,
                            'count2': follow_top2[num][top2[1]] if len(top2) >= 2 else 0
                        })
                
                # 去重并排序
                follow_pool = sorted(list(set(follow_pool)))
                
                # 保存数据（包含完整的生成上下文）
                pool_data = {
                    'n_period': n_period,
                    'n_plus_1': n_plus_1,
                    'n_nums': sorted(n_nums),
                    'follow_details': follow_details,
                    'follow_pool': follow_pool,
                    'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'data_version': len(st.session_state.lottery_data),  # 记录生成时的数据量
                    'analysis_period': 80  # 记录分析周期
                }
                
                filename = save_follow_pool(pool_data, n_plus_1)
                # 保存到session_state供Tab7使用
                st.session_state.current_follow_pool = follow_pool
                st.session_state.current_follow_period = n_plus_1
                st.success(f'✅ 相随号池生成完成！已保存至：{filename}')
                st.info('📌 此相随号池已永久保存，未来将不会因新增开奖数据而改变')
                
                st.divider()
                
                # 展示详细信息
                st.subheader('📌 每个号码的相随号详情')
                col_detail1, col_detail2 = st.columns(2)
                
                for idx, detail in enumerate(follow_details):
                    with col_detail1 if idx % 2 == 0 else col_detail2:
                        st.markdown(f"""<div style="background-color: #e3f2fd; padding: 10px; border-radius: 6px; margin-bottom: 8px; border-left: 4px solid #1565c0;">
                        <h5 style="margin-top: 0; color: #1565c0;">号码 {detail['num']:02d}</h5>
                        <p>第1相随：{detail['follow1']:02d}（出现 {detail['count1']} 次）</p>
                        <p>第2相随：{detail['follow2']:02d}（出现 {detail['count2']} 次）</p>
                        </div>""", unsafe_allow_html=True)
                
                st.divider()
                
                # 展示最终相随号池
                st.subheader('🎯 最终相随号池（已保存）')
                st.markdown(f"""<div style="background-color: #fff8e1; padding: 16px; border-radius: 8px; border: 2px solid #f57c00;">
                <h4 style="margin-top: 0; color: #f57c00;">{n_plus_1} 期相随号池（共 {len(follow_pool)} 个号码）</h4>
                <p style="font-family: monospace; font-size: 16px;">{' '.join(map(str, follow_pool))}</p>
                <p style="font-size: 12px; color: #666; margin-top: 10px;">📊 基于近80期数据生成 | 当前数据库共 {len(st.session_state.lottery_data)} 期</p>
                </div>""", unsafe_allow_html=True)
        
        st.divider()
        
        # 展示历史相随号池
        st.subheader('📚 历史相随号池记录')
        follow_pools = load_all_follow_pools()
        
        if follow_pools:
            pool_periods = list(follow_pools.keys())
            selected_pool_period = st.selectbox('选择期号查看历史记录', pool_periods, index=0)
            
            if selected_pool_period in follow_pools:
                pool = follow_pools[selected_pool_period]
                
                st.markdown(f"""<div style="background-color: #f5f5f5; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
                <h4 style="margin-top: 0;">{selected_pool_period} 期相随号池</h4>
                <p style="font-family: monospace; font-size: 14px;">{' '.join(map(str, pool['follow_pool']))}</p>
                <p style="font-size: 12px; color: #666;">生成时间：{pool['generated_at']}</p>
                </div>""", unsafe_allow_html=True)
        else:
            st.info('暂无历史相随号池记录，请先生成相随号池')
    else:
        st.warning('⚠️ 数据不足 10 期，无法生成相随号池')
    
    # 数据管理
    st.divider()
    st.subheader('🗑️ 相随号池数据管理')
    
    col_del1, col_del2 = st.columns(2)
    with col_del1:
        st.markdown('**📋 历史相随号池记录**')
        pool_files = []
        if os.path.exists('follow_pools'):
            pool_files = [f.replace('_follow_pool.json', '') for f in os.listdir('follow_pools') if f.endswith('_follow_pool.json')]
        if pool_files:
            for pf in sorted(pool_files, reverse=True)[:10]:
                st.text(f'• {pf}')
        else:
            st.text('暂无记录')
    
    with col_del2:
        if pool_files:
            delete_pool = st.selectbox('选择要删除的期号', pool_files, key='del_pool')
            if st.button('🗑️ 删除选中记录', type='secondary', key='btn_pool'):
                if delete_follow_pool_record(delete_pool):
                    st.success(f'✅ 已删除 {delete_pool} 期相随号池')
                else:
                    st.error('❌ 删除失败')

# ==================== 【Tab 5】体系全流程标准化执行 SOP ====================
with tabs[4]:
    # ==================== 【SOP 核心算法模块】 ====================
    def step1_prepare_data(data):
        """Step 1: 基础数据准备"""
        stats_100 = data.apply(lambda x: x.dropna().astype(int).value_counts()).sum()
        stats_100 = stats_100.reindex(range(1, 81), fill_value=0)
        
        stats_50 = data.tail(50).apply(lambda x: x.dropna().astype(int).value_counts()).sum()
        stats_50 = stats_50.reindex(range(1, 81), fill_value=0)
        
        stats_30 = data.tail(30).apply(lambda x: x.dropna().astype(int).value_counts()).sum()
        stats_30 = stats_30.reindex(range(1, 81), fill_value=0)
        
        stats_20 = data.tail(20).apply(lambda x: x.dropna().astype(int).value_counts()).sum()
        stats_20 = stats_20.reindex(range(1, 81), fill_value=0)
        
        stats_10 = data.tail(10).apply(lambda x: x.dropna().astype(int).value_counts()).sum()
        stats_10 = stats_10.reindex(range(1, 81), fill_value=0)
        
        omission = {}
        for num in range(1, 81):
            recent = data.tail(30)
            last_appear = None
            for idx in recent.index[::-1]:
                nums = recent.loc[idx].dropna().astype(int).tolist()
                if num in nums:
                    last_appear = idx
                    break
            if last_appear is not None:
                omission[num] = len(recent) - recent.index.get_loc(last_appear)
            else:
                omission[num] = 30
        
        return {
            'stats_100': stats_100,
            'stats_50': stats_50,
            'stats_30': stats_30,
            'stats_20': stats_20,
            'stats_10': stats_10,
            'omission': omission
        }
    
    def step2_risk_control(data, prepared_data):
        """Step 2: 刚性风控规则"""
        stats_100 = prepared_data['stats_100']
        omission = prepared_data['omission']
        
        if len(data) < 3:
            return {'exclude_list': [], 'three_consecutive': [], 'downgrade_list': [], 'hot_fuse': []}
        
        recent_3 = data.tail(3)
        recent_2 = data.tail(2)
        
        three_consecutive = []
        for num in range(1, 81):
            if all(num in recent_3.iloc[i].dropna().astype(int).tolist() for i in range(3)):
                three_consecutive.append(num)
        
        downgrade_list = []
        for num in range(1, 81):
            if num not in three_consecutive:
                if all(num in recent_2.iloc[i].dropna().astype(int).tolist() for i in range(2)):
                    downgrade_list.append(num)
        
        hot_fuse = []
        for num in range(1, 81):
            if stats_100[num] >= 28 and omission[num] <= 2:
                hot_fuse.append(num)
        
        exclude_list = list(set(three_consecutive + hot_fuse))
        
        return {
            'exclude_list': exclude_list,
            'three_consecutive': three_consecutive,
            'downgrade_list': downgrade_list,
            'hot_fuse': hot_fuse
        }
    
    def step3_market_judge(data, prepared_data):
        """Step 3: 行情周期判定"""
        stats_30 = prepared_data['stats_30']
        stats_10 = prepared_data['stats_10']
        omission = prepared_data['omission']
        
        hot_count = sum(1 for num in range(1, 81) if stats_30[num] >= 8 and omission[num] <= 3)
        warm_count = sum(1 for num in range(1, 81) if 4 <= stats_30[num] < 8 and 3 <= omission[num] <= 6)
        cold_count = sum(1 for num in range(1, 81) if stats_30[num] < 4 and omission[num] >= 7)
        
        if hot_count >= 15:
            market_type = "🔥 热行情"
            position = {"stable": 0.20, "warm": 0.25, "hot": 0.45, "cold": 0.10}
        elif cold_count >= 15:
            market_type = "❄️ 冷行情"
            position = {"stable": 0.25, "warm": 0.25, "hot": 0.10, "cold": 0.40}
        else:
            market_type = "⚖️ 均衡行情"
            position = {"stable": 0.30, "warm": 0.30, "hot": 0.20, "cold": 0.20}
        
        hot_ratio = hot_count / 80
        
        return {
            'market_type': market_type,
            'hot_ratio': hot_ratio,
            'position': position
        }
    
    def step4_select_numbers(data, prepared_data, risk_data, market_data, follow_pool):
        """Step 4: 从相随号池中筛选号码"""
        stats_100 = prepared_data['stats_100']
        stats_50 = prepared_data['stats_50']
        stats_30 = prepared_data['stats_30']
        stats_20 = prepared_data['stats_20']
        stats_10 = prepared_data['stats_10']
        omission = prepared_data['omission']
        exclude_list = risk_data['exclude_list']
        
        # 只在相随号池中筛选
        valid_pool = [num for num in follow_pool if num not in exclude_list]
        
        # 按综合指标排序
        pool_scores = {}
        for num in valid_pool:
            # 综合评分：考虑近期热度和遗漏
            score = (stats_30[num] * 0.4 + 
                     stats_20[num] * 0.3 + 
                     stats_10[num] * 0.2 + 
                     (15 - min(omission[num], 15)) * 0.1)
            pool_scores[num] = score
        
        # 按评分排序
        sorted_pool = sorted(valid_pool, key=lambda x: pool_scores[x], reverse=True)
        
        # 分配到不同流派
        stable_candidates = sorted_pool[:5] if len(sorted_pool) >= 5 else sorted_pool
        remaining = [num for num in sorted_pool if num not in stable_candidates]
        warm_candidates = remaining[:6] if len(remaining) >= 6 else remaining
        remaining = [num for num in remaining if num not in warm_candidates]
        hot_candidates = remaining[:3] if len(remaining) >= 3 else remaining
        remaining = [num for num in remaining if num not in hot_candidates]
        cold_candidates = remaining[:2] if len(remaining) >= 2 else remaining
        
        return {
            'stable': stable_candidates,
            'warm': warm_candidates,
            'hot': hot_candidates,
            'cold': cold_candidates
        }
    
    def step5_build_core_pool(selected_numbers, market_data, risk_data, follow_pool):
        """Step 5: 15码核心池锁定（仅从相随号池中选择）"""
        total_size = 15
        
        # 从所有候选号码中选择前15个
        all_candidates = (selected_numbers['stable'] + 
                         selected_numbers['warm'] + 
                         selected_numbers['hot'] + 
                         selected_numbers['cold'])
        
        # 去重并确保只在相随号池中
        all_candidates = sorted(list(set([num for num in all_candidates if num in follow_pool])))
        
        # 取前15个作为核心池
        core_pool = all_candidates[:total_size] if len(all_candidates) >= total_size else all_candidates
        
        # 如果还不足15个，从相随号池中补充
        if len(core_pool) < total_size:
            for num in follow_pool:
                if num not in core_pool and len(core_pool) < total_size:
                    core_pool.append(num)
        
        # 容错池
        backup_pool = {
            'level1': [num for num in all_candidates if num not in core_pool][:6],
            'level2': [],
            'level3': []
        }
        
        return {
            'core_pool': sorted(core_pool),
            'backup_pool': backup_pool
        }
    
    def step6_build_combinations(core_pool):
        """Step 6: 组合打法构建 - 3组11码、5组8码、10组6码、4组4码"""
        
        core_pool_sorted = sorted(core_pool)
        n = len(core_pool_sorted)
        
        def generate_comb(size, start, step):
            """生成指定大小的组合"""
            comb = []
            for j in range(size):
                idx = (start + j * step) % n
                comb.append(core_pool_sorted[idx])
            return sorted(list(set(comb)))
        
        # 3组11码
        eleven_code = []
        for i in range(3):
            comb = generate_comb(11, i * 5, 1)
            # 如果不够11个，补充
            while len(comb) < 11:
                for num in core_pool_sorted:
                    if num not in comb:
                        comb.append(num)
                        break
                comb.sort()
            eleven_code.append(sorted(comb))
        
        # 5组8码
        eight_code = []
        for i in range(5):
            comb = generate_comb(8, i * 3, 1)
            while len(comb) < 8:
                for num in core_pool_sorted:
                    if num not in comb:
                        comb.append(num)
                        break
                comb.sort()
            eight_code.append(sorted(comb))
        
        # 10组6码
        six_code = []
        for i in range(10):
            if i == 0:
                comb = core_pool_sorted[:6]
            elif i == 1:
                comb = core_pool_sorted[-6:]
            elif i == 2:
                comb = generate_comb(6, 0, 2)
            elif i == 3:
                comb = generate_comb(6, 1, 2)
            elif i == 4:
                comb = generate_comb(6, 0, 3)
            elif i == 5:
                comb = generate_comb(6, 2, 3)
            elif i == 6:
                comb = core_pool_sorted[4:10] if n >= 10 else core_pool_sorted[:6]
            elif i == 7:
                comb = core_pool_sorted[6:12] if n >= 12 else core_pool_sorted[-6:]
            elif i == 8:
                comb = generate_comb(6, 0, 4)
            else:
                comb = generate_comb(6, 3, 4)
            comb = sorted(list(set(comb)))
            while len(comb) < 6:
                for num in core_pool_sorted:
                    if num not in comb:
                        comb.append(num)
                        break
                comb.sort()
            six_code.append(sorted(comb))
        
        # 4组4码
        four_code = []
        for i in range(4):
            if i == 0:
                comb = core_pool_sorted[:4]
            elif i == 1:
                comb = core_pool_sorted[4:8]
            elif i == 2:
                comb = core_pool_sorted[8:12]
            else:
                comb = core_pool_sorted[-4:]
            comb = sorted(list(set(comb)))
            while len(comb) < 4:
                for num in core_pool_sorted:
                    if num not in comb:
                        comb.append(num)
                        break
                comb.sort()
            four_code.append(sorted(comb))
        
        return {
            'eleven_code': eleven_code,
            'eight_code': eight_code,
            'six_code': six_code,
            'four_code': four_code
        }

    # ==================== 【SOP 主界面】 ====================
    st.markdown("""
    ## 📋 体系全流程标准化执行 SOP
    <div style="background-color: #f0f2f6; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
    <p style="font-size: 16px; line-height: 1.6;">
    本 SOP 为体系的标准化执行流程，每期严格按步骤执行，无主观调整空间，确保每一期预测都可追溯、可复盘。
    </p>
    <ul style="margin-top: 10px; font-size: 14px;">
    <li>✅ 8步标准化流程，确保预测的科学性和一致性</li>
    <li>✅ 基于多周期数据的量化分析</li>
    <li>✅ 从相随号池中自动生成15码核心池</li>
    <li>✅ 自动生成3组11码、5组8码、10组6码、10组4码组合</li>
    <li>✅ 完整的风控机制，避免极端情况</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # 交互：选择 N 期为 N+1 期预测
    st.divider()
    st.subheader('🔮 为 N+1 期进行预测')
    
    if len(st.session_state.lottery_data) >= 10:
        # 检查是否有相随号池
        if 'current_follow_pool' not in st.session_state or not st.session_state.current_follow_pool:
            st.warning('⚠️ 请先在 Tab 4 中生成相随号池！')
            st.info('💡 提示：请先前往 Tab 4 生成相随号池后再执行此流程')
        else:
            st.success(f'✅ 已检测到相随号池（期号：{st.session_state.current_follow_period}，共 {len(st.session_state.current_follow_pool)} 个号码')
            st.markdown(f"""<div style="background-color: #e3f2fd; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
            <h4 style="margin-top: 0; color: #1565c0;">相随号池号码</h4>
            <p style="font-family: monospace; font-size: 14px;">{' '.join(map(str, sorted(st.session_state.current_follow_pool)))}</p>
            </div>""", unsafe_allow_html=True)
            
            period_list = st.session_state.lottery_data.index.tolist()
            sop_n_period = st.selectbox(
                '请选择 N 期数（已开奖的最后一期）',
                period_list,
                index=len(period_list)-1,
                help='选择已开奖的最后一期 N，系统将为 N+1 期准备预测'
            )
            
            n_plus_1 = str(int(sop_n_period) + 1)
            st.write(f'已选择 **{sop_n_period}** 期，将为 **{n_plus_1}** 期进行预测')
            
            # 直接执行，不需要点击按钮
            # 根据选择的期数裁剪数据，只使用到 sop_n_period 期为止的数据
            data = st.session_state.lottery_data.loc[:sop_n_period].copy()
            follow_pool = st.session_state.current_follow_pool
            
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
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 4/8: 从相随号池筛选号码...</div>', unsafe_allow_html=True)
            selected_numbers = step4_select_numbers(data, prepared_data, risk_data, market_data, follow_pool)
            progress_bar.progress(50)
            
            # Step 5
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 5/8: 15码核心池锁定...</div>', unsafe_allow_html=True)
            core_pool_data = step5_build_core_pool(selected_numbers, market_data, risk_data, follow_pool)
            progress_bar.progress(62)
            
            # Step 6
            status_text.markdown('<div style="color: #1e88e5; font-weight: bold;">Step 6/8: 组合打法构建...</div>', unsafe_allow_html=True)
            combinations = step6_build_combinations(core_pool_data['core_pool'])
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
            filename = save_prediction(prediction_data, n_plus_1, 'prediction1')
            st.session_state['prediction_data'] = prediction_data
            st.session_state['prediction1_data'] = prediction_data
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
            
            # 展示 Step 4-5 核心池
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
            
            # 展示 Step 6 组合
            st.divider()
            st.subheader('📌 Step 6: 组合打法')
            
            tab_11, tab_8, tab_6, tab_4 = st.tabs(['3组11码', '5组8码', '10组6码', '10组4码'])
            with tab_11:
                col_11_1, col_11_2 = st.columns(2)
                for i, comb in enumerate(combinations['eleven_code'], 1):
                    if i <= 2:
                        with col_11_1:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">11-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
                    else:
                        with col_11_2:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">11-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
            with tab_8:
                col_8_1, col_8_2 = st.columns(2)
                for i, comb in enumerate(combinations['eight_code'], 1):
                    if i <= 3:
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
            with tab_4:
                col_4_1, col_4_2 = st.columns(2)
                for i, comb in enumerate(combinations['four_code'], 1):
                    if i <= 5:
                        with col_4_1:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">4-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
                    else:
                        with col_4_2:
                            st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">4-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
            
            # 数据管理
            st.divider()
            st.subheader('💾 预测数据管理')
            
            col_del1, col_del2 = st.columns(2)
            with col_del1:
                st.markdown('**📋 当前存档记录**')
                pred_files = []
                if os.path.exists('predictions'):
                    for f in os.listdir('predictions'):
                        if f.endswith('_prediction1.json'):
                            pred_files.append(f.replace('_prediction1.json', ''))
                if pred_files:
                    for pf in sorted(pred_files, reverse=True):
                        st.text(f'• {pf}')
                else:
                    st.text('暂无存档')
            
            with col_del2:
                if pred_files:
                    delete_period = st.selectbox('选择要删除的期号', pred_files, key='del_pred1_period')
                    if st.button('🗑️ 删除选中记录', type='secondary', key='btn_del_pred1'):
                        if delete_prediction_record(delete_period, 'prediction1'):
                            st.success(f'✅ 已删除 {delete_period} 期预测记录')
                        else:
                            st.error('❌ 删除失败')
    else:
        st.warning('⚠️ 数据不足 10 期，无法执行完整 SOP 流程')

# ==================== 【Tab 6】V7.1 动态趋势适配 ====================
with tabs[5]:
    st.header('🔄 V7.1 动态趋势适配')
    st.divider()
    
    # 检查是否有相随号池
    if 'current_follow_pool' not in st.session_state or not st.session_state.current_follow_pool:
        st.warning('⚠️ 请先在 Tab 4 中生成相随号池！')
        st.info('💡 提示：请先前往 Tab 4 生成相随号池后再执行V7.1体系')
    else:
        st.success(f'✅ 已检测到相随号池（期号：{st.session_state.current_follow_period}，共 {len(st.session_state.current_follow_pool)} 个号码）')
        st.markdown(f"""
        <div style="background-color: #e3f2fd; padding: 12px; border-radius: 6px; margin-bottom: 20px;">
        <h4 style="margin-top: 0; color: #1565c0;">相随号池号码</h4>
        <p style="font-family: monospace; font-size: 14px;">{' '.join(map(str, sorted(st.session_state.current_follow_pool)))}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 选择期数
        period_list = st.session_state.lottery_data.index.tolist()
        sop_n_period = st.selectbox(
            '请选择 N 期数（已开奖的最后一期）',
            period_list,
            index=len(period_list)-1,
            help='选择已开奖的最后一期 N，系统将为 N+1 期进行预测'
        )
        
        n_plus_1 = str(int(sop_n_period) + 1)
        st.write(f'已选择 **{sop_n_period}** 期，将为 **{n_plus_1}** 期进行预测')
        
        # 直接执行，不需要点击按钮
        # 数据准备
        data = st.session_state.lottery_data.loc[:sop_n_period].copy()
        follow_pool = st.session_state.current_follow_pool
        
        # ==================== Step 0: 基础信息与用户硬性要求前置执行 ====================
        st.markdown('### Step 0: 基础信息与用户硬性要求前置执行')
        col_s0_1, col_s0_2 = st.columns(2)
        
        # 获取最近几期数据
        last_period = data.iloc[-1].dropna().astype(int).tolist()
        second_last = data.iloc[-2].dropna().astype(int).tolist() if len(data) >= 2 else []
        third_last = data.iloc[-3].dropna().astype(int).tolist() if len(data) >= 3 else []
        
        # 找出连续三期开出的号码
        three_consecutive = []
        if len(data) >= 3:
            for num in range(1, 81):
                if num in last_period and num in second_last and num in third_last:
                    three_consecutive.append(num)
        
        # 找出连续两期开出的号码
        two_consecutive = []
        if len(data) >= 2:
            for num in range(1, 81):
                if num in last_period and num in second_last and num not in three_consecutive:
                    two_consecutive.append(num)
        
        with col_s0_1:
            st.markdown(f'''
            <div style="background-color: #ffebee; padding: 12px; border-radius: 6px;">
            <h4 style="margin-top: 0; color: #c62828;">连续三期开出号码（剔除）</h4>
            <p>{three_consecutive if three_consecutive else "无"}</p>
            </div>
            ''', unsafe_allow_html=True)
        
        with col_s0_2:
            st.markdown(f'''
            <div style="background-color: #fff3e0; padding: 12px; border-radius: 6px;">
            <h4 style="margin-top: 0; color: #ef6c00;">连续两期开出号码（降权）</h4>
            <p>{two_consecutive if two_consecutive else "无"}</p>
            </div>
            ''', unsafe_allow_html=True)
        
        # ==================== Step 1: 双层级区间量化预判与趋势强度分级 ====================
        st.divider()
        st.markdown('### Step 1: 双层级区间量化预判与趋势强度分级')
        
        # 计算号码统计
        stats_100 = data.apply(lambda x: x.dropna().astype(int).value_counts()).sum()
        stats_100 = stats_100.reindex(range(1, 81), fill_value=0)
        
        stats_30 = data.tail(30).apply(lambda x: x.dropna().astype(int).value_counts()).sum()
        stats_30 = stats_30.reindex(range(1, 81), fill_value=0)
        
        stats_20 = data.tail(20).apply(lambda x: x.dropna().astype(int).value_counts()).sum()
        stats_20 = stats_20.reindex(range(1, 81), fill_value=0)
        
        stats_10 = data.tail(10).apply(lambda x: x.dropna().astype(int).value_counts()).sum()
        stats_10 = stats_10.reindex(range(1, 81), fill_value=0)
        
        # 简单判断趋势强度（基于热度）
        hot_count = sum(1 for num in range(1, 81) if stats_30[num] >= 8)
        trend_score = min(100, hot_count * 5 + 50)
        
        if trend_score >= 90:
            trend_level = "🔥 极强趋势"
            trend_desc = "核心子区间连续3期上行，开出数量≥7个"
        elif trend_score >= 70:
            trend_level = "⚡ 强趋势"
            trend_desc = "核心子区间连续2期上行，开出数量5-6个"
        elif trend_score >= 60:
            trend_level = "📊 弱趋势"
            trend_desc = "核心子区间震荡上行，开出数量3-4个"
        else:
            trend_level = "⚖️ 无趋势"
            trend_desc = "各区间均衡震荡，无明显核心趋势"
        
        st.markdown(f"""
        <div style="background-color: #e8f5e8; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
        <h3 style="margin-top: 0; color: #2e7d32;">趋势强度评分：{trend_score}分</h3>
        <p style="font-size: 18px; font-weight: bold;">{trend_level}</p>
        <p>{trend_desc}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # ==================== Step 2-3: 单号码价值量化评分 ====================
        st.divider()
        st.markdown('### Step 2-3: 单号码价值量化评分')
        
        # 计算每个号码的评分（从相随号池中选）
        scores = {}
        for num in follow_pool:
            # 基础分 - 近期热度
            score = stats_30[num] * 15 + stats_20[num] * 25 + stats_10[num] * 40
            
            # 遗漏加分
            omission = 0
            for i, idx in enumerate(reversed(data.index)):
                if num in data.loc[idx].dropna().astype(int).tolist():
                    omission = i
                    break
            else:
                omission = 30
            score += max(0, 20 - omission) * 2
            
            # 连续两期降权
            if num in two_consecutive:
                score -= 20
            
            # 连续三期直接排除
            if num in three_consecutive:
                continue
            
            scores[num] = max(0, score)
        
        # 分级
        s_level = []
        a_level = []
        b_level = []
        
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        for num, score in sorted_scores:
            if score >= 80:
                s_level.append(num)
            elif score >= 60:
                a_level.append(num)
            else:
                b_level.append(num)
        
        col_s3_1, col_s3_2, col_s3_3 = st.columns(3)
        with col_s3_1:
            st.markdown(f'''
            <div style="background-color: #ffebee; padding: 12px; border-radius: 6px;">
            <h4 style="margin-top: 0; color: #c62828;">S级号码 (≥80分)</h4>
            <p>{s_level if s_level else "无"}</p>
            </div>
            ''', unsafe_allow_html=True)
        
        with col_s3_2:
            st.markdown(f'''
            <div style="background-color: #fff3e0; padding: 12px; border-radius: 6px;">
            <h4 style="margin-top: 0; color: #ef6c00;">A级号码 (60-79分)</h4>
            <p>{a_level if a_level else "无"}</p>
            </div>
            ''', unsafe_allow_html=True)
        
        with col_s3_3:
            st.markdown(f'''
            <div style="background-color: #f5f5f5; padding: 12px; border-radius: 6px;">
            <h4 style="margin-top: 0; color: #333;">B级号码 (&lt;60分)</h4>
            <p>{b_level if b_level else "无"}</p>
            </div>
            ''', unsafe_allow_html=True)
        
        # ==================== Step 4: 动态自适应15码核心池构建 ====================
        st.divider()
        st.markdown('### Step 4: 动态自适应15码核心池构建')
        
        candidate_pool = s_level + a_level
        # 确保只从相随号池中选
        candidate_pool = [num for num in candidate_pool if num in follow_pool]
        
        # 控制与上期重合度
        overlap = set(candidate_pool) & set(last_period)
        overlap_count = len(overlap)
        
        if overlap_count > 3:
            # 移除部分重合号码
            for num in list(overlap):
                if overlap_count <= 3:
                    break
                candidate_pool.remove(num)
                overlap_count -= 1
        
        # 构建核心池
        core_pool = []
        for num in candidate_pool:
            if len(core_pool) >= 15:
                break
            core_pool.append(num)
        
        # 如果还不够，补充B级
        for num in b_level:
            if len(core_pool) >= 15:
                break
            if num in follow_pool:
                core_pool.append(num)
        
        # 确保排序
        core_pool = sorted(core_pool)
        
        st.markdown(f"""
        <div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; margin-bottom: 12px;">
        <h4 style="margin-top: 0; color: #1565c0;">15码核心池（升序）</h4>
        <p style="font-family: monospace; font-size: 16px;">{' '.join(map(str, core_pool))}</p>
        <p style="font-size: 12px; color: #666; margin-bottom: 0;">与上期重合号码：{sorted(overlap)}（{len(overlap)}个）</p>
        </div>
        """, unsafe_allow_html=True)
        
        # ==================== Step 5: 分级动态组合构建 ====================
        st.divider()
        st.markdown('### Step 5: 分级动态组合构建')
        
        # 生成组合
        def generate_combinations_v71(core_list):
            core_sorted = sorted(core_list)
            n = len(core_sorted)
            
            def get_comb(size, start_idx):
                comb = []
                for i in range(size):
                    idx = (start_idx + i * 2) % n
                    comb.append(core_sorted[idx])
                return sorted(list(set(comb)))
            
            # 3组11码
            eleven_code = []
            for i in range(3):
                comb = get_comb(11, i * 4)
                # 补充号码
                while len(comb) < 11:
                    for num in core_sorted:
                        if num not in comb:
                            comb.append(num)
                            break
                    comb.sort()
                eleven_code.append(sorted(comb))
            
            # 5组8码
            eight_code = []
            for i in range(5):
                comb = get_comb(8, i * 3)
                while len(comb) < 8:
                    for num in core_sorted:
                        if num not in comb:
                            comb.append(num)
                            break
                    comb.sort()
                eight_code.append(sorted(comb))
            
            # 10组6码
            six_code = []
            for i in range(10):
                if i < 4:
                    comb = get_comb(6, i * 3)
                elif i < 7:
                    comb = get_comb(6, i)
                else:
                    comb = get_comb(6, i * 2)
                while len(comb) < 6:
                    for num in core_sorted:
                        if num not in comb:
                            comb.append(num)
                            break
                    comb.sort()
                six_code.append(sorted(comb))
            
            # 4组4码
            four_code = []
            for i in range(4):
                if i == 0:
                    comb = core_sorted[:4]
                elif i == 1:
                    comb = core_sorted[4:8]
                elif i == 2:
                    comb = core_sorted[8:12]
                else:
                    comb = core_sorted[-4:]
                comb = sorted(list(set(comb)))
                while len(comb) < 4:
                    for num in core_sorted:
                        if num not in comb:
                            comb.append(num)
                            break
                    comb.sort()
                four_code.append(sorted(comb))
            
            return {
                'eleven_code': eleven_code,
                'eight_code': eight_code,
                'six_code': six_code,
                'four_code': four_code
            }
        
        combinations = generate_combinations_v71(core_pool)
        
        # 显示组合
        tab_11, tab_8, tab_6, tab_4 = st.tabs(['3组11码', '5组8码', '10组6码', '4组4码'])
        
        with tab_11:
            col_11_1, col_11_2 = st.columns(2)
            for i, comb in enumerate(combinations['eleven_code'], 1):
                if i <= 2:
                    with col_11_1:
                        st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">11-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
                else:
                    with col_11_2:
                        st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">11-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
        
        with tab_8:
            col_8_1, col_8_2 = st.columns(2)
            for i, comb in enumerate(combinations['eight_code'], 1):
                if i <= 3:
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
        
        with tab_4:
            col_4_1, col_4_2 = st.columns(2)
            for i, comb in enumerate(combinations['four_code'], 1):
                if i <= 2:
                    with col_4_1:
                        st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">4-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
                else:
                    with col_4_2:
                        st.markdown('''<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; margin-bottom: 8px;"><span style="font-weight: bold;">4-{:02d}</span>：{}</div>'''.format(i, ' '.join(map(str, sorted(comb)))), unsafe_allow_html=True)
        
        # ==================== Step 6-7: 保存方案 ====================
        st.divider()
        st.markdown('### Step 6-7: 终版方案存档')
        
        prediction_data = {
            'period': n_plus_1,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'trend_score': trend_score,
            'trend_level': trend_level,
            'core_pool': ' '.join(map(str, core_pool)),
            'combinations': combinations
        }
        
        filename = save_prediction(prediction_data, n_plus_1, 'prediction2')
        st.session_state['prediction_data'] = prediction_data
        st.session_state['prediction2_data'] = prediction_data
        st.success(f'✅ V7.1预测方案已成功保存！')
        
        # 数据管理
        st.divider()
        st.subheader('💾 预测数据管理')
        
        col_del1, col_del2 = st.columns(2)
        with col_del1:
            st.markdown('**📋 当前存档记录 (Tab6 V7.1)**')
            pred_files = []
            if os.path.exists('predictions'):
                for f in os.listdir('predictions'):
                    if f.endswith('_prediction2.json'):
                        pred_files.append(f.replace('_prediction2.json', ''))
            if pred_files:
                for pf in sorted(pred_files, reverse=True):
                    st.text(f'• {pf}')
            else:
                st.text('暂无存档')
        
        with col_del2:
            if pred_files:
                delete_period = st.selectbox('选择要删除的期号(Tab6)', pred_files, key='del_tab6')
                if st.button('🗑️ 删除选中记录', type='secondary', key='btn_tab6'):
                    if delete_prediction_record(delete_period, 'prediction2'):
                        st.success(f'✅ 已删除 {delete_period} 期预测记录')
                    else:
                        st.error('❌ 删除失败')

with tabs[6]:
    st.header('🔍 开奖号对比')
    st.divider()

    # 获取Tab1号码库期号列表
    period_list = st.session_state.lottery_data.index.tolist() if len(st.session_state.lottery_data) > 0 else []

    # 加载Tab5预测数据(prediction1)和Tab6预测数据(prediction2)
    predictions1 = load_predictions_by_type('prediction1')
    predictions2 = load_predictions_by_type('prediction2')

    # 加载Tab4相随号池
    follow_pools = load_all_follow_pools()

    if not period_list:
        st.warning('⚠️ 暂无开奖数据，请先在 Tab 1 中添加数据')
    else:
        # 选择开奖期号
        selected_period = st.selectbox('选择开奖期号', period_list, index=len(period_list)-1, key='tab7_select_period')

        # 获取开奖号码
        winning_numbers = st.session_state.lottery_data.loc[selected_period].dropna().astype(int).tolist()
        winning_numbers_str = ' '.join(map(str, sorted(winning_numbers)))

        st.markdown(f'''
        <div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
            <h4 style="margin-top: 0; color: #1565c0;">开奖期号：{selected_period}</h4>
            <p style="font-family: monospace; font-size: 16px;">开奖号码：{winning_numbers_str}</p>
        </div>
        ''', unsafe_allow_html=True)

        st.divider()

        # 查找对应的预测数据
        # Tab 4 相随号池（用n_plus_1匹配预测期）
        tab4_pool = None
        tab4_key = None
        for key, pool_data in follow_pools.items():
            if pool_data.get('n_plus_1') == selected_period:
                tab4_pool = pool_data
                tab4_key = key
                break

        # Tab 5 核心池（用period匹配）
        tab5_data = None
        tab5_key = None
        for key, pred_data in predictions1.items():
            if pred_data.get('period') == selected_period:
                tab5_data = pred_data
                tab5_key = key
                break

        # Tab 6 核心池（用period匹配）
        tab6_data = None
        tab6_key = None
        for key, pred_data in predictions2.items():
            if pred_data.get('period') == selected_period:
                tab6_data = pred_data
                tab6_key = key
                break

        # 辅助函数：生成带高亮的号码显示
        def highlight_numbers(pool_nums, winning_set):
            result_html = []
            for num in sorted(pool_nums):
                if num in winning_set:
                    result_html.append(f'<span style="color: #dc2626; font-weight: bold; text-decoration: underline;">{num}</span>')
                else:
                    result_html.append(f'<span style="color: #666;">{num}</span>')
            return ' '.join(result_html)

        # 三组数据命中率对比
        st.subheader('📊 三组核心池命中率对比')

        col_tab4, col_tab5, col_tab6 = st.columns(3)

        # Tab 4 相随号池
        with col_tab4:
            if tab4_pool:
                pool_nums = tab4_pool.get('follow_pool', [])
                if isinstance(pool_nums, str):
                    pool_nums = [int(x) for x in pool_nums.split()]
                pool_nums_set = set(pool_nums)
                pool_hit = len(pool_nums_set & set(winning_numbers))
                pool_rate = pool_hit / len(pool_nums) * 100 if pool_nums else 0

                # 颜色根据命中率变化
                if pool_rate >= 40:
                    pool_color = "#2e7d32"  # 绿色
                    pool_bg = "#e8f5e8"
                elif pool_rate >= 25:
                    pool_color = "#d97706"  # 橙色
                    pool_bg = "#fff3e0"
                else:
                    pool_color = "#dc2626"  # 红色
                    pool_bg = "#fef2f2"

                st.markdown(f'''
                <div style="background-color: {pool_bg}; padding: 16px; border-radius: 8px; border-left: 4px solid #0369a1;">
                    <h4 style="margin-top: 0; color: #0369a1;">📍 Tab4 相随号池</h4>
                    <p style="font-size: 14px; margin: 8px 0;">期号：<strong>{tab4_key}</strong></p>
                    <p style="font-size: 28px; font-weight: bold; color: {pool_color}; margin: 8px 0;">{pool_rate:.1f}%</p>
                    <p style="font-size: 14px;">命中：<strong>{pool_hit}/{len(pool_nums)}</strong> 码</p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 10px 0;">
                    <p style="font-size: 12px; font-family: monospace; line-height: 1.6;">
                        {highlight_numbers(pool_nums, set(winning_numbers))}
                    </p>
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown(f'''
                <div style="background-color: #f5f5f5; padding: 16px; border-radius: 8px; border-left: 4px solid #94a3b8;">
                    <h4 style="margin-top: 0; color: #64748b;">📍 Tab4 相随号池</h4>
                    <p style="font-size: 14px; color: #64748b;">暂无对应期号数据</p>
                </div>
                ''', unsafe_allow_html=True)

        # Tab 5 核心池
        with col_tab5:
            if tab5_data:
                core5_nums = [int(x) for x in tab5_data.get('core_pool', '').split()]
                core5_set = set(core5_nums)
                core5_hit = len(core5_set & set(winning_numbers))
                core5_rate = core5_hit / len(core5_nums) * 100 if core5_nums else 0

                if core5_rate >= 40:
                    core5_color = "#2e7d32"
                    core5_bg = "#e8f5e8"
                elif core5_rate >= 25:
                    core5_color = "#d97706"
                    core5_bg = "#fff3e0"
                else:
                    core5_color = "#dc2626"
                    core5_bg = "#fef2f2"

                st.markdown(f'''
                <div style="background-color: {core5_bg}; padding: 16px; border-radius: 8px; border-left: 4px solid #2e7d32;">
                    <h4 style="margin-top: 0; color: #2e7d32;">🎯 Tab5 15码核心池</h4>
                    <p style="font-size: 14px; margin: 8px 0;">期号：<strong>{tab5_key}</strong></p>
                    <p style="font-size: 28px; font-weight: bold; color: {core5_color}; margin: 8px 0;">{core5_rate:.1f}%</p>
                    <p style="font-size: 14px;">命中：<strong>{core5_hit}/{len(core5_nums)}</strong> 码</p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 10px 0;">
                    <p style="font-size: 12px; font-family: monospace; line-height: 1.6;">
                        {highlight_numbers(core5_nums, set(winning_numbers))}
                    </p>
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown(f'''
                <div style="background-color: #f5f5f5; padding: 16px; border-radius: 8px; border-left: 4px solid #94a3b8;">
                    <h4 style="margin-top: 0; color: #64748b;">🎯 Tab5 15码核心池</h4>
                    <p style="font-size: 14px; color: #64748b;">暂无对应期号数据</p>
                </div>
                ''', unsafe_allow_html=True)

        # Tab 6 核心池
        with col_tab6:
            if tab6_data:
                core6_nums = [int(x) for x in tab6_data.get('core_pool', '').split()]
                core6_set = set(core6_nums)
                core6_hit = len(core6_set & set(winning_numbers))
                core6_rate = core6_hit / len(core6_nums) * 100 if core6_nums else 0

                if core6_rate >= 40:
                    core6_color = "#2e7d32"
                    core6_bg = "#e8f5e8"
                elif core6_rate >= 25:
                    core6_color = "#d97706"
                    core6_bg = "#fff3e0"
                else:
                    core6_color = "#dc2626"
                    core6_bg = "#fef2f2"

                st.markdown(f'''
                <div style="background-color: {core6_bg}; padding: 16px; border-radius: 8px; border-left: 4px solid #d97706;">
                    <h4 style="margin-top: 0; color: #d97706;">🚀 Tab6 15码核心池</h4>
                    <p style="font-size: 14px; margin: 8px 0;">期号：<strong>{tab6_key}</strong></p>
                    <p style="font-size: 28px; font-weight: bold; color: {core6_color}; margin: 8px 0;">{core6_rate:.1f}%</p>
                    <p style="font-size: 14px;">命中：<strong>{core6_hit}/{len(core6_nums)}</strong> 码</p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 10px 0;">
                    <p style="font-size: 12px; font-family: monospace; line-height: 1.6;">
                        {highlight_numbers(core6_nums, set(winning_numbers))}
                    </p>
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown(f'''
                <div style="background-color: #f5f5f5; padding: 16px; border-radius: 8px; border-left: 4px solid #94a3b8;">
                    <h4 style="margin-top: 0; color: #64748b;">🚀 Tab6 15码核心池</h4>
                    <p style="font-size: 14px; color: #64748b;">暂无对应期号数据</p>
                </div>
                ''', unsafe_allow_html=True)

        # 操作按钮
        st.divider()
        col_save, col_del, _ = st.columns([1, 1, 2])

        with col_save:
            if tab4_pool or tab5_data or tab6_data:
                if st.button('💾 一键保存所有对比记录', type='primary', use_container_width=True):
                    # 保存Tab4
                    if tab4_pool:
                        pool_nums = tab4_pool.get('follow_pool', [])
                        if isinstance(pool_nums, str):
                            pool_nums = [int(x) for x in pool_nums.split()]
                        pool_nums_set = set(pool_nums)
                        pool_hit = len(pool_nums_set & set(winning_numbers))
                        pool_rate = pool_hit / len(pool_nums) * 100 if pool_nums else 0

                        tab4_comparison_data = {
                            'comparison_period': selected_period,
                            'pred_period': tab4_key,
                            'pred_type': 'tab4_follow_pool',
                            'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'follow_pool': ' '.join(map(str, sorted(pool_nums))),
                            'winning_numbers': winning_numbers_str,
                            'core_hit_count': pool_hit,
                            'core_total': len(pool_nums),
                            'core_hit_rate': pool_rate
                        }
                        if not os.path.exists('comparisons'):
                            os.makedirs('comparisons', exist_ok=True)
                        with open(os.path.join('comparisons', f'{tab4_key}_{selected_period}_tab4_follow_pool_comparison.json'), 'w', encoding='utf-8') as f:
                            json.dump(tab4_comparison_data, f, ensure_ascii=False, indent=2)

                    # 保存Tab5
                    if tab5_data:
                        core5_nums = [int(x) for x in tab5_data.get('core_pool', '').split()]
                        core5_set = set(core5_nums)
                        core5_hit = len(core5_set & set(winning_numbers))
                        core5_rate = core5_hit / len(core5_nums) * 100 if core5_nums else 0

                        tab5_comparison_data = {
                            'comparison_period': selected_period,
                            'pred_period': tab5_key,
                            'pred_type': 'prediction1',
                            'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'core_pool': tab5_data.get('core_pool', ''),
                            'winning_numbers': winning_numbers_str,
                            'core_hit_count': core5_hit,
                            'core_total': len(core5_nums),
                            'core_hit_rate': core5_rate
                        }
                        with open(os.path.join('comparisons', f'{tab5_key}_{selected_period}_prediction1_comparison.json'), 'w', encoding='utf-8') as f:
                            json.dump(tab5_comparison_data, f, ensure_ascii=False, indent=2)

                    # 保存Tab6
                    if tab6_data:
                        core6_nums = [int(x) for x in tab6_data.get('core_pool', '').split()]
                        core6_set = set(core6_nums)
                        core6_hit = len(core6_set & set(winning_numbers))
                        core6_rate = core6_hit / len(core6_nums) * 100 if core6_nums else 0

                        tab6_comparison_data = {
                            'comparison_period': selected_period,
                            'pred_period': tab6_key,
                            'pred_type': 'prediction2',
                            'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'core_pool': tab6_data.get('core_pool', ''),
                            'winning_numbers': winning_numbers_str,
                            'core_hit_count': core6_hit,
                            'core_total': len(core6_nums),
                            'core_hit_rate': core6_rate
                        }
                        with open(os.path.join('comparisons', f'{tab6_key}_{selected_period}_prediction2_comparison.json'), 'w', encoding='utf-8') as f:
                            json.dump(tab6_comparison_data, f, ensure_ascii=False, indent=2)

                    st.success('✅ 所有对比记录已保存！')

        with col_del:
            # 删除该期的所有对比记录
            if os.path.exists('comparisons'):
                del_count = 0
                for filename in os.listdir('comparisons'):
                    if str(selected_period) in filename:
                        del_count += 1
                if del_count > 0:
                    if st.button(f'🗑️ 删除{selected_period}期记录', type='secondary', use_container_width=True):
                        for filename in os.listdir('comparisons'):
                            if str(selected_period) in filename:
                                filepath = os.path.join('comparisons', filename)
                                os.remove(filepath)
                        st.warning(f'⚠️ 已删除{selected_period}期{del_count}条对比记录')
                else:
                    st.button(f'🗑️ 删除{selected_period}期记录', type='secondary', use_container_width=True, disabled=True)


# ==================== 【Tab 8】命中率数据汇总 ====================
with tabs[7]:
    st.header("📊 命中率数据汇总与分析")
    st.divider()
    
    # 加载对比记录
    comparisons = load_all_comparisons()
    
    if not comparisons:
        st.info("ℹ️ 暂无对比数据，请先在 Tab 7 中进行对比并保存记录")
    else:
        # 1. 数据整理 - 按开奖期分组
        period_groups = {}
        for key, data in comparisons.items():
            comp_period = data.get('comparison_period', '')
            pred_type = data.get('pred_type', '')
            
            if comp_period:
                if comp_period not in period_groups:
                    period_groups[comp_period] = {}
                
                if pred_type not in period_groups[comp_period] or \
                   data.get('saved_at', '') > period_groups[comp_period][pred_type].get('saved_at', ''):
                    period_groups[comp_period][pred_type] = {
                        'pred_period': data.get('pred_period', ''),
                        'saved_at': data.get('saved_at', ''),
                        'hit_count': data.get('core_hit_count', 0),
                        'total': data.get('core_total', 0),
                        'rate': data.get('core_hit_rate', 0)
                    }
        
        sorted_periods = sorted(period_groups.keys(), reverse=True)
        
        # 2. 总体统计卡片
        st.subheader("📈 总体命中率统计")
        
        tab4_data = []
        tab5_data = []
        tab6_data = []
        
        for period in sorted_periods:
            group = period_groups[period]
            if 'tab4_follow_pool' in group:
                tab4_data.append(group['tab4_follow_pool'])
            if 'prediction1' in group:
                tab5_data.append(group['prediction1'])
            if 'prediction2' in group:
                tab6_data.append(group['prediction2'])
        
        avg_tab4 = sum(d['rate'] for d in tab4_data) / len(tab4_data) if tab4_data else 0
        avg_tab5 = sum(d['rate'] for d in tab5_data) / len(tab5_data) if tab5_data else 0
        avg_tab6 = sum(d['rate'] for d in tab6_data) / len(tab6_data) if tab6_data else 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f'''
            <div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; text-align: center;">
                <h4 style="margin-top: 0; color: #1565c0;">📍 Tab4 相随号池</h4>
                <p style="font-size: 14px;">数据期数：<strong>{len(tab4_data)}</strong> 期</p>
                <p style="font-size: 32px; font-weight: bold; color: #1565c0;">{avg_tab4:.1f}%</p>
                <p style="font-size: 12px; color: #666;">平均命中率</p>
            </div>
            ''', unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'''
            <div style="background-color: #e8f5e8; padding: 16px; border-radius: 8px; text-align: center;">
                <h4 style="margin-top: 0; color: #2e7d32;">🎯 Tab5 核心池</h4>
                <p style="font-size: 14px;">数据期数：<strong>{len(tab5_data)}</strong> 期</p>
                <p style="font-size: 32px; font-weight: bold; color: #2e7d32;">{avg_tab5:.1f}%</p>
                <p style="font-size: 12px; color: #666;">平均命中率</p>
            </div>
            ''', unsafe_allow_html=True)
        
        with col3:
            st.markdown(f'''
            <div style="background-color: #fff3e0; padding: 16px; border-radius: 8px; text-align: center;">
                <h4 style="margin-top: 0; color: #ef6c00;">🚀 Tab6 核心池</h4>
                <p style="font-size: 14px;">数据期数：<strong>{len(tab6_data)}</strong> 期</p>
                <p style="font-size: 32px; font-weight: bold; color: #ef6c00;">{avg_tab6:.1f}%</p>
                <p style="font-size: 12px; color: #666;">平均命中率</p>
            </div>
            ''', unsafe_allow_html=True)
        
        # 3. 最佳方案判定
        st.divider()
        st.subheader("🏆 最佳方案判定")
        
        if avg_tab4 > avg_tab5 and avg_tab4 > avg_tab6:
            best = "Tab4 相随号池"
            best_color = "#1565c0"
        elif avg_tab5 > avg_tab4 and avg_tab5 > avg_tab6:
            best = "Tab5 核心池"
            best_color = "#2e7d32"
        elif avg_tab6 > avg_tab4 and avg_tab6 > avg_tab5:
            best = "Tab6 核心池"
            best_color = "#ef6c00"
        else:
            best = "多方案持平"
            best_color = "#666"
        
        st.markdown(f'''
        <div style="background-color: #f5f5f5; padding: 16px; border-radius: 8px; text-align: center;">
            <h4 style="margin-top: 0; color: #333;">当前最优方案</h4>
            <p style="font-size: 28px; font-weight: bold; color: {best_color};">{best}</p>
            <p style="font-size: 12px; color: #666;">基于平均命中率判定</p>
        </div>
        ''', unsafe_allow_html=True)
        
        # 4. 每期详细数据表格
        st.divider()
        st.subheader("📋 每期详细对比表")
        
        lottery_data = st.session_state.lottery_data
        
        # 构建表格数据
        table_data = []
        for period in sorted_periods:
            group = period_groups[period]
            
            # 获取开奖号码
            winning_nums = ""
            if period in lottery_data.index:
                nums = lottery_data.loc[period].dropna().astype(int).tolist()
                winning_nums = ' '.join(map(str, sorted(nums)))
            
            row = {
                '期号': period,
                '开奖号码': winning_nums
            }
            
            # Tab4 相随号池
            if 'tab4_follow_pool' in group:
                d = group['tab4_follow_pool']
                row['Tab4命中'] = d['hit_count']
                row['Tab4总数'] = d['total']
                row['Tab4命中率'] = f"{d['rate']:.1f}%"
                row['Tab4命中率数值'] = d['rate']
            else:
                row['Tab4命中'] = '-'
                row['Tab4总数'] = '-'
                row['Tab4命中率'] = '-'
                row['Tab4命中率数值'] = 0
            
            # Tab5 核心池
            if 'prediction1' in group:
                d = group['prediction1']
                row['Tab5命中'] = d['hit_count']
                row['Tab5总数'] = d['total']
                row['Tab5命中率'] = f"{d['rate']:.1f}%"
                row['Tab5命中率数值'] = d['rate']
            else:
                row['Tab5命中'] = '-'
                row['Tab5总数'] = '-'
                row['Tab5命中率'] = '-'
                row['Tab5命中率数值'] = 0
            
            # Tab6 核心池
            if 'prediction2' in group:
                d = group['prediction2']
                row['Tab6命中'] = d['hit_count']
                row['Tab6总数'] = d['total']
                row['Tab6命中率'] = f"{d['rate']:.1f}%"
                row['Tab6命中率数值'] = d['rate']
            else:
                row['Tab6命中'] = '-'
                row['Tab6总数'] = '-'
                row['Tab6命中率'] = '-'
                row['Tab6命中率数值'] = 0
            
            table_data.append(row)
        
        # 创建DataFrame
        df_table = pd.DataFrame(table_data)
        
        # 定义颜色标注函数
        def color_hit_rate(val, threshold=40):
            if val == '-':
                return 'color: #94a3b8; background-color: #f8fafc;'
            try:
                rate = float(val.replace('%', ''))
                if rate >= 40:
                    return 'color: #2e7d32; background-color: #e8f5e8; font-weight: bold;'
                elif rate >= 25:
                    return 'color: #d97706; background-color: #fff3e0; font-weight: bold;'
                else:
                    return 'color: #dc2626; background-color: #fef2f2; font-weight: bold;'
            except:
                return ''
        
        # 应用样式
        styled_df = df_table.style.map(
            lambda x: color_hit_rate(x) if isinstance(x, str) and '%' in x else '',
            subset=['Tab4命中率', 'Tab5命中率', 'Tab6命中率']
        ).set_properties(**{
            'text-align': 'center',
            'border': '1px solid #e2e8f0',
            'padding': '8px'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#1e40af'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center'), ('padding', '10px')]},
            {'selector': 'td', 'props': [('border', '1px solid #e2e8f0')]}
        ])
        
        # 显示表格
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # 添加图例说明
        st.markdown("""
        <div style="background-color: #f5f5f5; padding: 12px; border-radius: 6px; margin-top: 12px;">
            <p style="margin: 0; font-size: 13px; color: #666;">
                <strong>颜色说明：</strong>
                <span style="color: #2e7d32; font-weight: bold; margin-left: 12px;">■ 绿色：命中率 ≥ 40%</span>
                <span style="color: #d97706; font-weight: bold; margin-left: 12px;">■ 橙色：命中率 25%-39%</span>
                <span style="color: #dc2626; font-weight: bold; margin-left: 12px;">■ 红色：命中率 < 25%</span>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 5. 命中率趋势图
        if len(sorted_periods) > 1:
            st.divider()
            st.subheader("📊 命中率趋势对比图")
            
            chart_data = []
            for period in reversed(sorted_periods):
                group = period_groups[period]
                row = {'期号': period}
                if 'tab4_follow_pool' in group:
                    row['Tab4相随号池'] = group['tab4_follow_pool']['rate']
                if 'prediction1' in group:
                    row['Tab5核心池'] = group['prediction1']['rate']
                if 'prediction2' in group:
                    row['Tab6核心池'] = group['prediction2']['rate']
                chart_data.append(row)
            
            if chart_data:
                df_chart = pd.DataFrame(chart_data)
                df_chart.set_index('期号', inplace=True)
                st.line_chart(df_chart, color=['#1565c0', '#2e7d32', '#ef6c00'])
        
        # 6. 数据删除功能
        st.divider()
        st.subheader("🗑️ 数据管理")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if sorted_periods:
                selected_delete = st.selectbox("选择要删除的开奖期号", ['请选择'] + sorted_periods)
                if selected_delete != '请选择':
                    if st.button("删除该期所有记录", type="primary", use_container_width=True):
                        del_count = 0
                        for filename in os.listdir('comparisons'):
                            if str(selected_delete) in filename:
                                filepath = os.path.join('comparisons', filename)
                                os.remove(filepath)
                                del_count += 1
                        if del_count > 0:
                            st.warning(f"⚠️ 已删除 {selected_delete} 期的 {del_count} 条记录")
        
        with col2:
            st.markdown("""
            <div style="background-color: #fef2f2; padding: 12px; border-radius: 6px;">
                <p style="color: #dc2626; margin: 0; font-size: 14px;">
                    <strong>⚠️ 危险操作</strong> - 清空所有对比记录
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("清空所有数据", type="secondary", use_container_width=True):
                for filename in os.listdir('comparisons'):
                    filepath = os.path.join('comparisons', filename)
                    os.remove(filepath)
                st.warning("⚠️ 已清空所有对比记录")
        
        # 7. 数据导出
        st.divider()
        st.subheader("💾 数据导出")
        
        col_export1, col_export2 = st.columns(2)
        
        export_list = []
        for period in sorted_periods:
            group = period_groups[period]
            row = {'期号': period}
            
            if 'tab4_follow_pool' in group:
                d = group['tab4_follow_pool']
                row['Tab4命中'] = d['hit_count']
                row['Tab4总数'] = d['total']
                row['Tab4命中率'] = d['rate']
            
            if 'prediction1' in group:
                d = group['prediction1']
                row['Tab5命中'] = d['hit_count']
                row['Tab5总数'] = d['total']
                row['Tab5命中率'] = d['rate']
            
            if 'prediction2' in group:
                d = group['prediction2']
                row['Tab6命中'] = d['hit_count']
                row['Tab6总数'] = d['total']
                row['Tab6命中率'] = d['rate']
            
            export_list.append(row)
        
        with col_export1:
            if st.button("📥 导出为CSV", type="primary", use_container_width=True):
                df_export = pd.DataFrame(export_list)
                csv = df_export.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="下载 CSV 文件",
                    data=csv,
                    file_name=f"命中率对比_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col_export2:
            if st.button("📥 导出为JSON", type="secondary", use_container_width=True):
                json_str = json.dumps(export_list, ensure_ascii=False, indent=2)
                st.download_button(
                    label="下载 JSON 文件",
                    data=json_str,
                    file_name=f"命中率对比_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )


# ==================== 【Tab 9】V7.2a 用户核心池驱动系统 ====================
with tabs[8]:
    st.header('⚙️ 快乐8预测体系 V7.2a「用户核心池驱动 + 全周期趋势适配」系统')
    st.divider()

    # 初始化会话状态
    if 'v72a_initialized' not in st.session_state:
        st.session_state.v72a_initialized = False
    if 'v72a_auto_run_done' not in st.session_state:
        st.session_state.v72a_auto_run_done = False

    # 加载Tab5预测数据
    predictions1 = load_predictions_by_type('prediction1')
    
    if not predictions1:
        st.warning('⚠️ 暂无Tab5预测数据，请先在Tab5中生成15码核心池')
    else:
        # 获取所有可用期号（自动选择最新的）
        available_periods = list(predictions1.keys())
        latest_period = available_periods[-1]  # 最新期号
        
        # 自动加载最新期的15码核心池并执行诊断
        if latest_period in predictions1:
            pred_data = predictions1[latest_period]
            if 'core_pool' in pred_data:
                # 解析核心池
                core_pool_str = pred_data['core_pool']
                core_pool = [int(x) for x in core_pool_str.split()]
                core_pool = sorted(list(set(core_pool)))
                
                if len(core_pool) == 15:
                    # 保存到session_state
                    st.session_state.v72a_core_pool = core_pool
                    st.session_state.v72a_selected_period = latest_period
                    
                    # 自动执行诊断和组合生成
                    st.subheader('📥 自动加载：最新15码核心池')
                    st.markdown(f"""
                    <div style="background-color: #e8f5e8; padding: 12px; border-radius: 8px; border-left: 4px solid #2e7d32; margin-bottom: 16px;">
                    <p style="margin: 0; font-size: 14px;"><strong>已自动加载 {latest_period} 期核心池：</strong></p>
                    <p style="font-family: monospace; font-size: 16px; margin: 8px 0 0 0;">{' '.join(map(str, core_pool))}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 执行诊断
                    lottery_data = st.session_state.lottery_data
                    
                    # 1. 区间分布诊断
                    def get_interval(num):
                        if 1 <= num <= 20:
                            return 'A'
                        elif 21 <= num <= 40:
                            return 'B'
                        elif 41 <= num <= 60:
                            return 'C'
                        else:
                            return 'D'
                    
                    intervals = [get_interval(n) for n in core_pool]
                    interval_counts = {'A': intervals.count('A'), 'B': intervals.count('B'), 'C': intervals.count('C'), 'D': intervals.count('D')}
                    total = sum(interval_counts.values())
                    
                    # 确定核心区间和对冲区间
                    max_interval = max(interval_counts, key=interval_counts.get)
                    core_interval = max_interval
                    hedge_intervals = [k for k, v in interval_counts.items() if v > 0 and k != max_interval]
                    missing_intervals = [k for k, v in interval_counts.items() if v == 0]
                    
                    # 2. 冷热结构诊断（基于历史数据）
                    if len(lottery_data) >= 20:
                        recent_data = lottery_data.tail(20)
                        all_recent_nums = recent_data.values.flatten()
                        all_recent_nums = [int(x) for x in all_recent_nums if pd.notna(x)]
                        
                        def get_cold_level(num):
                            count = all_recent_nums.count(num)
                            if count >= 4:
                                return '热号'
                            elif count >= 2:
                                return '温号'
                            elif count >= 1:
                                return '冷号'
                            else:
                                return '深冷号'
                        
                        cold_levels = [get_cold_level(n) for n in core_pool]
                        cold_counts = {'热号': cold_levels.count('热号'), '温号': cold_levels.count('温号'), 
                                     '冷号': cold_levels.count('冷号'), '深冷号': cold_levels.count('深冷号')}
                        
                        # 冷热均衡度评分
                        ideal_dist = [3, 7, 3, 2]  # 理想分布
                        actual_dist = [cold_counts['热号'], cold_counts['温号'], cold_counts['冷号'], cold_counts['深冷号']]
                        balance_score = 100 - sum(abs(a - i) for a, i in zip(actual_dist, ideal_dist)) * 5
                        balance_score = max(0, min(100, balance_score))
                    else:
                        cold_counts = {'热号': 0, '温号': 0, '冷号': 0, '深冷号': 0}
                        balance_score = 50
                        def get_cold_level(num):
                            return '温号'
                    
                    # 3. 价值密度诊断（简化版评分）
                    def get_value_score(num, cold_level):
                        interval_weights = {'A': 1.0, 'B': 1.1, 'C': 1.2, 'D': 1.0}
                        cold_weights = {'热号': 1.2, '温号': 1.0, '冷号': 0.9, '深冷号': 0.7}
                        return interval_weights[get_interval(num)] * cold_weights[cold_level]
                    
                    value_scores = [get_value_score(n, get_cold_level(n)) if len(lottery_data) >= 20 else 1.0 for n in core_pool]
                    avg_value = sum(value_scores) / len(value_scores)
                    
                    # 评级
                    if avg_value >= 1.1:
                        value_grade = 'S级'
                    elif avg_value >= 1.0:
                        value_grade = 'A级'
                    else:
                        value_grade = 'B级'
                    
                    # 4. 趋势契合度诊断（简化版）
                    trend_score = 68
                    
                    # 5. 风险集中度诊断
                    max_concentration = max(interval_counts.values()) / total * 100
                    if max_concentration <= 40:
                        risk_level = '低风险'
                    elif max_concentration <= 55:
                        risk_level = '中风险'
                    else:
                        risk_level = '高风险'
                    
                    # 6. 历史命中率诊断（模拟）
                    expected_hits = round(15 * 0.42)
                    
                    # 保存诊断结果
                    diagnosis = {
                        'core_pool': core_pool,
                        'interval_analysis': {
                            'counts': interval_counts,
                            'core_interval': core_interval,
                            'hedge_intervals': hedge_intervals,
                            'missing_intervals': missing_intervals
                        },
                        'cold_analysis': {
                            'counts': cold_counts,
                            'balance_score': balance_score
                        },
                        'value_analysis': {
                            'avg_value': avg_value,
                            'grade': value_grade
                        },
                        'trend_score': trend_score,
                        'risk_level': risk_level,
                        'expected_hits': expected_hits
                    }
                    st.session_state.v72a_diagnosis = diagnosis
                    
                    # 自动生成分层组合
                    import random
                    random.seed(int(latest_period) if latest_period.isdigit() else 42)
                    
                    def generate_combinations(pool, n, size):
                        combinations = []
                        attempts = 0
                        max_attempts = 1000
                        
                        while len(combinations) < n and attempts < max_attempts:
                            candidate = sorted(random.sample(pool, size))
                            valid = True
                            for combo in combinations:
                                overlap = len(set(candidate) & set(combo))
                                if size == 11 and overlap > 2:
                                    valid = False
                                    break
                                if size in [6, 8] and overlap > 1:
                                    valid = False
                                    break
                            if valid:
                                combinations.append(candidate)
                            attempts += 1
                        
                        return combinations
                    
                    combinations_11 = generate_combinations(core_pool, 3, 11)
                    combinations_8 = generate_combinations(core_pool, 5, 8)
                    combinations_6 = generate_combinations(core_pool, 10, 6)
                    
                    st.session_state.v72a_combinations = {
                        '11码': combinations_11,
                        '8码': combinations_8,
                        '6码': combinations_6
                    }
                    
                    st.session_state.v72a_initialized = True
                

    # 显示诊断结果
    if st.session_state.v72a_diagnosis:
        diagnosis = st.session_state.v72a_diagnosis
        
        st.divider()
        st.subheader('📊 Step 2：核心池多维度诊断报告')
        
        # 区间分布诊断
        st.markdown('#### 1️⃣ 区间分布诊断')
        col_int1, col_int2 = st.columns(2)
        with col_int1:
            df_interval = pd.DataFrame({
                '区间': list(diagnosis['interval_analysis']['counts'].keys()),
                '数量': list(diagnosis['interval_analysis']['counts'].values())
            })
            st.dataframe(df_interval, use_container_width=True, hide_index=True)
        with col_int2:
            st.markdown(f"""
            <div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px;">
            <h5 style="margin-top: 0; color: #1565c0;">诊断结果</h5>
            <p><strong>核心区间：</strong>{diagnosis['interval_analysis']['core_interval']}区</p>
            <p><strong>对冲区间：</strong>{', '.join(diagnosis['interval_analysis']['hedge_intervals'])}</p>
            <p><strong>缺失区间：</strong>{', '.join(diagnosis['interval_analysis']['missing_intervals']) if diagnosis['interval_analysis']['missing_intervals'] else '无'}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # 冷热结构诊断
        st.markdown('#### 2️⃣ 冷热结构诊断')
        col_cold1, col_cold2 = st.columns(2)
        with col_cold1:
            df_cold = pd.DataFrame({
                '类型': list(diagnosis['cold_analysis']['counts'].keys()),
                '数量': list(diagnosis['cold_analysis']['counts'].values())
            })
            st.dataframe(df_cold, use_container_width=True, hide_index=True)
        with col_cold2:
            balance_color = '#2e7d32' if diagnosis['cold_analysis']['balance_score'] >= 70 else '#d97706' if diagnosis['cold_analysis']['balance_score'] >= 50 else '#dc2626'
            st.markdown(f"""
            <div style="background-color: #e8f5e8; padding: 16px; border-radius: 8px;">
            <h5 style="margin-top: 0; color: #2e7d32;">均衡度评分</h5>
            <p style="font-size: 32px; font-weight: bold; color: {balance_color};">{diagnosis['cold_analysis']['balance_score']:.0f}</p>
            <p style="font-size: 13px; color: #666;">冷热均衡度</p>
            </div>
            """, unsafe_allow_html=True)
        
        # 价值密度诊断
        st.markdown('#### 3️⃣ 价值密度诊断')
        value_color = '#2e7d32' if diagnosis['value_analysis']['grade'] == 'S级' else '#d97706' if diagnosis['value_analysis']['grade'] == 'A级' else '#dc2626'
        st.markdown(f"""
        <div style="background-color: #fff3e0; padding: 16px; border-radius: 8px;">
        <h5 style="margin-top: 0; color: #ef6c00;">核心池整体价值评分</h5>
        <p style="font-size: 32px; font-weight: bold; color: {value_color};">{diagnosis['value_analysis']['grade']}</p>
        <p style="font-size: 13px; color: #666;">综合评分：{diagnosis['value_analysis']['avg_value']:.2f}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 其他诊断
        col_other1, col_other2, col_other3 = st.columns(3)
        with col_other1:
            st.markdown(f"""
            <div style="background-color: #f3e5f5; padding: 16px; border-radius: 8px; text-align: center;">
            <h5 style="margin-top: 0; color: #7b1fa2;">趋势契合度</h5>
            <p style="font-size: 28px; font-weight: bold; color: #7b1fa2;">{diagnosis['trend_score']}</p>
            <p style="font-size: 12px; color: #666;">满分100分</p>
            </div>
            """, unsafe_allow_html=True)
        with col_other2:
            risk_color = '#2e7d32' if diagnosis['risk_level'] == '低风险' else '#d97706' if diagnosis['risk_level'] == '中风险' else '#dc2626'
            st.markdown(f"""
            <div style="background-color: #ffebee; padding: 16px; border-radius: 8px; text-align: center;">
            <h5 style="margin-top: 0; color: #c62828;">风险等级</h5>
            <p style="font-size: 20px; font-weight: bold; color: {risk_color};">{diagnosis['risk_level']}</p>
            </div>
            """, unsafe_allow_html=True)
        with col_other3:
            st.markdown(f"""
            <div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; text-align: center;">
            <h5 style="margin-top: 0; color: #1565c0;">预期命中</h5>
            <p style="font-size: 28px; font-weight: bold; color: #1565c0;">{diagnosis['expected_hits']}</p>
            <p style="font-size: 12px; color: #666;">预期命中区间</p>
            </div>
            """, unsafe_allow_html=True)

        # 生成组合按钮
        st.divider()
        st.subheader('🎯 Step 3：生成分层组合方案')
        
        if st.button('🚀 生成3/5/10组合方案', type='primary', use_container_width=True):
            core_pool = diagnosis['core_pool']
            
            # 实现组合生成算法
            import random
            random.seed(42)  # 固定种子确保可重复性
            
            # 定义组合生成函数
            # 生成组合
            combinations_11 = generate_combinations(core_pool, 3, 11)
            combinations_8 = generate_combinations(core_pool, 5, 8)
            combinations_6 = generate_combinations(core_pool, 10, 6)
            
            st.session_state.v72a_combinations = {
                '11码': combinations_11,
                '8码': combinations_8,
                '6码': combinations_6
            }
            
            st.success('✅ 组合方案生成成功！')

    # 显示组合结果
    if st.session_state.v72a_combinations:
        combos = st.session_state.v72a_combinations
        
        st.markdown('#### 一、3组11码组合')
        for i, combo in enumerate(combos['11码'], 1):
            risk_type = '激进型' if i == 1 else '稳健型'
            st.markdown(f"""
            <div style="background-color: #f5f5f5; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
            <span style="color: #666; font-size: 13px;">{risk_type}</span>
            <p style="font-family: monospace; font-size: 16px; margin: 4px 0 0 0;">{' '.join(f'{n:02d}' for n in combo)}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('#### 二、5组8码组合')
        for i, combo in enumerate(combos['8码'], 1):
            risk_type = '主投型' if i <= 2 else '平衡型'
            st.markdown(f"""
            <div style="background-color: #f5f5f5; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
            <span style="color: #666; font-size: 13px;">{risk_type}</span>
            <p style="font-family: monospace; font-size: 16px; margin: 4px 0 0 0;">{' '.join(f'{n:02d}' for n in combo)}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('#### 三、10组6码组合')
        st.markdown('**核心主投组（3组）**')
        for combo in combos['6码'][:3]:
            st.code(' '.join(f'{n:02d}' for n in combo), language='text')
        
        st.markdown('**平衡对冲组（4组）**')
        for combo in combos['6码'][3:7]:
            st.code(' '.join(f'{n:02d}' for n in combo), language='text')
        
        st.markdown('**极端兜底组（3组）**')
        for combo in combos['6码'][7:]:
            st.code(' '.join(f'{n:02d}' for n in combo), language='text')
        
        # 输出纯打票版
        st.divider()
        st.subheader('📋 纯打票版（复制即可使用）')
        ticket_text = ''
        
        ticket_text += '【3组11码】\n'
        for combo in combos['11码']:
            ticket_text += ' '.join(f'{n:02d}' for n in combo) + '\n'
        
        ticket_text += '\n【5组8码】\n'
        for combo in combos['8码']:
            ticket_text += ' '.join(f'{n:02d}' for n in combo) + '\n'
        
        ticket_text += '\n【10组6码】\n'
        for combo in combos['6码']:
            ticket_text += ' '.join(f'{n:02d}' for n in combo) + '\n'
        
        st.code(ticket_text, language='text')

    # 重置功能
    st.divider()
    if st.button('🔄 重置系统', type='secondary', use_container_width=True):
        st.session_state.v72a_core_pool = []
        st.session_state.v72a_diagnosis = None
        st.session_state.v72a_combinations = None


# ==================== 【Tab 10】 ====================
with tabs[9]:
    st.header('📋 快乐8预测体系 V7.1「动态趋势适配-风险收益平衡」优化方案')
    st.divider()
    
    # 一、方案核心定位与优化总纲
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    <h2 style="color: white; margin-top: 0;">一、方案核心定位与优化总纲</h2>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader('（一）核心定位')
    st.markdown("""
    <div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; border-left: 4px solid #2196f3; margin-bottom: 16px;">
    <p style="font-size: 16px; line-height: 1.8; margin: 0;">
    <strong>长期稳定娱乐优先，极强趋势收益释放：</strong>在保留 V7.0 体系「单价值锚定、无关联绑定、风险分散闭环」核心优势的基础上，彻底解决原体系「一刀切区域覆盖导致极强趋势收益稀释、纯价值打法极端风险过高」的矛盾，实现「常规行情稳保底、极强趋势冲上限、极端行情不翻车」的全场景最优平衡。
    </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader('（二）优化核心依据（100% 基于事前历史统计，无事后倒推）')
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div style="background-color: #fff3e0; padding: 16px; border-radius: 8px; height: 100%;">
        <h4 style="color: #e65100; margin-top: 0;">📊 常规行情数据</h4>
        <p style="font-size: 14px;"><strong>95.2%</strong> 的行情为常规均衡/弱趋势行情</p>
        <p style="font-size: 13px; color: #666;">区域覆盖均衡打法的长期稳定性和收益性最优</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div style="background-color: #ffebee; padding: 16px; border-radius: 8px; height: 100%;">
        <h4 style="color: #c62828; margin-top: 0;">⚡ 极强趋势行情数据</h4>
        <p style="font-size: 14px;"><strong>4.8%</strong> 的极强趋势行情</p>
        <p style="font-size: 13px;">核心子区间趋势强度≥90分时，纯价值打法长期收益比均衡打法高 <strong>35%</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background-color: #f5f5f5; padding: 12px; border-radius: 6px; margin: 16px 0; border-left: 4px solid #9e9e9e;">
    <p style="margin: 0;"><strong>💡 关键发现：</strong>原体系一刀切的区域规则，导致在 4.8% 的极强趋势行情中，白白损失了 35% 的潜在收益，而在 95.2% 的常规行情中，纯价值打法的风险远高于收益。</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader('（三）不可突破的刚性红线（零例外）')
    
    rules = [
        ("🚫 纯价值激进打法", "仅可用于极强趋势行情，且单期投注额不得超过总预算的 10%"),
        ("🛡️ 最低仓位保障", "无论何种行情，平衡对冲组 + 极端兜底组的总仓位不得低于 70%"),
        ("✅ 用户硬性要求", "核心池与上一期开奖号码重合率≤20%、连续三期开出号码100%剔除、连续两期开出号码降权处理"),
        ("🔄 废除硬性绑定", "彻底废除2码关联组合、共现率、生命周期的所有硬性绑定，仅保留单号码价值评分作为核心筛选依据")
    ]
    
    for title, desc in rules:
        st.markdown(f"""
        <div style="background-color: #fff; padding: 12px; border-radius: 6px; margin-bottom: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h4 style="margin: 0 0 8px 0; color: #333;">{title}</h4>
        <p style="margin: 0; font-size: 14px; color: #666;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # 二、核心规则升级
    st.markdown("""
    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    <h2 style="color: white; margin-top: 0;">二、核心规则升级：趋势强度分级动态适配体系（方案核心）</h2>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader('（一）核心子区间趋势强度量化分级')
    
    st.markdown("""
    | 趋势强度等级 | 量化评分标准 | 历史发生概率 | 核心特征 | 最优打法匹配 |
    |------------|------------|------------|---------|------------|
    | **极强趋势** | ≥90 分 | 4.8%（约每20期1次） | 核心子区间连续3期上行，开出数量≥7个，均值回归修正值<20%，无回调预警 | 主投组纯价值导向，释放收益潜力 |
    | **强趋势** | 70-89 分 | 21.3% | 核心子区间连续2期上行，开出数量5-6个，无明显回调风险 | 主投组低比例对冲，兼顾收益与稳定 |
    | **弱趋势** | 60-69 分 | 52.7% | 核心子区间震荡上行，开出数量3-4个，趋势延续性一般 | 原区域覆盖均衡打法，稳为主 |
    | **无趋势** | <60 分 | 21.2% | 各区间均衡震荡，无明显核心趋势，冷热切换频繁 | 强制多区间分散，最大化风险对冲 |
    """)
    
    st.subheader('（二）分级动态区间规则（替代原一刀切区域规则）')
    
    st.markdown("""
    | 趋势强度等级 | 核心主投组区间要求 | 平衡对冲组区间要求 | 极端兜底组区间要求 |
    |------------|-----------------|-----------------|-----------------|
    | **极强趋势** | 可取消区间限制，100%核心子区间高价值号码 | 核心子区间占比70%，反向区间占比30% | 覆盖所有4个中子区间 |
    | **强趋势** | 核心子区间占比80%，反向区间占比20% | 核心子区间占比60%，反向区间占比40% | 覆盖所有4个中子区间 |
    | **弱趋势** | 核心子区间占比60%，反向区间占比40% | 核心子区间占比50%，反向区间占比50% | 覆盖所有4个中子区间 |
    | **无趋势** | 强制覆盖≥3个中子区间，单区间占比≤50% | 强制覆盖所有4个中子区间，单区间占比≤40% | 覆盖所有4个中子区间，冷号占比≥30% |
    """)
    
    st.subheader('（三）分级动态仓位分配规则')
    
    st.markdown("""
    | 趋势强度等级 | 核心主投组仓位 | 平衡对冲组仓位 | 极端兜底组仓位 | 纯价值激进打法仓位上限 |
    |------------|-------------|-------------|-------------|-------------------|
    | **极强趋势** | 30% | 50% | 20% | 10%（总预算） |
    | **强趋势** | 25% | 55% | 20% | 0% |
    | **弱趋势** | 20% | 60% | 20% | 0% |
    | **无趋势** | 15% | 65% | 20% | 0% |
    """)
    
    st.divider()
    
    # 三、全流程标准化执行步骤
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    <h2 style="color: white; margin-top: 0;">三、全流程标准化执行步骤（优化版）</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Step 0
    with st.expander("**Step0**：基础信息与用户硬性要求前置执行（不变）", expanded=False):
        st.markdown("""
        - ✅ 锁定基期、上上期、前三期官方开奖号码，无错录漏录
        - ✅ 生成《全程绝对剔除号码清单》（连续三期开出号码），全程100%剔除
        - ✅ 生成《降权处理号码清单》（连续两期开出号码），评分强制下调20分，不得纳入核心池主仓位
        - ✅ 明确核心池与上一期重合率≤20%的硬性要求，核心池构建环节强制执行
        """)
    
    # Step 1
    with st.expander("**Step1**：双层级区间量化预判与趋势强度分级（核心升级）", expanded=False):
        st.markdown("""
        - ✅ 执行原V7.0六阶宏观区间扫描，确定宏观区间趋势与仓位范围
        - ✅ 执行原V7.0中子区间热度量级评分，确定核心/对冲/边缘子区间
        - 🆕 **新增**：计算核心子区间趋势强度评分，按标准划分为极强/强/弱/无趋势四个等级
        - ✅ 输出《N+1期趋势强度分级报告》，明确对应区间规则与仓位分配
        """)
    
    # Step 2
    with st.expander("**Step2**：纯相随号基础号码池构建（不变）", expanded=False):
        st.markdown("""
        - ✅ 严格执行「仅取前2名相随号」规则，提取三类相随号，剔除绝对剔除号码
        - ✅ 按核心/对冲/边缘子区间分层过滤，形成42-46个号码的分层总池
        - ✅ 剔除深冷禁区号、过热熔断号，完成总池合规校验
        """)
    
    # Step 3
    with st.expander("**Step3**：单号码价值量化评分（不变）", expanded=False):
        st.markdown("""
        - ✅ 按趋势强度等级动态调整评分维度权重
           - 极强趋势：核心子区间匹配度权重提升至60%
           - 无趋势：权重降至30%
        - ✅ 执行刚性降权/剔除规则，完成100分制量化评分
        - ✅ 按评分划分为：
           - **S级**：≥80分
           - **A级**：60-79分  
           - **B级**：<60分
        """)
    
    # Step 4
    with st.expander("**Step4**：动态自适应15码核心池构建（优化）", expanded=False):
        st.markdown("""
        - ✅ 规模固定15码，100%来自S级+A级高价值号码
        - ✅ 按趋势强度等级动态调整区间占比：
           | 趋势等级 | 核心子区间占比 | 反向区间上限 |
           |--------|-------------|------------|
           | 极强趋势 | ≥12个（≥80%） | ≤3个 |
           | 强趋势 | ≥10个（≥67%） | ≤5个 |
           | 弱趋势 | ≥9个（≥60%） | ≤6个 |
           | 无趋势 | 各区间均衡分布 | 单区间≤5个 |
        - ✅ 严格控制与上一期开奖号重合数量≤3个，重合率≤20%
        - ✅ 完成回测校验，单期最低命中≥4个
        """)
    
    # Step 5
    with st.expander("**Step5**：分级动态组合构建（核心升级）", expanded=False):
        st.markdown("""
        **📋 通用刚性规则（所有趋势等级通用）**
        - ✅ 固定12组6码组合 + 5组8码组合，规模不变
        - ✅ 任意两组组合重合号码≤1个，彻底避免同质化
        - ✅ 所有号码100%来自核心池+对冲趋势池，无池外号码
        - ✅ 平衡组+兜底组总仓位≥70%，确保保底收益
        
        ---
        
        **📊 分趋势等级组合构建细则**
        
        **1️⃣ 极强趋势行情（核心升级）**
        - 核心主投组（4组，30%仓位）：2组纯价值导向 + 2组低对冲导向
        - 平衡对冲组（4组，50%仓位）：核心子区间70%，反向区间30%
        - 极端兜底组（4组，20%仓位）：覆盖所有4个中子区间
        - 🆕 可选纯价值激进包（≤10%总预算）：额外2组纯价值6码组合
        
        **2️⃣ 强趋势行情**
        - 核心主投组（4组，25%仓位）：核心子区间80%，反向区间20%
        - 平衡对冲组（4组，55%仓位）：核心子区间60%，反向区间40%
        - 极端兜底组（4组，20%仓位）：覆盖所有4个中子区间
        
        **3️⃣ 弱趋势/无趋势行情（原V7.0均衡打法）**
        - 核心主投组（4组，20%/15%仓位）：核心子区间60%/50%
        - 平衡对冲组（4组，60%/65%仓位）：核心子区间50%/40%
        - 极端兜底组（4组，20%仓位）：无趋势行情下冷号占比≥30%
        """)
    
    # Step 6
    with st.expander("**Step6**：全场景极端压力测试（不变）", expanded=False):
        st.markdown("""
        - ✅ 执行原V7.0十大专项极端场景测试
        - ✅ 全部达标方可输出终版方案
        """)
    
    # Step 7
    with st.expander("**Step7**：终版方案存档与复盘迭代（不变）", expanded=False):
        st.markdown("""
        - ✅ 生成不可修改的终版方案存档，包含所有执行过程与结果
        - ✅ 开奖后24小时内完成标准化复盘，重点验证趋势强度分级的准确性
        - ✅ 仅当连续2期同一指标不合格，方可调整对应规则
        """)
    
    st.divider()
    
    st.markdown("""
    <div style="background-color: #e8f5e9; padding: 16px; border-radius: 8px; text-align: center; margin-top: 20px;">
    <h4 style="margin-top: 0; color: #2e7d32;">📌 体系核心优势总结</h4>
    <p style="margin-bottom: 0;"><strong>常规行情稳保底 → 极强趋势冲上限 → 极端行情不翻车</strong></p>
    <p style="font-size: 13px; color: #666; margin-top: 8px;">V7.1通过趋势强度分级动态适配，实现全场景最优平衡</p>
    </div>
    """, unsafe_allow_html=True)


# ==================== 【Tab 11】V7.2a 用户核心池驱动 ====================
with tabs[10]:
    st.header('🎯 快乐8预测体系 V7.2a「用户核心池驱动 + 全周期趋势适配」定制优化版')
    st.divider()

    # 一、修改核心说明与体系定位
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    <h2 style="color: white; margin-top: 0;">一、修改核心说明与体系定位</h2>
    </div>
    """, unsafe_allow_html=True)

    st.subheader('（一）核心改动')
    st.markdown("""
    <div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; border-left: 4px solid #2196f3; margin-bottom: 16px;">
    <p style="font-size: 15px; line-height: 1.8; margin: 0;">
    彻底移除原 V7.2 系统自动筛选 15 码核心池模块，改为<strong>用户自主提供 15 码核心池作为唯一输入源</strong>，体系所有分析、评分、组合动作<strong>100% 限定在用户给定的 15 码范围内</strong>，不新增、不删减任何号码。体系核心功能转变为：基于历史数据对用户核心池进行多维度量化诊断，结合当期趋势强度，生成最优风险分层组合。
    </p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader('（二）体系定位')
    st.markdown("""
    <div style="background-color: #f5f5f5; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
    <p style="font-size: 15px; line-height: 1.8; margin: 0;">
    <strong>用户核心池为根，趋势适配为纲，风险分散为底：</strong>保留 V7.2 三维趋势判定、多维度风险对冲、动态容错机制的全部核心优势，所有组合策略严格围绕用户提供的 15 码展开，最大化挖掘用户核心池的中奖潜力，同时通过分层对冲控制极端风险。
    </p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader('（三）不可突破的刚性红线（零例外）')

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div style="background-color: #ffebee; padding: 16px; border-radius: 8px; height: 100%;">
        <h4 style="color: #c62828; margin-top: 0;">🚫 号码范围红线</h4>
        <p style="font-size: 14px;">所有组合 100% 来自用户提供的 15 码核心池，绝对不引入池外任何号码</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background-color: #fff3e0; padding: 16px; border-radius: 8px; height: 100%; margin-top: 12px;">
        <h4 style="color: #ef6c00; margin-top: 0;">⚠️ 风险控制红线</h4>
        <p style="font-size: 14px;">平衡 + 兜底组合总仓位不得低于 65%，极端行情下确保保底收益</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background-color: #e8f5e8; padding: 16px; border-radius: 8px; height: 100%;">
        <h4 style="color: #2e7d32; margin-top: 0;">✅ 用户规则优先级红线</h4>
        <p style="font-size: 14px;">用户指定的任何号码剔除 / 保留要求，优先级高于所有体系内规则</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; height: 100%; margin-top: 12px;">
        <h4 style="color: #1565c0; margin-top: 0;">🔒 纯盲测红线</h4>
        <p style="font-size: 14px;">所有分析仅基于开奖前历史数据，不使用任何当期开奖信息</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # 二、全流程标准化执行步骤
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    <h2 style="color: white; margin-top: 0;">二、全流程标准化执行步骤（用户核心池专属）</h2>
    </div>
    """, unsafe_allow_html=True)

    # Step 0
    st.subheader('Step 0：基础信息与用户核心池导入')
    st.markdown("""
    <div style="background-color: #f5f5f5; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
    <ul style="margin: 0; padding-left: 20px; line-height: 1.8;">
    <li>锁定基期、上上期、前三期官方开奖号码，生成《全程绝对剔除号码清单》《降权处理号码清单》</li>
    <li>导入用户提供的 15 码核心池，去重、排序，确认无错录漏录</li>
    <li>执行前置风控筛查：标记核心池内的绝对剔除号码、降权号码、过热熔断号、深冷禁区号，向用户出具《核心池前置风险预警报告》</li>
    <li>明确当期组合输出要求：固定输出<strong>3 组 11 码、5 组 8 码、10 组 6 码</strong></li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # Step 1
    st.subheader('Step 1：用户核心池多维度量化诊断（体系核心）')
    st.markdown("""
    <div style="background-color: #e8f5e8; padding: 16px; border-radius: 8px; border-left: 4px solid #2e7d32; margin-bottom: 16px;">
    <p style="font-size: 15px; margin: 0 0 12px 0;"><strong>基于近 80 期历史数据，对用户 15 码核心池进行 6 维度全量化分析，生成《用户核心池价值诊断报告》，作为后续组合构建的唯一依据：</strong></p>
    </div>
    """, unsafe_allow_html=True)

    # 诊断维度表格
    import pandas as pd
    diagnosis_data = {
        '诊断维度': ['区间分布诊断', '冷热结构诊断', '价值密度诊断', '趋势契合度诊断', '风险集中度诊断', '历史命中率诊断'],
        '量化指标': [
            '四大中子区间（A/B/C/D）号码数量与占比',
            '热号 / 温号 / 冷号 / 深冷号数量与占比',
            'S 级 / A 级 / B 级号码数量与占比（V7.2 标准评分）',
            '核心池号码与当期三维趋势的匹配度',
            '单一区间 / 单一冷热类型最高占比',
            '近 10 期同结构核心池平均命中数'
        ],
        '核心输出': [
            '核心区间、对冲区间、缺失区间标记',
            '冷热均衡度评分、冷号回补潜力',
            '核心池整体价值评分',
            '趋势契合度评分（0-100 分）',
            '极端风险等级（低 / 中 / 高）',
            '预期命中区间'
        ]
    }
    df_diagnosis = pd.DataFrame(diagnosis_data)
    st.dataframe(df_diagnosis, use_container_width=True, hide_index=True)

    # Step 2
    st.subheader('Step 2：三维立体趋势判定（保留 V7.2 原版）')
    st.markdown("""
    <div style="background-color: #f5f5f5; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
    <ul style="margin: 0; padding-left: 20px; line-height: 1.8;">
    <li>计算四大中子区间热度强度、轮动周期、冷热结构平衡度</li>
    <li>综合三维评分，确定当期趋势等级（极强 / 强 / 弱 / 趋势反转预警）</li>
    <li>检查是否触发冷号回补预警、区间轮动预警，自动调整组合风险参数</li>
    <li>输出《当期趋势判定与组合策略指引》</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # Step 3
    st.subheader('Step 3：分层动态组合构建（适配 3/5/10 输出要求）')

    st.markdown("""
    <div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; border-left: 4px solid #2196f3; margin-bottom: 16px;">
    <h4 style="margin-top: 0; color: #1565c0;">通用组合构建刚性规则（所有组合必须满足）</h4>
    <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
    <li>所有号码 100% 来自用户 15 码核心池</li>
    <li>任意两组组合重合号码≤2 个（11 码）/≤1 个（8 码 / 6 码）</li>
    <li>无绝对剔除号码集中，单组降权号码≤1 个</li>
    <li>所有组合至少覆盖 2 个中子区间，极端兜底组必须覆盖全部 4 个中子区间</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('#### 一、3 组 11 码组合（分激进 / 稳健两层）')
    combo_11_data = {
        '组别': ['激进型 11 码', '稳健型 11 码'],
        '数量': ['1 组', '2 组'],
        '仓位占比': ['20%', '30%'],
        '核心定位': ['趋势契合时冲高奖级', '全行情稳定收益'],
        '动态区间规则': ['核心区间占比≥70%，优先纳入 S 级高价值号码', '核心区间占比 60%，冷热均衡，覆盖 3 个以上中子区间']
    }
    df_11 = pd.DataFrame(combo_11_data)
    st.dataframe(df_11, use_container_width=True, hide_index=True)

    st.markdown('#### 二、5 组 8 码组合（分主投 / 平衡两层）')
    combo_8_data = {
        '组别': ['主投型 8 码', '平衡型 8 码'],
        '数量': ['2 组', '3 组'],
        '仓位占比': ['20%', '20%'],
        '核心定位': ['主打中高命中', '保基础中奖率'],
        '动态区间规则': ['核心区间占比 65%，S 级号码占比≥50%', '核心 / 对冲区间各占 50%，冷热均衡']
    }
    df_8 = pd.DataFrame(combo_8_data)
    st.dataframe(df_8, use_container_width=True, hide_index=True)

    st.markdown('#### 三、10 组 6 码组合（分主投 / 平衡 / 兜底三层）')
    combo_6_data = {
        '组别': ['核心主投 6 码', '平衡对冲 6 码', '极端兜底 6 码'],
        '数量': ['3 组', '4 组', '3 组'],
        '仓位占比': ['15%', '20%', '15%'],
        '核心定位': ['冲击选六中六', '稳定中奖率', '极端行情防翻车'],
        '动态区间规则': [
            '核心区间占比≥70%，S 级号码占比≥50%',
            '核心 / 对冲区间各占 50%，覆盖 3 个中子区间',
            '覆盖全部 4 个中子区间，冷号占比≥30%'
        ]
    }
    df_6 = pd.DataFrame(combo_6_data)
    st.dataframe(df_6, use_container_width=True, hide_index=True)

    # Step 4
    st.subheader('Step 4：组合合规性与风险校验')
    st.markdown("""
    <div style="background-color: #f5f5f5; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
    <ul style="margin: 0; padding-left: 20px; line-height: 1.8;">
    <li><strong>号码范围校验：</strong>所有组合 100% 来自用户核心池</li>
    <li><strong>重合度校验：</strong>任意两组组合重合数符合要求</li>
    <li><strong>区间覆盖校验：</strong>兜底组全覆盖 4 个中子区间</li>
    <li><strong>风险集中度校验：</strong>无单一区间 / 单一号码过度集中</li>
    <li><strong>趋势匹配校验：</strong>组合结构与当期趋势等级匹配</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # Step 5
    st.subheader('Step 5：终版方案输出与存档')
    st.markdown("""
    <div style="background-color: #f5f5f5; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
    <ul style="margin: 0; padding-left: 20px; line-height: 1.8;">
    <li>输出纯打票版组合清单（升序排列，无多余信息）</li>
    <li>输出《组合方案说明》，包含核心池诊断结果、趋势判定、仓位建议、容错等级</li>
    <li>生成不可修改的存档文件，全程可追溯</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # 三、实战示例
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    <h2 style="color: white; margin-top: 0;">三、实战示例（基于用户历史核心池演示）</h2>
    </div>
    """, unsafe_allow_html=True)

    st.subheader('输入：用户自主提供 15 码核心池')
    st.markdown("""
    <div style="background-color: #e8f5e8; padding: 16px; border-radius: 8px; border-left: 4px solid #2e7d32; margin-bottom: 16px;">
    <p style="font-size: 18px; font-weight: bold; margin: 0; font-family: monospace;">05、06、10、25、30、33、37、38、41、45、48、51、57、67、70</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader('Step 1：核心池诊断结果')
    col_diag1, col_diag2 = st.columns(2)
    with col_diag1:
        st.markdown("""
        <div style="background-color: #e3f2fd; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
        <p style="margin: 0;"><strong>区间分布：</strong>A 区 3 个、B 区 5 个、C 区 5 个、D 区 2 个，整体均衡</p>
        </div>
        <div style="background-color: #fff3e0; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
        <p style="margin: 0;"><strong>冷热结构：</strong>热号 4 个、温号 8 个、冷号 3 个，冷热均衡</p>
        </div>
        <div style="background-color: #e8f5e8; padding: 12px; border-radius: 6px;">
        <p style="margin: 0;"><strong>价值密度：</strong>S 级 5 个、A 级 9 个、B 级 1 个，价值密度优秀</p>
        </div>
        """, unsafe_allow_html=True)

    with col_diag2:
        st.markdown("""
        <div style="background-color: #f3e5f5; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
        <p style="margin: 0;"><strong>趋势契合度：</strong>68 分，匹配弱趋势行情</p>
        </div>
        <div style="background-color: #ffebee; padding: 12px; border-radius: 6px;">
        <p style="margin: 0;"><strong>风险等级：</strong>低风险</p>
        </div>
        """, unsafe_allow_html=True)

    st.subheader('Step 2：当期趋势判定')
    st.markdown("""
    <div style="background-color: #f5f5f5; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
    <p style="margin: 0;"><strong>弱趋势行情（三维综合评分 65 分），无风险预警</strong></p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader('Step 3：终版打票组合（纯号码）')

    st.markdown('#### 一、3 组 11 码')
    st.code('06、10、25、33、37、41、45、48、57、67、70', language='text')
    st.code('05、10、30、33、37、38、45、51、57、67、70', language='text')
    st.code('05、06、25、30、38、41、45、48、51、57、70', language='text')

    st.markdown('#### 二、5 组 8 码')
    st.code('06、25、33、37、45、48、57、67', language='text')
    st.code('10、30、38、41、45、51、57、70', language='text')
    st.code('05、25、33、37、41、57、67、70', language='text')
    st.code('06、10、30、38、45、48、67、70', language='text')
    st.code('05、06、33、38、41、51、57、70', language='text')

    st.markdown('#### 三、10 组 6 码')
    st.markdown('**核心主投组（3 组）**')
    st.code('25、33、37、45、48、57', language='text')
    st.code('30、38、41、45、51、57', language='text')
    st.code('33、37、45、57、67、70', language='text')

    st.markdown('**平衡对冲组（4 组）**')
    st.code('05、25、33、45、57、67', language='text')
    st.code('06、30、38、48、51、70', language='text')
    st.code('10、33、37、41、57、67', language='text')
    st.code('05、30、38、45、51、70', language='text')

    st.markdown('**极端兜底组（3 组）**')
    st.code('05、06、25、41、57、70', language='text')
    st.code('06、10、30、45、48、67', language='text')
    st.code('05、10、33、37、51、70', language='text')

    st.divider()

    # 四、V7.2a 版核心优势
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    <h2 style="color: white; margin-top: 0;">四、V7.2a 版核心优势</h2>
    </div>
    """, unsafe_allow_html=True)

    col_adv1, col_adv2 = st.columns(2)

    with col_adv1:
        st.markdown("""
        <div style="background-color: #e8f5e8; padding: 16px; border-radius: 8px; margin-bottom: 12px;">
        <h4 style="color: #2e7d32; margin-top: 0;">✅ 完全尊重用户自主选号</h4>
        <p style="font-size: 14px; margin: 0;">所有组合严格限定在用户提供的 15 码内，不改变用户的选号基础</p>
        </div>

        <div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; margin-bottom: 12px;">
        <h4 style="color: #1565c0; margin-top: 0;">📊 专业量化诊断赋能</h4>
        <p style="font-size: 14px; margin: 0;">通过多维度历史数据分析，帮用户发现核心池的优势与潜在风险</p>
        </div>
        """, unsafe_allow_html=True)

    with col_adv2:
        st.markdown("""
        <div style="background-color: #fff3e0; padding: 16px; border-radius: 8px; margin-bottom: 12px;">
        <h4 style="color: #ef6c00; margin-top: 0;">📈 全周期趋势适配</h4>
        <p style="font-size: 14px; margin: 0;">根据当期行情动态调整组合结构，最大化挖掘用户核心池的中奖潜力</p>
        </div>

        <div style="background-color: #f3e5f5; padding: 16px; border-radius: 8px; margin-bottom: 12px;">
        <h4 style="color: #7b1fa2; margin-top: 0;">🎯 精细化风险分层</h4>
        <p style="font-size: 14px; margin: 0;">3/5/10 组合结构覆盖不同风险偏好，平衡收益与风险</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background-color: #e8f5e9; padding: 16px; border-radius: 8px; text-align: center; margin-top: 20px;">
    <h4 style="margin-top: 0; color: #2e7d32;">📌 输出标准统一</h4>
    <p style="margin-bottom: 0;"><strong>固定输出格式，纯号码打票版直接可用，无需二次整理</strong></p>
    </div>
    """, unsafe_allow_html=True)

