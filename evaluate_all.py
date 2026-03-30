import argparse
import copy
import multiprocessing
import os
import shutil
import time
from functools import partial

import numpy as np
import tabulate
import tqdm

from utils import load_messages, dump_messages, load_frontalk_dataset
from webvoyager.run_evaluate import run_evaluate

N_TURNS_PER_DATA = 10


def calc_forgetting(results, instruction_type=None):
    results = [aggregate_metrics(r, suppress_warning=True) for r in results]

    numerator = 0
    denominator = 0
    for i in range(N_TURNS_PER_DATA - 1):  # <- per instruction (excluding last one)
        if instruction_type is not None:
            n = results[i]['per_inst_and_type'][instruction_type][i]['correct']
            d = results[-1]['per_inst_and_type'][instruction_type][i]['correct']
            if n is None or d is None:
                continue
        else:
            n = results[i]['per_inst'][i]['correct']
            d = results[-1]['per_inst'][i]['correct']
        numerator += n
        denominator += d
    return 1 - denominator / numerator


def augment_type_in_metrics(metrics, data):
    metrics = copy.deepcopy(metrics)
    for d in data:
        k = d['id']
        if k in metrics:
            metrics[k] = [[i, j, acc, d['cases'][i]['type']] for i, j, acc in metrics[k]]
    return metrics


def aggregate_metrics(metrics, suppress_warning=False, force_complete=False):
    if 'all' in metrics:  # metrics are already aggregated
        return metrics

    metrics_all = []
    metrics_per_inst = [[] for _ in range(10)]
    metrics_per_type = {'function': [], 'design': []}
    metrics_per_inst_and_type = {'function': [[] for _ in range(10)], 'design': [[] for _ in range(10)]}
    for k, m in metrics.items():
        for i, _, acc, t in m:
            acc = int(acc)
            metrics_all.append(acc)
            metrics_per_inst[i].append(acc)
            metrics_per_type[t].append(acc)
            metrics_per_inst_and_type[t][i].append(acc)

    def aggregate(x):
        if len(x) == 0:
            return {'correct': None, 'total': None, 'acc': None}
        else:
            return {'correct': sum(x), 'total': len(x), 'acc': sum(x) / len(x)}

    if len(metrics_all) != 3676:
        if not suppress_warning:
            print(f"This isn't full evaluation. Only has {len(metrics_all)} entries (total should be 3676)")
        if force_complete:
            return None

    return {
        'all': aggregate(metrics_all),
        'per_inst': [aggregate(x) for x in metrics_per_inst],
        'per_type': {k: aggregate(v) for k, v in metrics_per_type.items()},
        'per_inst_and_type': {k: [aggregate(vv) for vv in v] for k, v in metrics_per_inst_and_type.items()}
    }


def display_metrics(metrics):
    aggregated = aggregate_metrics(metrics)

    def tabulated_line(aggregated):
        if aggregated is None or aggregated['total'] is None:
            return ['-', '-', ]
        else:
            return ["{:.2f}".format(aggregated['acc'] * 100),
                    '{:d}/{:d}'.format(aggregated['correct'], aggregated['total'])]

    table = [["Acc. all", ] + tabulated_line(aggregated['all']), '', ] + \
            [["Acc. Type {:s}".format(k.capitalize()), ] + tabulated_line(aggregated['per_type'][k])
             for k in ['function', 'design']] + ['', ] + \
            [["Acc. Instruction {:d}".format(i + 1), ] + tabulated_line(aggregated['per_inst'][i]) for i in range(10)]
    print(tabulate.tabulate(table))


def main_func(o, args):
    data, i, j = o

    request_kwargs = {'model': args.openai_model, 'openai_api_key': args.local_openai_key,
                      'local_openai_port': args.local_openai_port}

    test_conditions = data['cases'][i]['test_conditions'][j]
    context = '\n\n'.join([d['instructions'] for d in data['cases'][:i + 1]])

    filename = os.path.abspath(os.path.join(args.dir, data['id'], 'index.html'))
    task_dir = os.path.join(args.dir, data['id'], 'evaluation_tmpdir',
                            args.openai_model.replace('/', '__'), f'{i}-{j}')
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir, ignore_errors=True)
    acc = run_evaluate('file://' + filename, test_conditions, context, request_kwargs, task_dir=task_dir)
    return data, i, j, acc


def evaluate_main(args):
    data = load_frontalk_dataset()

    metrics_fname = os.path.join(
        args.dir, 'evaluation_results.{}.jsonl'.format(args.openai_model.replace('/', '__'))
    )
    metrics = {}
    acc_all = []
    if os.path.exists(metrics_fname):
        metrics = load_messages(metrics_fname)
        for k in metrics:
            acc_all += [acc for i, j, acc in metrics[k]]

    inputs_todo = []
    for d in data:
        for i in range(len(d['cases'])):
            if args.t_start <= i <= args.t_end:
                for j in range(len(d['cases'][i]['test_conditions'])):
                    if d['id'] not in metrics or not any([i == i_ and j == j_ for i_, j_, acc in metrics[d['id']]]):
                        inputs_todo.append((d, i, j))

    if len(inputs_todo) > 0:
        d_old = data[0]
        with multiprocessing.Pool(args.num_workers) as p:
            pbar = tqdm.tqdm(p.imap(partial(main_func, args=args), inputs_todo), total=len(inputs_todo))
            for d, i, j, acc in pbar:
                if d['id'] not in metrics:
                    metrics[d['id']] = []
                dump_messages(metrics_fname, d['id'], metrics[d['id']], metrics[d['id']] + [[i, j, int(acc)], ])
                metrics[d['id']].append([i, j, int(acc)])

                acc_all.append(int(acc))
                if d != d_old:
                    print("At data {:d}: acc = {:.4f}".format(data.index(d), np.mean(acc_all)))
                    d_old = d
                pbar.set_postfix(acc=np.mean(acc_all))

    metrics = augment_type_in_metrics(metrics, data)
    display_metrics(metrics)
    return metrics


def evaluate_one(args, t):
    args = copy.deepcopy(args)
    args.dir = os.path.join(args.dir, f't.{t}')
    if t == N_TURNS_PER_DATA - 1:
        args.t_start = 0
        args.t_end = N_TURNS_PER_DATA
    else:
        args.t_start = args.t_end = t
    print("-" * 10, "Evaluating {}...".format(t))

    while True:
        try:
            metrics = evaluate_main(args)
        except:
            time.sleep(10)
        else:
            break

    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")
    parser.add_argument("--local_openai_port", default=None)
    parser.add_argument("--local_openai_key", default=None)
    parser.add_argument("--openai_model", default="gpt-4o")
    parser.add_argument("--num_workers", default=16, type=int)
    parser.add_argument("--last_turn_only", default=False, action="store_true")
    args = parser.parse_args()

    results_all = [None for _ in range(N_TURNS_PER_DATA)]
    for t in [N_TURNS_PER_DATA - 1, ] + list(range(N_TURNS_PER_DATA - 1)):
        results = evaluate_one(args, t)
        results_all[t] = results
        if args.last_turn_only:
            break
    print("Final accuracy:\n------")
    display_metrics(results_all[-1])
    if args.last_turn_only:
        return

    # Calculate forgetting
    print()
    print("Forgetting = {:.2f}".format(calc_forgetting(results_all) * 100))
    for key in ['function', 'design']:
        print("{} - Forgetting = {:.2f}".format(
            key.capitalize(), calc_forgetting(results_all, instruction_type=key) * 100
        ))


if __name__ == "__main__":
    main()
