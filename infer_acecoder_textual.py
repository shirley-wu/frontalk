import argparse
import json
import os
import shutil
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import tqdm

from infer_multiturn_textual import (
    PROMPT, N_TURNS_PER_DATA, simulate_user, get_simple_navigation
)
from utils import (
    parse_files, dump_files, load_frontalk_dataset, n_turns, load_messages, dump_messages, request_with_truncation
)
from webvoyager.run_acecoder import run_verify_instruction

REFINE_PROMPT = "---\n\nIn addition to following the instructions above, also consider the feedback below:"


def main_func(data, args, messages):
    request_kwargs = {'model': args.openai_model, 'openai_api_key': args.local_openai_key,
                      'local_openai_port': args.local_openai_port}
    if args.max_tokens is not None:
        request_kwargs['max_tokens'] = args.max_tokens
    user_kwargs = dict(model=args.user_model)

    if len(messages) == 0:  # initialize message
        messages = [{'role': 'system', 'content': PROMPT}]

    # request i-th turn
    i = n_turns(messages)
    assert i < N_TURNS_PER_DATA
    if i == 0:
        last_out_dirname_ = None
    else:
        last_out_dirname_ = os.path.join(args.out_dirname, f't.{i - 1}', data['id'].replace('.json', ".html"))

    # request by dynamic user message
    msg = simulate_user(user_kwargs, i, data, html_dir=last_out_dirname_)
    # request
    messages.append({"role": "user", "content": msg})

    # iteratively request, until NOT overlength
    response = request_with_truncation(messages=messages, data_id=data['id'], **request_kwargs)

    # output
    out_dirname_ = os.path.join(args.out_dirname, f't.{i}', data['id'].replace('.json', ".html"))
    shutil.rmtree(out_dirname_, ignore_errors=True)
    if i > 0:  # copy last
        shutil.copytree(last_out_dirname_, out_dirname_)
    else:
        os.makedirs(out_dirname_, exist_ok=True)
    files = parse_files(response, out_dirname_)
    dump_files(files, out_dirname_)

    # New, ours: reflect
    reflect_msg = ''
    reflect_all_outputs = {}
    task_dir = os.path.join(args.out_dirname, 'ours_tmpdir', data['id'], f't.{i}-reflect.curr')
    shutil.rmtree(task_dir, ignore_errors=True)
    met, reason = run_verify_instruction(
        'file://' + os.path.abspath(os.path.join(out_dirname_, 'index.html')), data['summary']['purpose'],
        msg, request_kwargs={**request_kwargs, 'max_tokens': 1000}, task_dir=task_dir
    )
    reflect_all_outputs['current'] = (met, reason)
    if not met:
        reflect_msg = "## Feedback for Instructions at Current Turn\n" + reason
    for i_ in range(i):
        task_dir = os.path.join(args.out_dirname, 'ours_tmpdir', data['id'], f't.{i}-reflect.{i_}')
        shutil.rmtree(task_dir, ignore_errors=True)
        msg = messages[i_ * 2 + 1]['content']
        met, reason = run_verify_instruction(
            'file://' + os.path.abspath(os.path.join(out_dirname_, 'index.html')), data['summary']['purpose'],
            msg, request_kwargs={**request_kwargs, 'max_tokens': 1000}, task_dir=task_dir
        )
        reflect_all_outputs[i_] = (met, reason)
        if not met:
            reflect_msg += "\n\n### Instructions at Turn {:d}\n{}\n\n### Feedback for Instructions at Turn {:d}\n{}".format(
                i_ + 1, msg, i_ + 1, reason
            )
    with open(os.path.join(out_dirname_, 'reflect.json'), 'w') as f:
        json.dump(reflect_all_outputs, f)
    reflect_msg = reflect_msg.strip()
    if reflect_msg:
        response = request_with_truncation(
            messages=messages[:-1] + [{
                'role': 'user', 'content': messages[-1]['content'] + '\n\n' + REFINE_PROMPT + '\n\n' + reflect_msg
            }],
            data_id=data['id'] + '||refine', **request_kwargs,
        )
        # backup
        shutil.move(out_dirname_, out_dirname_ + '.backup-prior-to-reflect')
        # re-do output
        shutil.rmtree(out_dirname_, ignore_errors=True)
        if i > 0:  # copy last
            shutil.copytree(last_out_dirname_, out_dirname_)
        else:
            os.makedirs(out_dirname_, exist_ok=True)
        files = parse_files(response, out_dirname_)
        dump_files(files, out_dirname_)

    messages.append({"role": "assistant", "content": response})
    return data, messages, i == N_TURNS_PER_DATA - 1


def main_(args):
    os.makedirs(args.out_dirname, exist_ok=True)

    data = load_frontalk_dataset()

    messages_all = {}
    total = len(data) * N_TURNS_PER_DATA
    messages_fname = os.path.join(args.out_dirname, "messages.jsonl")
    if os.path.exists(messages_fname):
        print("Load existing messages:", messages_fname)
        messages_all = load_messages(messages_fname)
        total = sum([N_TURNS_PER_DATA - n_turns(messages_all.get(d['id'])) for d in data])
    with open(os.path.join(args.out_dirname, "navigation.html"), "w") as f:
        f.write(get_simple_navigation(data, messages_all))

    finished_all = {d['id']: n_turns(messages_all.get(d['id'])) == N_TURNS_PER_DATA for d in data}
    pbar = tqdm.tqdm(total=total)
    with ProcessPoolExecutor(max_workers=args.num_workers) as exe:
        # map each future -> its (x,i) so we know how to chain
        future_to_args = [exe.submit(main_func, d, args, messages_all.get(d['id'], []))
                          for d in data if not finished_all[d['id']]]
        while not all(finished_all.values()):
            # wait for the next future to complete
            fut = next(as_completed(future_to_args))
            d, messages, finished = fut.result()
            dump_messages(messages_fname, d['id'], messages_all.get(d['id']), messages)
            messages_all[d['id']] = messages
            finished_all[d['id']] = finished
            # remove the completed future
            future_to_args.remove(fut)
            if not finished:
                future_to_args.append(exe.submit(main_func, d, args, messages_all[d['id']]))
            pbar.update()
            if pbar.n % 20 == 0:
                with open(os.path.join(args.out_dirname, "navigation.html"), "w") as f:
                    f.write(get_simple_navigation(data, messages_all))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out_dirname', type=str)
    parser.add_argument("--local_openai_port", default=None, nargs="+")
    parser.add_argument("--local_openai_key", default=None)
    parser.add_argument("--openai_model", default="gpt-4o")
    parser.add_argument("--num_workers", default=16, type=int)
    parser.add_argument("--max_tokens", default=None, type=int)
    parser.add_argument("--keep_retrying", default=False, action="store_true")
    args = parser.parse_args()
    args.user_model = 'gpt-4o'  # <- hardcode as gpt-4o

    if args.keep_retrying:
        while True:
            try:
                main_(args)
            except:
                time.sleep(10)
            else:
                break
    else:
        main_(args)


if __name__ == "__main__":
    main()
