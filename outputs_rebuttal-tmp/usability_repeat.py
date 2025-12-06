import argparse
import json
import multiprocessing
import os
import shutil
import time
from functools import partial

import numpy as np
import tqdm

from utils import load_frontalk_dataset
from webvoyager.run_evaluate import run_evaluate_usability, compare_usability


def main_func(data, args):
    request_kwargs = {'model': 'gpt-4o', 'openai_api_key': args.local_openai_key,
                      'local_openai_port': args.local_openai_port}

    filename = os.path.abspath(os.path.join(args.dir, data['id'], 'index.html'))
    task_dir = os.path.join(args.dir, data['id'], 'usability_compare_tmpdir', args.openai_model.replace('/', '__'))
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir, ignore_errors=True)
    run_evaluate_usability('file://' + filename, data['summary']['purpose'], request_kwargs, task_dir=task_dir)

    ref_dir = os.path.join(REF, data['id'], 'usability_compare_tmpdir')
    msg_1, score_1 = compare_usability(task_dir, ref_dir, request_kwargs)  # 0, 0.5, 1
    msg_2, score_2 = compare_usability(ref_dir, task_dir, request_kwargs)
    score_2 = (1 - score_2) if score_2 is not None else None
    return data, (msg_1, score_1), (msg_2, score_2)


def main_(args):
    data = load_frontalk_dataset()

    metrics_fname = os.path.join(
        args.dir, 'usability_comparison_results.{}.jsonl'.format(args.openai_model.replace('/', '__'))
    )
    metrics = {}
    if os.path.exists(metrics_fname):
        with open(metrics_fname) as f:
            for line in f:
                k, v1, v2 = json.loads(line)
                metrics[k] = (v1, v2)
        metrics = {d['id']: metrics[d['id']] for d in data if d['id'] in metrics}

    messages_fname = os.path.join(
        args.dir, 'usability_comparison_messages.{}.jsonl'.format(args.openai_model.replace('/', '__'))
    )
    messages = {}
    if os.path.exists(messages_fname):
        with open(messages_fname) as f:
            for line in f:
                k, m1, m2 = json.loads(line)
                messages[k] = (m1, m2)
        messages = {d['id']: messages[d['id']] for d in data if d['id'] in messages}
    assert len(messages) == len(metrics)

    while True:
        data_todo = [d for d in data if d['id'] not in metrics]
        with multiprocessing.Pool(args.num_workers) as p:
            pbar = tqdm.tqdm(p.imap(partial(main_func, args=args), data_todo), total=len(data_todo))
            for d, (m1, v1), (m2, v2) in pbar:
                if v1 is not None and v2 is not None:
                    metrics[d['id']] = (v1, v2)
                    pbar.set_postfix(winrate=np.mean(list(metrics.values())))
                    with open(metrics_fname, 'a') as f:
                        f.write(json.dumps([d['id'], v1, v2]) + '\n')
                    with open(messages_fname, 'a') as f:
                        f.write(json.dumps([d['id'], m1, m2]) + '\n')
        if len(metrics) == len(data):
            break
        print("Not finished! Only finished {:d} out of {:d}. Try again".format(len(metrics), len(data)))

    print('->', np.mean(list(metrics.values())))
    return metrics


REF = './outputs_comparison_ref'


def mean_confidence_interval(data, confidence=0.95):
    import math
    import statistics
    from scipy import stats

    n = len(data)
    if n < 2:
        raise ValueError("Need at least 2 data points for a confidence interval.")

    mean = statistics.mean(data)
    s = statistics.stdev(data)  # sample standard deviation (n-1)

    se = s / math.sqrt(n)  # standard error
    alpha = 1 - confidence
    t_crit = stats.t.ppf(1 - alpha / 2, df=n - 1)  # critical t value

    margin = t_crit * se
    lower = mean - margin
    upper = mean + margin
    return mean, margin, lower, upper


def main(args=None):
    if args is None:
        parser = argparse.ArgumentParser()
        parser.add_argument("dir")
        parser.add_argument("--local_openai_port", default=None)
        parser.add_argument("--local_openai_key", default=None)
        parser.add_argument("--openai_model", default=None)
        parser.add_argument("--num_workers", default=32, type=int)
        parser.add_argument("--keep_retrying", default=False, action="store_true")
        args = parser.parse_args()

    accs = []
    for m in ['gpt-4o', 'gpt-4o_turn-0', 'gpt-4o_turn-1', 'gpt-4o_turn-2', 'gpt-4o_turn-3']:
        args.openai_model = m
        metrics = main_(args)
        accs.append(metrics.values())
    mean, margin, lower, upper = mean_confidence_interval(accs)
    print(f"Mean ± 95% CI: {mean:.3f} ± {margin:.3f}")
    print(f"Interval: [{lower:.3f}, {upper:.3f}]")


if __name__ == "__main__":
    main()
