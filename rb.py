import argparse
import os

import numpy as np

import fixed_env as env
import load_trace


A_DIM = 6
VIDEO_BIT_RATE = [300, 750, 1200, 1850, 2850, 4300]  # Kbps
M_IN_K = 1000.0
BITS_IN_BYTE = 8.0
REBUF_PENALTY = 4.3
SMOOTH_PENALTY = 1
DEFAULT_QUALITY = 1
RANDOM_SEED = 42


def select_rb_bitrate(throughput_history, safety_factor):
    if not throughput_history:
        return DEFAULT_QUALITY

    predicted_bandwidth = np.mean(throughput_history) * safety_factor
    bit_rate = 0
    for i, rate in enumerate(VIDEO_BIT_RATE):
        if rate <= predicted_bandwidth:
            bit_rate = i
        else:
            break
    return bit_rate


def build_arg_parser():
    parser = argparse.ArgumentParser(description='Run a basic rate-based ABR simulation.')
    parser.add_argument('--history-len', type=int, default=5,
                        help='Number of recent chunk throughputs used for prediction.')
    parser.add_argument('--safety-factor', type=float, default=0.9,
                        help='Conservative multiplier applied to predicted bandwidth.')
    parser.add_argument('--rebuf-penalty', type=float, default=REBUF_PENALTY,
                        help='Reward penalty weight for rebuffer time.')
    parser.add_argument('--smooth-penalty', type=float, default=SMOOTH_PENALTY,
                        help='Reward penalty weight for bitrate switching.')
    parser.add_argument('--trace-folder', default=load_trace.COOKED_TRACE_FOLDER,
                        help='Folder containing network trace files.')
    parser.add_argument('--traces', nargs='*', default=None,
                        help='Optional trace file names to run, e.g. norway_bus_1 norway_car_1.')
    parser.add_argument('--summary-dir', default=None,
                        help='Output folder for log files.')
    return parser


def main():
    args = build_arg_parser().parse_args()
    assert args.history_len > 0
    assert args.safety_factor > 0

    np.random.seed(RANDOM_SEED)

    all_cooked_time, all_cooked_bw, all_file_names = load_trace.load_trace(
        cooked_trace_folder=args.trace_folder,
        trace_files=args.traces)

    net_env = env.Environment(all_cooked_time=all_cooked_time,
                              all_cooked_bw=all_cooked_bw)

    summary_dir = args.summary_dir
    if summary_dir is None:
        summary_dir = './results_rb_h{}_sf{}_rp{}_sp{}'.format(
            args.history_len, args.safety_factor, args.rebuf_penalty, args.smooth_penalty)
    os.makedirs(summary_dir, exist_ok=True)
    log_prefix = os.path.join(summary_dir, 'log_sim_rb')

    video_count = 0

    while video_count < len(all_file_names):
        log_path = log_prefix + '_' + all_file_names[net_env.trace_idx]
        log_file = open(log_path, 'w')
        time_stamp = 0
        last_bit_rate = DEFAULT_QUALITY
        bit_rate = DEFAULT_QUALITY
        throughput_history = []
        r_batch = []

        while True:
            delay, sleep_time, buffer_size, rebuf, \
            video_chunk_size, next_video_chunk_sizes, \
            end_of_video, video_chunk_remain = \
                net_env.get_video_chunk(bit_rate)

            time_stamp += delay
            time_stamp += sleep_time

            reward = VIDEO_BIT_RATE[bit_rate] / M_IN_K \
                     - args.rebuf_penalty * rebuf \
                     - args.smooth_penalty * np.abs(VIDEO_BIT_RATE[bit_rate] -
                                                    VIDEO_BIT_RATE[last_bit_rate]) / M_IN_K
            r_batch.append(reward)

            last_bit_rate = bit_rate

            log_file.write(str(time_stamp / M_IN_K) + '\t' +
                           str(VIDEO_BIT_RATE[bit_rate]) + '\t' +
                           str(buffer_size) + '\t' +
                           str(rebuf) + '\t' +
                           str(video_chunk_size) + '\t' +
                           str(delay) + '\t' +
                           str(reward) + '\n')
            log_file.flush()

            if delay > 0:
                throughput_kbps = video_chunk_size * BITS_IN_BYTE / (delay / M_IN_K) / M_IN_K
                throughput_history.append(throughput_kbps)
                throughput_history = throughput_history[-args.history_len:]

            bit_rate = select_rb_bitrate(throughput_history, args.safety_factor)

            if end_of_video:
                break

        log_file.write('\n')
        log_file.close()

        print("video count", video_count,
              "trace", all_file_names[(net_env.trace_idx - 1) % len(all_file_names)],
              "reward", np.sum(r_batch))
        video_count += 1


if __name__ == '__main__':
    main()
