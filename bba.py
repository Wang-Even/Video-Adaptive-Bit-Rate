import os
import argparse
import numpy as np
import fixed_env as env
import load_trace



A_DIM = 6
VIDEO_BIT_RATE = [300,750,1200,1850,2850,4300]  # Kbps
M_IN_K = 1000.0
REBUF_PENALTY = 4.3  
SMOOTH_PENALTY = 1
DEFAULT_QUALITY = 1
RANDOM_SEED = 42
RAND_RANGE = 1000000
RESERVOIR = 5  # BB
CUSHION = 10  # BB
# log in format of time_stamp bit_rate buffer_size rebuffer_time chunk_size download_time reward


def select_bba_bitrate(buffer_size, reservoir, cushion):
    if buffer_size < reservoir:
        bit_rate = 0
    elif buffer_size >= reservoir + cushion:
        bit_rate = A_DIM - 1
    else:
        bit_rate = (A_DIM - 1) * (buffer_size - reservoir) / float(cushion)
    return int(np.clip(bit_rate, 0, A_DIM - 1))


def build_arg_parser():
    parser = argparse.ArgumentParser(description='Run BBA ABR simulation.')
    parser.add_argument('--reservoir', type=float, default=RESERVOIR,
                        help='BBA reservoir threshold in seconds.')
    parser.add_argument('--cushion', type=float, default=CUSHION,
                        help='BBA cushion width in seconds.')
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

    np.random.seed(RANDOM_SEED)

    assert len(VIDEO_BIT_RATE) == A_DIM
    assert args.cushion > 0

    all_cooked_time, all_cooked_bw, all_file_names = load_trace.load_trace(
        cooked_trace_folder=args.trace_folder,
        trace_files=args.traces)

    net_env = env.Environment(all_cooked_time=all_cooked_time,
                              all_cooked_bw=all_cooked_bw)

    summary_dir = args.summary_dir
    if summary_dir is None:
        summary_dir = './results_bba_r{}_c{}_rp{}_sp{}'.format(
            args.reservoir, args.cushion, args.rebuf_penalty, args.smooth_penalty)
    os.makedirs(summary_dir, exist_ok=True)
    log_prefix = os.path.join(summary_dir, 'log_sim_bba')

    video_count = 0

    while video_count < len(all_file_names):
        log_path = log_prefix + '_' + all_file_names[net_env.trace_idx]
        log_file = open(log_path, 'w')
        time_stamp = 0
        last_bit_rate = DEFAULT_QUALITY
        bit_rate = DEFAULT_QUALITY
        r_batch = []

        while True:
            # the action is from the last decision
            # this is to make the framework similar to the real
            delay, sleep_time, buffer_size, rebuf, \
            video_chunk_size, next_video_chunk_sizes, \
            end_of_video, video_chunk_remain = \
                net_env.get_video_chunk(bit_rate)

            time_stamp += delay  # in ms
            time_stamp += sleep_time  # in ms

            # reward is video quality - rebuffer penalty - smoothness penalty
            reward = VIDEO_BIT_RATE[bit_rate] / M_IN_K \
                     - args.rebuf_penalty * rebuf \
                     - args.smooth_penalty * np.abs(VIDEO_BIT_RATE[bit_rate] -
                                                    VIDEO_BIT_RATE[last_bit_rate]) / M_IN_K
            r_batch.append(reward)

            last_bit_rate = bit_rate

            # log format: time_stamp bit_rate buffer_size rebuffer_time chunk_size download_time reward
            log_file.write(str(time_stamp / M_IN_K) + '\t' +
                           str(VIDEO_BIT_RATE[bit_rate]) + '\t' +
                           str(buffer_size) + '\t' +
                           str(rebuf) + '\t' +
                           str(video_chunk_size) + '\t' +
                           str(delay) + '\t' +
                           str(reward) + '\n')
            log_file.flush()

            bit_rate = select_bba_bitrate(buffer_size, args.reservoir, args.cushion)

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
