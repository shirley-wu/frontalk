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
    request_kwargs = {'model': args.openai_model, 'openai_api_key': args.local_openai_key,
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

    messages_fname = os.path.join(
        args.dir, 'usability_comparison_messages.{}.jsonl'.format(args.openai_model.replace('/', '__'))
    )
    messages = {}
    if os.path.exists(messages_fname):
        with open(messages_fname) as f:
            for line in f:
                k, m1, m2 = json.loads(line)
                messages[k] = (m1, m2)
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

    if args.keep_retrying:
        while True:
            try:
                ret = main_(args)
            except:
                time.sleep(10)
            else:
                break
    else:
        ret = main_(args)
    return ret


if __name__ == "__main__":
    main()
