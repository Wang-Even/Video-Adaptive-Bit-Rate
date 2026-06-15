# ABR 实验运行说明

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 运行 BBA

默认运行全部 trace：

```bash
python bba.py
```

选择 3 条 trace，并指定输出目录：

```bash
python bba.py --traces norway_bus_1 norway_car_1 norway_train_1 --summary-dir results_bba_demo
```

修改 BBA 参数：

```bash
python bba.py --reservoir 5 --cushion 10 --traces norway_bus_1 norway_car_1 norway_train_1 --summary-dir results_bba_r5_c10
python bba.py --reservoir 10 --cushion 20 --traces norway_bus_1 norway_car_1 norway_train_1 --summary-dir results_bba_r10_c20
```

修改 reward 惩罚权重：

```bash
python bba.py --rebuf-penalty 6.0 --smooth-penalty 1.5 --traces norway_bus_1 norway_car_1 norway_train_1 --summary-dir results_bba_penalty
```

## 3. 运行 RB

基础 RB 使用最近若干个 chunk 的实测吞吐量均值预测带宽，再选择不超过预测带宽的最高码率。

```bash
python rb.py --traces norway_bus_1 norway_car_1 norway_train_1 --summary-dir results_rb_demo
```

修改吞吐量历史窗口和安全系数：

```bash
python rb.py --history-len 5 --safety-factor 0.9 --traces norway_bus_1 norway_car_1 norway_train_1 --summary-dir results_rb_h5_sf09
```

## 4. 生成统计表和曲线图

```bash
python analyze_results.py --traces norway_bus_1 norway_car_1 norway_train_1 --result-dirs results_bba_demo results_rb_demo --output-dir analysis_demo
```

输出内容：

- `trace_stats.csv`：平均带宽、最大/最小带宽、标准差、带宽变化幅度、是否突发下降或剧烈波动。
- `abr_metrics.csv`：平均码率、总卡顿时间、平均卡顿时间、平均码率波动、总 reward、平均 reward。
- `*_bandwidth.png`：网络带宽变化曲线。
- `*_buffer.png`：缓冲区大小变化曲线。
- `*_bitrate.png`：视频码率选择变化曲线。

## 5. 日志格式

`bba.py` 和 `rb.py` 生成的日志每行字段依次为：

```text
time_stamp bit_rate buffer_size rebuffer_time chunk_size download_time reward
```
